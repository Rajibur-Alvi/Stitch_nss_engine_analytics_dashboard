from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os
import random

from engine import NSSProcessor
from pruning_agent import PruningAgent, PruningReport
import bridge

app = FastAPI(title="NSS Engine Analytics Dashboard")

# ── Singletons ────────────────────────────────────────────────────────
processor     = NSSProcessor()
pruning_agent = PruningAgent(cutoff_strategy="mean", merge_adjacent=True)

# ── Analysis store ────────────────────────────────────────────────────
analysis_store: dict = {
    "entropy_history":  [],
    "patterns_found":   [],
    "spike_indices":    [],
    "total_bytes":      0,
    "avg_entropy":      0.0,
    "last_filename":    "",
    "pruning_report":   None,   # PruningReport | None
}

# ── Templates / static ────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR    = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ── Pages ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse(request, "upload.html", {})

@app.get("/monitor", response_class=HTMLResponse)
async def monitor_page(request: Request):
    return templates.TemplateResponse(request, "monitor.html", {})

@app.get("/results", response_class=HTMLResponse)
async def results_page(request: Request):
    report = analysis_store["pruning_report"]
    return templates.TemplateResponse(request, "results.html", {
        "patterns":       analysis_store["patterns_found"],
        "pruning_report": report.to_dict() if report else None,
    })


# ── Upload & analysis ─────────────────────────────────────────────────

@app.post("/upload")
async def handle_upload(file: UploadFile = File(...)):
    content = await file.read()

    # ── 1. Entropy Core: compute per-window Shannon entropy ──────────
    patterns, entropy = processor.find_patterns(content)
    if isinstance(entropy, float):
        entropy = [entropy]

    spike_indices = getattr(processor, "last_spike_indices", [])

    # ── 2. Pruning Agent: strip low-entropy background noise ─────────
    report: PruningReport = pruning_agent.prune(
        byte_data      = content,
        entropy_series = entropy,
        spike_indices  = spike_indices,
    )

    # ── 3. Persist to analysis store ────────────────────────────────
    analysis_store["entropy_history"] = entropy
    analysis_store["patterns_found"]  = [p.hex() for p in patterns[:50]]
    analysis_store["spike_indices"]   = spike_indices
    analysis_store["total_bytes"]     = len(content)
    analysis_store["avg_entropy"]     = sum(entropy) / len(entropy) if entropy else 0.0
    analysis_store["last_filename"]   = file.filename
    analysis_store["pruning_report"]  = report

    return JSONResponse(content={
        "status":           "success",
        "filename":         file.filename,
        "bytes_processed":  len(content),
        "patterns_found":   len(patterns),
        "spikes_detected":  len(spike_indices),
        "avg_entropy":      round(analysis_store["avg_entropy"], 3),
        # Pruning summary
        "pruning": {
            "retained_bytes":   report.retained_bytes,
            "pruned_bytes":     report.pruned_bytes,
            "reduction_pct":    report.reduction_pct,
            "retained_windows": report.retained_windows,
            "pruned_windows":   report.pruned_windows,
            "entropy_cutoff":   round(report.entropy_cutoff, 4),
            "target_met":       report.target_met,
        },
    })


# ── API: live stats (monitor dashboard polls this) ────────────────────

@app.get("/api/stats")
async def get_stats():
    history   = analysis_store["entropy_history"]
    spike_idx = analysis_store["spike_indices"]

    if history:
        recent  = history[-100:]
        offset  = max(0, len(history) - 100)
        spike_count = len([i for i in spike_idx if i >= offset])
        recent_spike_positions = [
            i - offset for i in spike_idx if i >= offset
        ]
    else:
        recent                 = [random.uniform(3.5, 7.5) for _ in range(100)]
        spike_count            = random.randint(3, 12)
        recent_spike_positions = []

    # Pruning stats for the monitor panel
    report = analysis_store["pruning_report"]
    pruning_stats = report.to_dict() if report else {
        "reduction_pct":    0.0,
        "retained_windows": 0,
        "pruned_windows":   0,
        "entropy_cutoff":   0.0,
        "target_met":       False,
    }

    return JSONResponse(content={
        "avg_entropy":         round(analysis_store["avg_entropy"] or 5.5, 3),
        "total_bytes":         analysis_store["total_bytes"],
        "spike_count":         spike_count,
        "recent_entropy":      recent,
        "spike_positions":     recent_spike_positions,
        "window_size_bytes":   16,
        "spike_threshold_pct": 15,
        "pruning":             pruning_stats,
    })


# ── API: download pruned signal patches as JSON ───────────────────────

@app.get("/api/pruned-patches")
async def get_pruned_patches():
    report = analysis_store["pruning_report"]
    if not report:
        return JSONResponse(
            status_code=404,
            content={"error": "No file has been analysed yet. Upload a file first."}
        )
    return JSONResponse(content={
        "filename":        analysis_store["last_filename"],
        "reduction_pct":   report.reduction_pct,
        "entropy_cutoff":  report.entropy_cutoff,
        "total_patches":   len(report.signal_patches),
        "patches":         [p.to_dict() for p in report.signal_patches],
    })


@app.post("/api/analyze")
async def analyze_signal():
    report = analysis_store["pruning_report"]
    if not report:
        return JSONResponse(
            status_code=404,
            content={"error": "No data to analyze."}
        )
    
    # Combine first 50 high-entropy patches into a hex stream for the AI
    signal_sample = " ".join([p.raw_bytes.hex() for p in report.signal_patches[:50]])
    analysis_result = bridge.send_signal_to_minimax(signal_sample)
    
    return JSONResponse(content={
        "analysis": analysis_result
    })


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

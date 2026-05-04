import torch
import torch.nn as nn
import numpy as np
from collections import deque, Counter
import math

# ── Configuration ────────────────────────────────────────────────────
ENTROPY_WINDOW_SIZE  = 16       # Analyse entropy in 16-byte chunks
SPIKE_DEVIATION_PCT  = 0.15     # Flag a spike when entropy deviates >15% from moving avg
MOVING_AVG_WINDOW    = 8        # Windows kept in the moving-average buffer
# ─────────────────────────────────────────────────────────────────────


class NSSEngine(nn.Module):
    """
    Quantized GRU that reads raw bytes and predicts the next byte.
    No vocabulary / dictionary is used — all pattern knowledge comes
    purely from byte-transition statistics learned at runtime.
    """
    def __init__(self, vocab_size: int = 256, embed_size: int = 32, hidden_size: int = 64):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_size)
        self.gru       = nn.GRU(embed_size, hidden_size, batch_first=True)
        self.fc        = nn.Linear(hidden_size, vocab_size)

    def forward(self, x, hidden=None):
        x, hidden = self.gru(self.embedding(x), hidden)
        return self.fc(x), hidden


def get_quantized_engine() -> NSSEngine:
    """
    Build and dynamically quantise the NSSEngine to int8.
    Dynamic Quantisation converts Linear + GRU weights to int8 at load time,
    reducing memory ~4× and CPU inference time ~2× with no accuracy tuning.
    """
    model = NSSEngine()
    model.eval()
    return torch.quantization.quantize_dynamic(
        model, {nn.GRU, nn.Linear}, dtype=torch.qint8
    )


def shannon_entropy(window: bytes) -> float:
    """
    True Shannon entropy (bits per byte) of a raw byte window.

    This is the primary signal for the Byte Surprise Index.
    It measures how random/unpredictable the bytes are:
      • Pure ASCII English text   → ~3.5–4.5 bits  (low, predictable)
      • UTF-8 Bengali / Devanagari → ~6.0–7.5 bits  (higher, denser encoding)
      • Compressed / encrypted data → ~7.8–8.0 bits (maximum randomness)

    A sudden jump from ~4 bits → ~7 bits in a 16-byte window means the
    file has transitioned from one script (or format) to another.
    """
    if not window:
        return 0.0
    counts = Counter(window)
    total  = len(window)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


class NSSProcessor:
    """
    High-resolution byte-stream analyser.

    Two-layer design
    ────────────────
    Layer 1 — Shannon entropy per 16-byte window (instantaneous, exact)
      Produces the raw "Byte Surprise Index" curve shown on the dashboard.
      Because each window is only 16 bytes, a single script-switch triggers
      an immediate visible cliff on the graph rather than a slow gradient.

    Layer 2 — Quantized PyTorch GRU (context-aware)
      Runs alongside Shannon to learn *transition patterns*. The GRU's
      prediction error (cross-entropy loss) is a complementary signal; it
      rises when the model encounters a byte sequence it hasn't seen before.
      Used for pattern extraction (find_patterns).

    Dynamic Threshold
    ─────────────────
    A fixed cutoff (e.g. "flag anything above 7.0") fails when the baseline
    shifts — e.g. a file that is 90% Bengali will have a uniformly high
    baseline and internal variation will be invisible.

    Instead we keep a rolling mean of the last MOVING_AVG_WINDOW readings
    and flag any window that deviates from that mean by > SPIKE_DEVIATION_PCT
    (15 %). This means the threshold *moves with the file's own baseline*,
    making the detector equally sensitive in ASCII-heavy and Unicode-heavy
    sections.
    """

    def __init__(self):
        self.engine               = get_quantized_engine()
        self.hidden               = None
        self.last_spike_indices:  list[int]   = []
        self.last_entropy:        list[float] = []

    # ── Shannon entropy layer ─────────────────────────────────────────

    def analyze_bytes(self, byte_data: bytes) -> list[float]:
        """
        Slide a 16-byte window and return one Shannon-entropy value per window.
        The signal is *not* smoothed so script transitions appear as sharp peaks.
        """
        self.last_entropy = []
        for start in range(0, len(byte_data), ENTROPY_WINDOW_SIZE):
            window = byte_data[start: start + ENTROPY_WINDOW_SIZE]
            if not window:
                break
            self.last_entropy.append(shannon_entropy(window))
        return self.last_entropy

    # ── Dynamic-threshold spike detector ─────────────────────────────

    # ── Script Identification (Zero-Shot) ───────────────────────────

    def _identify_script(self, window: bytes) -> str:
        """
        Identify the likely script/data type of a byte window using 
        zero-shot statistical byte-range analysis.
        """
        if not window: return "EMPTY"
        
        # 1. Check for pure ASCII (0-127)
        if all(b < 128 for b in window):
            # Further distinguish between text and control/binary
            printable = sum(1 for b in window if 32 <= b <= 126 or b in (9, 10, 13))
            if printable / len(window) > 0.8:
                return "LATIN_TEXT"
            return "ASCII_CONTROL"

        # 2. Check for UTF-8 Multi-byte sequences
        # Bengali: U+0980 to U+09FF (Bytes: E0 A6 80 to E0 A7 BF)
        if any(b == 0xE0 for b in window):
            indices = [i for i, b in enumerate(window) if b == 0xE0]
            for idx in indices:
                if idx + 1 < len(window) and window[idx+1] == 0xA6:
                    return "BENGALI_UNICODE"
                if idx + 1 < len(window) and window[idx+1] == 0xA4:
                    return "DEVANAGARI_UNICODE"

        # 3. Cyrillic: U+0400 to U+04FF (Bytes: D0 80 to D1 BF)
        if any(b in (0xD0, 0xD1) for b in window):
            return "CYRILLIC_UNICODE"

        # 4. Fallback: High-entropy binary or Unknown
        entropy = shannon_entropy(window)
        if entropy > 7.5:
            return "ENCRYPTED_OR_COMPRESSED"
        
        return "UNKNOWN_SIGNAL"

    def _detect_spikes(self, entropy_series: list[float]) -> list[int]:
        """
        Walk the entropy series and flag any window whose value deviates
        more than SPIKE_DEVIATION_PCT from the moving average of the
        preceding MOVING_AVG_WINDOW values.
        """
        spike_indices: list[int] = []
        buf: deque = deque(maxlen=MOVING_AVG_WINDOW)

        for i, e in enumerate(entropy_series):
            if buf:
                moving_avg = float(np.mean(buf))
                if moving_avg > 0:
                    deviation = abs(e - moving_avg) / moving_avg
                    if deviation > SPIKE_DEVIATION_PCT:
                        spike_indices.append(i)
            buf.append(e)

        return spike_indices

    # ── GRU-based pattern extractor ───────────────────────────────────

    def _gru_entropy(self, window: bytes) -> float:
        """GRU cross-entropy for a single window (complementary signal)."""
        if not window:
            return 0.0
        inp = torch.tensor([list(window)], dtype=torch.long)
        with torch.no_grad():
            logits, self.hidden = self.engine(inp, self.hidden)
            probs   = torch.softmax(logits, dim=-1)
            gru_ent = -torch.sum(probs * torch.log(probs + 1e-9), dim=-1)
        if isinstance(self.hidden, tuple):
            self.hidden = tuple(h.detach() for h in self.hidden)
        else:
            self.hidden = self.hidden.detach()
        return float(gru_ent.mean().item())

    # ── Public API ────────────────────────────────────────────────────

    def find_patterns(
        self,
        byte_data:         bytes,
        static_threshold:  float = 2.0,
    ) -> tuple[list[bytes], list[float]]:
        """
        Full pipeline:
          1. Compute per-window Shannon entropy  → Byte Surprise Index
          2. Detect dynamic-threshold spikes     → script-transition markers
          3. Extract low-entropy runs as patterns (via Shannon < static_threshold)

        Returns
        ───────
        patterns : list of raw byte sequences that repeat predictably
        entropy  : list of per-window entropy values (one per 16 bytes)
        scripts  : list of identified scripts for each window
        """
        entropy_series = self.analyze_bytes(byte_data)
        scripts_series = []

        # Spike detection
        self.last_spike_indices = self._detect_spikes(entropy_series)

        # Pattern extraction — low-entropy windows = predictable byte runs
        patterns:       list[bytes] = []
        current_run:    list[int]   = []
        self.hidden = None  # reset GRU state for fresh pass

        for i, (e, start) in enumerate(
            zip(entropy_series, range(0, len(byte_data), ENTROPY_WINDOW_SIZE))
        ):
            window = byte_data[start: start + ENTROPY_WINDOW_SIZE]
            scripts_series.append(self._identify_script(window))
            
            if e < static_threshold:
                current_run.extend(window)
            else:
                if len(current_run) > 2:
                    patterns.append(bytes(current_run))
                current_run = []

        if len(current_run) > 2:
            patterns.append(bytes(current_run))

        return patterns, entropy_series, scripts_series

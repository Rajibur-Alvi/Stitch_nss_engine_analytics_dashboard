# NSS Engine Analytics Dashboard

A high-performance byte-stream analytics dashboard and data pruning system.

## Overview
The NSS Engine is designed to identify and strip low-entropy "background noise" from data streams, reducing data volume by 60-80% for downstream AI processing. It uses a combination of Shannon entropy analysis and a quantized GRU (Gated Recurrent Unit) to detect patterns and script transitions in raw bytes.

### Key Features
- **Entropy Core**: High-resolution Shannon entropy analysis per 16-byte window.
- **Dynamic Pruning**: Automatically strips predictable data (padding, boilerplate) while retaining high-signal patches.
- **Spike Detection**: Dynamic thresholding flags sudden shifts in data entropy (e.g., English to Bengali transitions).
- **AI Signal Intelligence**: Integrated with NVIDIA NIM (MiniMax-M2) to reconstruct meaning from pruned signals.
- **Cyber-Aesthetic UI**: Real-time monitoring and analysis with a premium, low-latency dashboard.

## Tech Stack
- **Backend**: FastAPI (Python 3.10+)
- **Neural Engine**: PyTorch (Quantized int8 GRU)
- **Frontend**: TailwindCSS, Jinja2, Vanilla JS
- **AI Acceleration**: NVIDIA NIM (MiniMax-M2.7)

## Setup & Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd stitch_nss_engine_analytics_dashboard
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Environment Variables**:
   To enable AI Signal Intelligence, set your NVIDIA API Key:
   ```bash
   export NVIDIA_API_KEY=your_key_here  # Linux/macOS
   set NVIDIA_API_KEY=your_key_here     # Windows
   ```

4. **Run the Dashboard**:
   ```bash
   python main.py
   ```
   Or use the provided batch file on Windows:
   ```bash
   run_dashboard.bat
   ```

## Usage
1. Open `http://localhost:8000` in your browser.
2. **Upload**: Drag and drop any raw file (logs, binary blobs, mixed-script text).
3. **Monitor**: Watch the "Byte Surprise Index" in real-time as the engine processes the stream.
4. **Results**: Review the pruning report and click **RUN_AI_RECONSTRUCTION** to have the AI analyze the dense signal.

## Architecture
- `engine.py`: The core NSS Processor and PyTorch model.
- `pruning_agent.py`: Logic for data reduction and patch extraction.
- `bridge.py`: Integration with external AI models via NVIDIA NIM.
- `main.py`: FastAPI application routing and state management.

---
*Built for high-efficiency signal intelligence.*

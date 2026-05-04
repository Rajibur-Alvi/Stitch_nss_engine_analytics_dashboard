import os
import requests

# Your NVIDIA API Key from build.nvidia.com
# Use an environment variable for security
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "your_nv_api_key_here")

def send_signal_to_minimax(pruned_text):
    """
    Sends the high-entropy pruned signal patches to the MiniMax-M2 model
    via NVIDIA NIM for reconstruction and analysis.
    """
    if not NVIDIA_API_KEY or NVIDIA_API_KEY == "your_nv_api_key_here":
        return "ERROR: NVIDIA_API_KEY not set. Please set the environment variable to enable AI analysis."

    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "application/json",
    }

    payload = {
        "model": "minimaxai/minimax-m2.7",
        "messages": [
            {"role": "system", "content": "You are a Signal Intelligence Agent. You receive high-entropy data patches (hex or raw) and reconstruct meaning or identify the data type/script."},
            {"role": "user", "content": f"Analyze this pruned signal: {pruned_text}"}
        ],
        "max_tokens": 1024,
        "temperature": 0.1 # Keep it low for high-entropy data
    }

    try:
        response = requests.post(invoke_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"AI analysis failed: {str(e)}"

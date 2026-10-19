import os
import sys
import uvicorn

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
os.environ["PYTHONIOENCODING"] = "utf-8"

# Ensure current directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("=" * 60)
    print(f"🚀 Shark Bot Pro is running on port {port}...")
    print(f"🌐 Local URL: http://localhost:{port}")
    print(f"📡 Webhook URL: http://localhost:{port}/api/webhook")
    print("=" * 60)
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

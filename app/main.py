import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routes.api import router as api_router
from app.logger import broadcaster
from app.binance_client import binance_service
from app.config import settings

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await broadcaster.broadcast("INFO", "🚀 تم إطلاق منصة التداول الآلي بنجاح.")
    if binance_service.is_connected():
        mode = "تجريبي (Testnet)" if settings.use_testnet else "حقيقي (Live)"
        await broadcaster.broadcast("SUCCESS", f"✅ تم الاتصال ببينانس بنجاح! النمط الحالي: {mode}")
    else:
        await broadcaster.broadcast("WARNING", "⚠️ مفاتيح بينانس غير مدخلة أو غير متصلة. يرجى إدخالها من لوحة الإعدادات.")
    yield
    # Shutdown
    await broadcaster.broadcast("INFO", "🛑 تم إيقاف منصة التداول.")

app = FastAPI(title="Binance TradingView Bot", lifespan=lifespan)

# Allow CORS for webhook and local access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

# WebSocket for live Terminal
@app.websocket("/ws/terminal")
async def websocket_terminal(websocket: WebSocket):
    await broadcaster.connect(websocket)
    try:
        while True:
            # We keep the connection open and receive any ping from client
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
    except Exception:
        broadcaster.disconnect(websocket)

# Serve Frontend static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def serve_index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Binance TradingView Webhook Bot is running. Static files missing."}

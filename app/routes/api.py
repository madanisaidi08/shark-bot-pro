import traceback
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.config import settings, save_settings, BotSettings
from app.logger import broadcaster
from app.binance_client import binance_service
from app.trading_engine import trading_engine
from app.zone_grid_engine import zone_grid_engine

router = APIRouter()

class ZoneGridConfigRequest(BaseModel):
    symbol: str = "BTCUSDT"
    total_capital: float = 200.0
    num_zones: int = 10
    zone_step_percent: float = 1.0
    base_price: Optional[float] = None
    stop_loss_type: str = "TOTAL"
    stop_loss_percent: float = 10.0
    open_range: bool = True
    demo_mode: bool = False

class UpdateSettingsRequest(BaseModel):
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None
    use_testnet: Optional[bool] = None
    webhook_passphrase: Optional[str] = None
    capital_percent: Optional[float] = None
    bot_enabled: Optional[bool] = None
    default_tp_percent: Optional[float] = None
    default_sl_percent: Optional[float] = None

class TestSignalRequest(BaseModel):
    action: str  # BUY or SELL
    symbol: str  # e.g. BTCUSDT
    tp_percent: Optional[float] = 2.0
    sl_percent: Optional[float] = 1.0
    capital_percent: Optional[float] = None

@router.get("/status")
async def get_status():
    connected = binance_service.is_connected()
    return {
        "bot_enabled": settings.bot_enabled,
        "binance_connected": connected,
        "use_testnet": settings.use_testnet,
        "capital_percent": settings.capital_percent,
        "webhook_passphrase": settings.webhook_passphrase,
        "default_tp_percent": settings.default_tp_percent,
        "default_sl_percent": settings.default_sl_percent,
        "has_keys": bool(settings.binance_api_key and settings.binance_api_secret)
    }

@router.get("/config")
async def get_config():
    # Return masked secret for security
    masked_key = settings.binance_api_key[:6] + "..." + settings.binance_api_key[-4:] if len(settings.binance_api_key) > 10 else settings.binance_api_key
    return {
        "binance_api_key": masked_key,
        "use_testnet": settings.use_testnet,
        "webhook_passphrase": settings.webhook_passphrase,
        "capital_percent": settings.capital_percent,
        "bot_enabled": settings.bot_enabled,
        "default_tp_percent": settings.default_tp_percent,
        "default_sl_percent": settings.default_sl_percent
    }

@router.post("/config")
async def update_config(req: UpdateSettingsRequest):
    if req.binance_api_key is not None and not req.binance_api_key.startswith("..."):
        settings.binance_api_key = req.binance_api_key.strip()
    if req.binance_api_secret is not None and not req.binance_api_secret.startswith("..."):
        settings.binance_api_secret = req.binance_api_secret.strip()
    if req.use_testnet is not None:
        settings.use_testnet = req.use_testnet
    if req.webhook_passphrase is not None:
        settings.webhook_passphrase = req.webhook_passphrase.strip()
    if req.capital_percent is not None:
        settings.capital_percent = max(1.0, min(100.0, req.capital_percent))
    if req.bot_enabled is not None:
        settings.bot_enabled = req.bot_enabled
    if req.default_tp_percent is not None:
        settings.default_tp_percent = req.default_tp_percent
    if req.default_sl_percent is not None:
        settings.default_sl_percent = req.default_sl_percent

    save_settings(settings)
    binance_service.reload()

    is_conn = binance_service.is_connected()
    await broadcaster.broadcast("INFO", f"⚙️ تم تحديث الإعدادات بنجاح. حالة اتصال بينانس: {'متصل ✅' if is_conn else 'غير متصل ⚠️'}")

    return {
        "status": "success",
        "binance_connected": is_conn,
        "settings": {
            "use_testnet": settings.use_testnet,
            "capital_percent": settings.capital_percent,
            "bot_enabled": settings.bot_enabled,
            "webhook_passphrase": settings.webhook_passphrase
        }
    }

@router.get("/balances")
async def get_balances():
    return binance_service.get_balances()

@router.get("/orders")
async def get_open_orders(symbol: Optional[str] = None):
    orders = binance_service.get_open_orders(symbol)
    return {"orders": orders}

@router.post("/cancel-orders")
async def cancel_orders(symbol: str):
    res = binance_service.cancel_open_orders_for_symbol(symbol)
    await broadcaster.broadcast("INFO", f"تم إلغاء الأوامر المفتوحة للزوج {symbol}")
    return {"canceled": res}

@router.post("/webhook")
async def handle_webhook(request: Request):
    """
    نقطة استقبال إشارات TradingView عبر Webhook
    """
    try:
        body = await request.json()
    except Exception:
        # بعض تنبيهات تريدينغ فيو قد ترسل كنص عادي
        try:
            body_text = (await request.body()).decode("utf-8")
            import json
            body = json.loads(body_text)
        except Exception:
            await broadcaster.broadcast("ERROR", "تم استلام رسالة Webhook ولكن ليست بتنسيق JSON صحيح!")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

    result = await trading_engine.process_signal(body)
    return result

@router.post("/test-signal")
async def test_signal(req: TestSignalRequest):
    """
    إرسال إشارة تجريبية مباشرة من واجهة التحكم لفحص التيرمينال وسرعة التنفيذ
    """
    payload = {
        "secret": settings.webhook_passphrase,
        "action": req.action,
        "symbol": req.symbol,
        "tp_percent": req.tp_percent,
        "sl_percent": req.sl_percent,
        "capital_percent": req.capital_percent or settings.capital_percent
    }
    result = await trading_engine.process_signal(payload)
    return result

# ==============================================================================
# SHARK INDEPENDENT ZONE GRID API ENDPOINTS
# ==============================================================================

@router.get("/zone-grid/status")
async def get_zone_grid_status():
    return zone_grid_engine.get_full_status()

@router.post("/zone-grid/configure")
async def configure_zone_grid(req: ZoneGridConfigRequest):
    base_p = req.base_price
    if base_p is None or base_p <= 0:
        if binance_service.is_connected():
            try:
                base_p = binance_service.get_ticker_price(req.symbol)
            except Exception:
                base_p = 100.0
        else:
            base_p = 100.0

    zone_grid_engine.configure(
        symbol=req.symbol,
        total_capital=req.total_capital,
        num_zones=req.num_zones,
        zone_step_percent=req.zone_step_percent,
        base_price=base_p,
        stop_loss_type=req.stop_loss_type,
        stop_loss_percent=req.stop_loss_percent,
        open_range=req.open_range,
        demo_mode=req.demo_mode
    )
    mode_text = "تجريبي (ديمو 10,000$)" if req.demo_mode else "حقيقي (Live Binance)"
    range_text = "مفتوح (Infinity)" if req.open_range else "مغلق (ثابت)"
    await broadcaster.broadcast("INFO", f"⚙️ تم تحديث إعدادات شبكة الزونات لزوج {req.symbol} ({req.num_zones} مستويات بمبلغ ${zone_grid_engine.per_zone_capital:.2f} لكل مستوى | الوضع: {mode_text} | النطاق: {range_text}).")
    return zone_grid_engine.get_full_status()

@router.post("/zone-grid/preview")
async def preview_zone_grid(req: ZoneGridConfigRequest):
    base_p = req.base_price
    if base_p is None or base_p <= 0:
        if binance_service.is_connected():
            try:
                base_p = binance_service.get_ticker_price(req.symbol)
            except Exception:
                base_p = 100.0
        else:
            try:
                base_p = binance_service.get_ticker_price(req.symbol)
            except Exception:
                base_p = 100.0

    # Calculate preview levels without modifying active running bot
    step_factor = 1.0 + (req.zone_step_percent / 100.0)
    levels = []
    cur_p = base_p
    per_zone = round(req.total_capital / req.num_zones, 2)
    for i in range(1, req.num_zones + 1):
        next_p = cur_p * step_factor
        levels.append({
            "index": i,
            "price": round(cur_p, 4),
            "target_price": round(next_p, 4),
            "capital": per_zone,
            "is_holding": False
        })
        cur_p = next_p

    return {
        "symbol": req.symbol.upper(),
        "base_price": round(base_p, 4),
        "total_capital": req.total_capital,
        "num_zones": req.num_zones,
        "per_zone_capital": per_zone,
        "zone_step_percent": req.zone_step_percent,
        "open_range": req.open_range,
        "demo_mode": req.demo_mode,
        "levels": levels
    }

@router.post("/zone-grid/demo-reset")
async def reset_demo_balance():
    zone_grid_engine.reset_demo_balance(10000.0)
    await broadcaster.broadcast("INFO", "🔄 تم إعادة تعيين رصيد الحساب التجريبي الديمو إلى 10,000$ USDT.")
    return {"status": "success", "demo_balance": zone_grid_engine.demo_balance, "grid": zone_grid_engine.get_full_status()}

@router.post("/zone-grid/demo-toggle")
async def toggle_demo_mode(req: Request):
    body = await req.json()
    enabled = body.get("enabled", True)
    zone_grid_engine.demo_mode = enabled
    mode_str = "الحساب التجريبي (ديمو 10,000$)" if enabled else "التداول الحقيقي (Live Binance)"
    await broadcaster.broadcast("INFO", f"🔀 تم تغيير وضع التداول إلى: {mode_str}")
    return {"status": "success", "demo_mode": zone_grid_engine.demo_mode, "grid": zone_grid_engine.get_full_status()}

@router.post("/zone-grid/start")
async def start_zone_grid():
    try:
        await zone_grid_engine.start()
        return {"status": "success", "message": "Shark Zone Grid started successfully", "grid": zone_grid_engine.get_full_status()}
    except Exception as e:
        await broadcaster.broadcast("ERROR", f"فشل تشغيل بوت الزونات: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/zone-grid/stop")
async def stop_zone_grid():
    await zone_grid_engine.stop()
    return {"status": "success", "message": "Shark Zone Grid paused", "grid": zone_grid_engine.get_full_status()}

@router.post("/zone-grid/emergency-close")
async def emergency_close_zone_grid():
    result = await zone_grid_engine.emergency_liquidate_all()
    return result

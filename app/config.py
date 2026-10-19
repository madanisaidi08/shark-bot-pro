import os
import json
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.json"

class BotSettings(BaseModel):
    binance_api_key: str = ""
    binance_api_secret: str = ""
    use_testnet: bool = True
    webhook_passphrase: str = "secure_trading_pass_2026"
    capital_percent: float = 100.0   # Default 100% of available USDT
    bot_enabled: bool = True
    slippage_buffer_percent: float = 0.2  # Buffer for stop loss limit price below trigger
    default_tp_percent: float = 2.0
    default_sl_percent: float = 1.0

def load_settings() -> BotSettings:
    data = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    # Allow environment variables (ideal for Render / Cloud hosting)
    if os.environ.get("BINANCE_API_KEY"):
        data["binance_api_key"] = os.environ.get("BINANCE_API_KEY")
    if os.environ.get("BINANCE_API_SECRET"):
        data["binance_api_secret"] = os.environ.get("BINANCE_API_SECRET")
    if os.environ.get("BINANCE_TESTNET") is not None:
        data["use_testnet"] = os.environ.get("BINANCE_TESTNET", "").lower() in ("true", "1", "yes")
    if os.environ.get("WEBHOOK_PASSPHRASE"):
        data["webhook_passphrase"] = os.environ.get("WEBHOOK_PASSPHRASE")
    if os.environ.get("CAPITAL_PERCENT"):
        try:
            data["capital_percent"] = float(os.environ.get("CAPITAL_PERCENT"))
        except ValueError:
            pass

    try:
        settings = BotSettings(**data)
    except Exception:
        settings = BotSettings()

    try:
        save_settings(settings)
    except Exception:
        pass

    return settings

def save_settings(settings: BotSettings):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings.model_dump(), f, indent=4, ensure_ascii=False)
    except Exception:
        pass

settings = load_settings()

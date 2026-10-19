# 🦈 Shark Bot Pro — Automated Binance Spot & TradingView Webhook Engine

**Shark Bot Pro** is a high-speed, automated Spot trading engine that links **TradingView** alerts (Buy/Sell/TP/SL) to **Binance Spot** execution via secure Webhooks.

---

## 🌟 Key Features

1. **Bilingual Interface (English & Arabic)**:
   - English is the primary default language (LTR).
   - Instant 1-click toggle to Arabic (RTL) in the top navigation bar.
2. **High-Speed Real-Time Balance Updating**:
   - **Pre-trade verification**: Instantly syncs with Binance to confirm available USDT before placing orders.
   - **Post-buy sync**: Automatically fetches and broadcasts updated USDT & coin balances via WebSocket immediately upon fill.
   - **Post-sell sync**: Immediately updates available USDT so subsequent buy signals execute without delay.
   - **Visual Pulse**: Green glow animation whenever balance changes, plus a dedicated manual fast-refresh button.
3. **Binance Live (Real Money) & Testnet Support**:
   - Supports genuine Binance accounts for Live Spot trading.
   - Safe toggle for Binance Testnet (demo mode).
4. **Capital Allocation & Risk Management**:
   - Customizable purchase percentage (e.g. 100% of available capital or custom slider).
   - Automated **OCO (One-Cancels-the-Other)** orders for Take Profit and Stop Loss natively on Binance Spot.
5. **Live Terminal & Signal Simulator**:
   - Dark mode console streaming logs and orders in real-time.
   - Built-in simulator to test BUY and SELL execution without needing TradingView open.

---

## 🚀 How to Run

Double-click:
```
start_bot.bat
```
Or run via PowerShell:
```bash
.\venv\Scripts\python run.py
```
Open your browser at:
👉 **`http://localhost:8000`**

---

## 📩 TradingView Alert Payload (JSON)

### BUY Alert:
```json
{
  "secret": "secure_trading_pass_2026",
  "action": "BUY",
  "symbol": "{{ticker}}",
  "tp_percent": 2.5,
  "sl_percent": 1.2,
  "capital_percent": 100
}
```

### SELL Alert:
```json
{
  "secret": "secure_trading_pass_2026",
  "action": "SELL",
  "symbol": "{{ticker}}"
}
```

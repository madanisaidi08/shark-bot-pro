import asyncio
from typing import Dict, Any, Optional
from app.config import settings
from app.logger import broadcaster
from app.binance_client import binance_service

def clean_symbol(symbol: str) -> str:
    """
    Clean and format trading symbol (e.g. BINANCE:BTCUSDT -> BTCUSDT)
    """
    s = symbol.upper().replace("/", "").replace(" ", "").replace("-", "")
    if ":" in s:
        s = s.split(":")[-1]
    return s

def extract_base_asset(symbol: str) -> str:
    for quote in ["USDT", "FDUSD", "USDC", "BUSD", "EUR", "BTC"]:
        if symbol.endswith(quote):
            return symbol[:-len(quote)]
    return symbol

class TradingEngine:
    async def process_signal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming TradingView signal via Webhook
        """
        # 1. Verify Passphrase
        secret = payload.get("secret") or payload.get("passphrase")
        if secret != settings.webhook_passphrase:
            msg = "Unauthorized alert: Invalid secret passphrase / كلمة السر غير صحيحة"
            await broadcaster.broadcast("ERROR", msg, {"received_secret": secret})
            return {"status": "error", "message": msg}

        # 2. Check Bot Status
        if not settings.bot_enabled:
            msg = "Alert received but bot is currently PAUSED / تم استلام الإشارة لكن البوت متوقف مؤقتاً"
            await broadcaster.broadcast("WARNING", msg, payload)
            return {"status": "paused", "message": msg}

        # 3. Check Binance Connection
        if not binance_service.is_connected():
            msg = "Execution failed: Binance API keys not connected / مفاتيح بينانس غير متصلة"
            await broadcaster.broadcast("ERROR", msg)
            return {"status": "error", "message": msg}

        # Check if alert is specifically for Shark Zone Grid
        if payload.get("bot_type") == "zone_grid" or payload.get("type") == "zone_grid":
            from app.zone_grid_engine import zone_grid_engine
            price = float(payload.get("price") or payload.get("close") or 0.0)
            if price > 0:
                await zone_grid_engine.on_price_tick(price)
                return {"status": "success", "message": f"Shark Zone Grid processed price tick: ${price:,.4f}"}

        # 4. Immediate Live Balance Sync before trade execution
        try:
            fresh_balances = binance_service.get_balances()
            await broadcaster.broadcast_event("balance_updated", fresh_balances)
        except Exception:
            pass

        raw_symbol = payload.get("symbol", "")
        if not raw_symbol:
            msg = "Alert is missing symbol / الإشارة تفتقر إلى اسم الزوج"
            await broadcaster.broadcast("ERROR", msg, payload)
            return {"status": "error", "message": msg}

        symbol = clean_symbol(raw_symbol)
        action = str(payload.get("action", "")).upper()
        base_asset = extract_base_asset(symbol)

        # TP / SL percentages
        tp_percent = float(payload.get("tp_percent") or payload.get("tp") or settings.default_tp_percent or 0.0)
        sl_percent = float(payload.get("sl_percent") or payload.get("sl") or settings.default_sl_percent or 0.0)

        # Capital percent
        capital_percent = float(payload.get("capital_percent") or settings.capital_percent or 100.0)
        capital_percent = max(1.0, min(100.0, capital_percent))

        await broadcaster.broadcast(
            "INFO",
            f"📥 Received [{action}] for {symbol} | Capital: {capital_percent}% | TP: {tp_percent}% | SL: {sl_percent}%",
            payload
        )

        # Execute BUY
        if action in ["BUY", "LONG"]:
            return await self._execute_buy(symbol, base_asset, capital_percent, tp_percent, sl_percent)

        # Execute SELL / CLOSE
        elif action in ["SELL", "SHORT", "CLOSE"]:
            return await self._execute_sell(symbol, base_asset)

        else:
            msg = f"Unknown signal action: {action}. Must be BUY, SELL, or CLOSE."
            await broadcaster.broadcast("WARNING", msg)
            return {"status": "error", "message": msg}

    async def _execute_buy(self, symbol: str, base_asset: str, capital_percent: float, tp_percent: float, sl_percent: float) -> Dict[str, Any]:
        try:
            # 1. Fetch fresh live USDT balance
            balances = binance_service.get_balances()
            usdt_free = float(balances.get("usdt_free", 0.0))

            if usdt_free < 5.0:
                msg = f"Insufficient USDT balance for BUY ({usdt_free:.2f} USDT). Minimum 5.0 USDT required."
                await broadcaster.broadcast("ERROR", msg)
                return {"status": "error", "message": msg}

            # 2. Calculate investment amount based on capital percentage
            invest_amount = (usdt_free * (capital_percent / 100.0))
            if invest_amount < 5.0:
                invest_amount = 5.0

            # Safety buffer for fees (0.1%)
            invest_amount = min(invest_amount, usdt_free * 0.999)

            await broadcaster.broadcast(
                "INFO",
                f"⚡ Executing Market BUY: {invest_amount:.2f} USDT out of {usdt_free:.2f} USDT ({capital_percent}%)"
            )

            # 3. Send Market Buy Order
            buy_order = binance_service.place_market_buy(symbol=symbol, quote_quantity=invest_amount)

            # Compute filled quantity and average price
            fills = buy_order.get("fills", [])
            executed_qty = float(buy_order.get("executedQty", 0.0))
            cummulative_quote_qty = float(buy_order.get("cummulativeQuoteQty", 0.0))

            if executed_qty <= 0:
                raise Exception("Zero quantity executed on market buy.")

            if fills:
                total_cost = sum(float(f["price"]) * float(f["qty"]) for f in fills)
                total_qty = sum(float(f["qty"]) for f in fills)
                avg_price = total_cost / total_qty if total_qty > 0 else float(fills[0]["price"])
            else:
                avg_price = cummulative_quote_qty / executed_qty if executed_qty > 0 else binance_service.get_ticker_price(symbol)

            await broadcaster.broadcast(
                "SUCCESS",
                f"✅ BUY Order Filled: {executed_qty} {base_asset} @ ${avg_price:,.4f} (Total: ${cummulative_quote_qty:,.2f})",
                {"order_id": buy_order.get("orderId"), "fills": fills}
            )

            # 4. Instant Post-Buy Balance Sync and UI broadcast
            await asyncio.sleep(0.3)
            fresh_balances = binance_service.get_balances()
            await broadcaster.broadcast_event("balance_updated", fresh_balances)

            # 5. Place OCO Order for Take Profit and Stop Loss
            oco_result = None
            if tp_percent > 0 and sl_percent > 0:
                actual_free_qty = binance_service.get_asset_free_balance(base_asset)
                sellable_qty = min(executed_qty, actual_free_qty) if actual_free_qty > 0 else executed_qty

                tp_price = avg_price * (1.0 + (tp_percent / 100.0))
                sl_stop_price = avg_price * (1.0 - (sl_percent / 100.0))
                sl_limit_price = sl_stop_price * (1.0 - (settings.slippage_buffer_percent / 100.0))

                await broadcaster.broadcast(
                    "INFO",
                    f"🎯 Placing OCO Order: Target TP (+{tp_percent}%): ${tp_price:,.4f} | Stop Loss SL (-{sl_percent}%): ${sl_stop_price:,.4f}"
                )

                try:
                    oco_result = binance_service.place_oco_sell(
                        symbol=symbol,
                        quantity=sellable_qty,
                        tp_price=tp_price,
                        sl_stop_price=sl_stop_price,
                        sl_limit_price=sl_limit_price
                    )
                    await broadcaster.broadcast(
                        "SUCCESS",
                        f"🛡️ OCO Protection Activated! Orders placed on Binance.",
                        {"order_list_id": oco_result.get("orderListId")}
                    )
                except Exception as oco_err:
                    await broadcaster.broadcast(
                        "WARNING",
                        f"⚠️ Buy filled, but OCO placement failed: {str(oco_err)}"
                    )

            # Push balance update again after OCO locking
            final_balances = binance_service.get_balances()
            await broadcaster.broadcast_event("balance_updated", final_balances)

            return {
                "status": "success",
                "action": "BUY",
                "symbol": symbol,
                "executed_qty": executed_qty,
                "avg_price": avg_price,
                "buy_order": buy_order,
                "oco_order": oco_result
            }

        except Exception as e:
            msg = f"Error during BUY execution for {symbol}: {str(e)}"
            await broadcaster.broadcast("ERROR", msg)
            return {"status": "error", "message": msg}

    async def _execute_sell(self, symbol: str, base_asset: str) -> Dict[str, Any]:
        try:
            # 1. Cancel open orders to unlock coins for immediate sell
            canceled = binance_service.cancel_open_orders_for_symbol(symbol)
            if canceled:
                await broadcaster.broadcast("INFO", f"Cancelled {len(canceled)} pending orders to free balance for sell.")

            # 2. Check coin balance
            await asyncio.sleep(0.4)
            coin_balance = binance_service.get_asset_free_balance(base_asset)
            ticker_price = binance_service.get_ticker_price(symbol)
            usd_value = coin_balance * ticker_price

            if usd_value < 5.0 or coin_balance <= 0:
                msg = f"No sufficient balance of {base_asset} to SELL (Available: {coin_balance} ~ ${usd_value:.2f})"
                await broadcaster.broadcast("WARNING", msg)
                return {"status": "warning", "message": msg}

            await broadcaster.broadcast(
                "INFO",
                f"🔴 Executing Market SELL for 100% of balance: {coin_balance} {base_asset} (~${usd_value:,.2f})"
            )

            # 3. Execute Market Sell
            sell_order = binance_service.place_market_sell(symbol=symbol, quantity=coin_balance)

            executed_qty = float(sell_order.get("executedQty", 0.0))
            cummulative_quote_qty = float(sell_order.get("cummulativeQuoteQty", 0.0))

            await broadcaster.broadcast(
                "SUCCESS",
                f"✅ Position Closed: Sold {executed_qty} {base_asset} for ${cummulative_quote_qty:,.2f} USDT",
                {"order_id": sell_order.get("orderId")}
            )

            # 4. Instant Post-Sell Balance Sync
            # Wait 0.3s for settlement, then immediately push fresh USDT balance to UI
            await asyncio.sleep(0.3)
            fresh_balances = binance_service.get_balances()
            await broadcaster.broadcast_event("balance_updated", fresh_balances)
            await broadcaster.broadcast("INFO", f"💰 Updated USDT Balance: {fresh_balances.get('usdt_free', 0.0):,.2f} USDT")

            return {
                "status": "success",
                "action": "SELL",
                "symbol": symbol,
                "executed_qty": executed_qty,
                "quote_received": cummulative_quote_qty,
                "sell_order": sell_order
            }

        except Exception as e:
            msg = f"Error during SELL execution for {symbol}: {str(e)}"
            await broadcaster.broadcast("ERROR", msg)
            return {"status": "error", "message": msg}

trading_engine = TradingEngine()

import os
import json
import asyncio
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.config import settings
from app.logger import broadcaster
from app.binance_client import binance_service

STATE_FILE = Path(__file__).resolve().parent.parent / "zone_grid_state.json"

class ZoneLevel:
    def __init__(
        self,
        index: int,
        price: float,
        target_price: float,
        is_holding: bool = False,
        bought_qty: float = 0.0,
        buy_price: float = 0.0,
        total_cost: float = 0.0,
        buy_order_id: Optional[int] = None,
        last_trade_time: str = ""
    ):
        self.index = index
        self.price = price
        self.target_price = target_price
        self.is_holding = is_holding
        self.bought_qty = bought_qty
        self.buy_price = buy_price
        self.total_cost = total_cost
        self.buy_order_id = buy_order_id
        self.last_trade_time = last_trade_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "price": self.price,
            "target_price": self.target_price,
            "is_holding": self.is_holding,
            "bought_qty": self.bought_qty,
            "buy_price": self.buy_price,
            "total_cost": self.total_cost,
            "buy_order_id": self.buy_order_id,
            "last_trade_time": self.last_trade_time
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ZoneLevel":
        return cls(
            index=int(data["index"]),
            price=float(data["price"]),
            target_price=float(data["target_price"]),
            is_holding=bool(data.get("is_holding", False)),
            bought_qty=float(data.get("bought_qty", 0.0)),
            buy_price=float(data.get("buy_price", 0.0)),
            total_cost=float(data.get("total_cost", 0.0)),
            buy_order_id=data.get("buy_order_id"),
            last_trade_time=data.get("last_trade_time", "")
        )


class ZoneGridEngine:
    def __init__(self):
        self.symbol: str = "BTCUSDT"
        self.total_capital: float = 200.0
        self.num_zones: int = 10
        self.zone_step_percent: float = 1.0
        self.base_price: float = 0.0
        self.stop_loss_type: str = "TOTAL"  # "TOTAL", "PER_ZONE", "NONE"
        self.stop_loss_percent: float = 10.0
        self.is_running: bool = False
        self.levels: List[ZoneLevel] = []
        self.last_price: float = 0.0
        self._watcher_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.load_state()

    @property
    def per_zone_capital(self) -> float:
        if self.num_zones <= 0:
            return 20.0
        return round(self.total_capital / self.num_zones, 2)

    def generate_levels(self, base_price: float):
        """
        Generate N levels starting from base_price upwards by zone_step_percent
        Level 1 = base_price
        Level 2 = base_price * (1 + step%)
        ...
        """
        self.base_price = base_price
        self.levels = []
        step_factor = 1.0 + (self.zone_step_percent / 100.0)

        current_p = base_price
        for i in range(1, self.num_zones + 1):
            next_p = current_p * step_factor
            lvl = ZoneLevel(
                index=i,
                price=round(current_p, 4),
                target_price=round(next_p, 4),
                is_holding=False
            )
            self.levels.append(lvl)
            current_p = next_p

        self.save_state()

    def configure(
        self,
        symbol: str,
        total_capital: float,
        num_zones: int,
        zone_step_percent: float,
        base_price: float,
        stop_loss_type: str,
        stop_loss_percent: float
    ):
        self.symbol = symbol.upper().replace("/", "").replace(" ", "").replace("-", "")
        self.total_capital = max(10.0, float(total_capital))
        self.num_zones = max(2, min(50, int(num_zones)))
        self.zone_step_percent = max(0.1, float(zone_step_percent))
        self.stop_loss_type = stop_loss_type.upper()
        self.stop_loss_percent = max(0.5, float(stop_loss_percent))

        # Generate levels if base_price given
        if base_price > 0:
            self.generate_levels(base_price)
        self.save_state()

    def save_state(self):
        try:
            data = {
                "symbol": self.symbol,
                "total_capital": self.total_capital,
                "num_zones": self.num_zones,
                "zone_step_percent": self.zone_step_percent,
                "base_price": self.base_price,
                "stop_loss_type": self.stop_loss_type,
                "stop_loss_percent": self.stop_loss_percent,
                "is_running": self.is_running,
                "last_price": self.last_price,
                "levels": [lvl.to_dict() for lvl in self.levels]
            }
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            broadcaster.log_sync("ERROR", f"Error saving zone grid state: {str(e)}")

    def load_state(self):
        if not STATE_FILE.exists():
            return
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.symbol = data.get("symbol", "BTCUSDT")
            self.total_capital = float(data.get("total_capital", 200.0))
            self.num_zones = int(data.get("num_zones", 10))
            self.zone_step_percent = float(data.get("zone_step_percent", 1.0))
            self.base_price = float(data.get("base_price", 0.0))
            self.stop_loss_type = data.get("stop_loss_type", "TOTAL")
            self.stop_loss_percent = float(data.get("stop_loss_percent", 10.0))
            self.is_running = bool(data.get("is_running", False))
            self.last_price = float(data.get("last_price", 0.0))
            self.levels = [ZoneLevel.from_dict(d) for d in data.get("levels", [])]
        except Exception as e:
            broadcaster.log_sync("WARNING", f"Could not load zone grid state: {str(e)}")

    async def start(self):
        if not binance_service.is_connected():
            raise Exception("Cannot start Zone Bot: Binance is not connected. Add API keys first.")

        if not self.levels or len(self.levels) != self.num_zones:
            # Fetch current ticker price to initialize levels if not already configured
            cur_price = binance_service.get_ticker_price(self.symbol)
            self.generate_levels(cur_price)

        self.is_running = True
        self.save_state()
        await broadcaster.broadcast(
            "SUCCESS",
            f"🚀 Shark Zone Grid STARTED for {self.symbol}! Total Capital: ${self.total_capital:,.2f} ({self.num_zones} levels @ ${self.per_zone_capital:,.2f} each | Gap: {self.zone_step_percent}%)"
        )

        if not self._watcher_task or self._watcher_task.done():
            self._watcher_task = asyncio.create_task(self._watch_loop())

    async def stop(self):
        self.is_running = False
        self.save_state()
        if self._watcher_task and not self._watcher_task.done():
            self._watcher_task.cancel()
        await broadcaster.broadcast("WARNING", f"⏸️ Shark Zone Grid for {self.symbol} has been PAUSED.")

    async def emergency_liquidate_all(self) -> Dict[str, Any]:
        """
        Emergency close all active holding levels at market price.
        """
        async with self._lock:
            sold_count = 0
            total_qty_to_sell = 0.0
            for lvl in self.levels:
                if lvl.is_holding and lvl.bought_qty > 0:
                    total_qty_to_sell += lvl.bought_qty
                    lvl.is_holding = False
                    lvl.bought_qty = 0.0
                    lvl.buy_price = 0.0
                    lvl.total_cost = 0.0
                    sold_count += 1

            self.is_running = False
            self.save_state()

            if total_qty_to_sell > 0:
                await broadcaster.broadcast(
                    "WARNING",
                    f"🚨 EMERGENCY LIQUIDATION: Selling {total_qty_to_sell:.6f} across {sold_count} active levels for {self.symbol}..."
                )
                try:
                    res = binance_service.place_market_sell(self.symbol, total_qty_to_sell)
                    await broadcaster.broadcast("SUCCESS", f"✅ Emergency liquidation completed! Orders closed on Binance.")
                    return {"status": "success", "sold_count": sold_count, "order": res}
                except Exception as e:
                    await broadcaster.broadcast("ERROR", f"Failed to execute emergency market sell: {str(e)}")
                    return {"status": "error", "message": str(e)}

            await broadcaster.broadcast("INFO", "Emergency liquidate called, but no active positions were holding.")
            return {"status": "success", "sold_count": 0}

    async def _watch_loop(self):
        """
        Continuous market price polling and execution watcher
        """
        while self.is_running:
            try:
                if not binance_service.is_connected():
                    await asyncio.sleep(5)
                    continue

                current_price = binance_service.get_ticker_price(self.symbol)
                await self.on_price_tick(current_price)
                await asyncio.sleep(1.5)  # 1.5s interval is fast and well within Binance rate limits

            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log without flooding
                await asyncio.sleep(3)

    async def on_price_tick(self, current_price: float):
        """
        Core State Machine: Evaluates price movement across independent zones
        """
        async with self._lock:
            prev_price = self.last_price if self.last_price > 0 else current_price
            self.last_price = current_price

            # 1. Check Stop Losses first
            await self._check_stop_loss(current_price)
            if not self.is_running:
                return

            # Tolerance band around level line (e.g. 0.15% or price crossing)
            band = self.zone_step_percent * 0.20

            # 2. Iterate levels
            for i, lvl in enumerate(self.levels):
                lvl_idx = lvl.index
                lvl_price = lvl.price
                target_p = lvl.target_price

                # Check if current price is within touch range or crossed through lvl_price
                has_touched = (
                    abs(current_price - lvl_price) / lvl_price <= (band / 100.0)
                    or (prev_price < lvl_price <= current_price)
                    or (prev_price > lvl_price >= current_price)
                )

                if not has_touched:
                    # Also check if target price hit for a holding level!
                    if lvl.is_holding and current_price >= target_p:
                        # Price reached or exceeded target price for this level
                        await self._sell_level(lvl, current_price, reason="TP_HIT")
                    continue

                # The price is touching / crossing Level lvl_idx!
                is_rising = current_price >= prev_price

                # ========================================================
                # CASE A: RISING SCENARIO (الصعود)
                # ========================================================
                if is_rising:
                    # 1. Check if previous level (lvl_idx - 1) is holding:
                    # If so, SELL it immediately for profit! (+1% achieved)
                    if lvl_idx > 1:
                        prev_lvl = self.levels[lvl_idx - 2]
                        if prev_lvl.is_holding:
                            await self._sell_level(prev_lvl, current_price, reason="TP_REACHED_HIGHER_LEVEL")

                    # 2. Check if current level is free to buy:
                    # Buy from current level with target = next level!
                    if not lvl.is_holding:
                        await self._buy_level(lvl, current_price)
                    else:
                        # Already holding: do NOT duplicate buy! (One-shot rule)
                        pass

                # ========================================================
                # CASE B: FALLING SCENARIO (الهبوط والتراجع)
                # ========================================================
                else:
                    # Price is falling and touched Level lvl_idx:
                    # If this level is free (not holding), BUY it!
                    if not lvl.is_holding:
                        await self._buy_level(lvl, current_price)
                    else:
                        # STRICT ONE-SHOT RULE:
                        # Level already holds a trade that hasn't sold yet.
                        # NEVER re-buy at this level until previous position exits!
                        pass

            self.save_state()

    async def _buy_level(self, lvl: ZoneLevel, current_price: float):
        """
        Execute dedicated $20 buy for this level
        """
        amount = self.per_zone_capital
        lvl_num = lvl.index

        await broadcaster.broadcast(
            "INFO",
            f"🎯 [Level {lvl_num}] Price touched ${current_price:,.4f} -> Executing BUY for ${amount:.2f} (Target: Level {lvl_num+1} @ ${lvl.target_price:,.4f})"
        )

        try:
            buy_order = binance_service.place_market_buy(self.symbol, quote_quantity=amount)
            executed_qty = float(buy_order.get("executedQty", 0.0))
            cummulative_cost = float(buy_order.get("cummulativeQuoteQty", 0.0))

            fills = buy_order.get("fills", [])
            if fills:
                avg_price = sum(float(f["price"]) * float(f["qty"]) for f in fills) / executed_qty
            else:
                avg_price = cummulative_cost / executed_qty if executed_qty > 0 else current_price

            # Update level state to HOLDING
            lvl.is_holding = True
            lvl.bought_qty = executed_qty
            lvl.buy_price = avg_price
            lvl.total_cost = cummulative_cost if cummulative_cost > 0 else amount
            lvl.buy_order_id = buy_order.get("orderId")
            lvl.last_trade_time = time.strftime("%H:%M:%S")

            await broadcaster.broadcast(
                "SUCCESS",
                f"✅ [Level {lvl_num} LOCKED 🔒] Bought {executed_qty} @ ${avg_price:,.4f} | Target: ${lvl.target_price:,.4f} (+{self.zone_step_percent}%)"
            )

            # Sync balance to UI
            try:
                fresh_bal = binance_service.get_balances()
                await broadcaster.broadcast_event("balance_updated", fresh_bal)
            except Exception:
                pass

        except Exception as e:
            await broadcaster.broadcast("ERROR", f"❌ [Level {lvl_num}] BUY failed: {str(e)}")

    async def _sell_level(self, lvl: ZoneLevel, current_price: float, reason: str = "TP"):
        """
        Execute sell for this level, taking profit and freeing the level
        """
        lvl_num = lvl.index
        qty_to_sell = lvl.bought_qty

        if qty_to_sell <= 0:
            lvl.is_holding = False
            return

        pnl_usd = (current_price - lvl.buy_price) * qty_to_sell
        pnl_percent = ((current_price - lvl.buy_price) / lvl.buy_price) * 100.0 if lvl.buy_price > 0 else 0.0

        await broadcaster.broadcast(
            "INFO",
            f"💰 [Level {lvl_num}] Target reached! Selling {qty_to_sell} @ ${current_price:,.4f} | Est. PnL: +{pnl_percent:.2f}% (+${pnl_usd:.2f})"
        )

        try:
            sell_order = binance_service.place_market_sell(self.symbol, quantity=qty_to_sell)
            executed_qty = float(sell_order.get("executedQty", 0.0))
            received_quote = float(sell_order.get("cummulativeQuoteQty", 0.0))

            # Mark level as UNLOCKED / FREE
            lvl.is_holding = False
            lvl.bought_qty = 0.0
            lvl.buy_price = 0.0
            lvl.total_cost = 0.0
            lvl.buy_order_id = None
            lvl.last_trade_time = time.strftime("%H:%M:%S")

            await broadcaster.broadcast(
                "SUCCESS",
                f"🎉 [Level {lvl_num} UNLOCKED 🔓] Profit Locked! Received ${received_quote:,.2f} USDT (+{pnl_percent:.2f}%). Level is now FREE for new cycles."
            )

            # Sync balance to UI
            try:
                fresh_bal = binance_service.get_balances()
                await broadcaster.broadcast_event("balance_updated", fresh_bal)
            except Exception:
                pass

        except Exception as e:
            await broadcaster.broadcast("ERROR", f"❌ [Level {lvl_num}] SELL failed: {str(e)}")

    async def _check_stop_loss(self, current_price: float):
        """
        Evaluate Stop Loss (Option A: Total Portfolio vs Option B: Per-Zone)
        """
        if self.stop_loss_type == "NONE" or self.stop_loss_percent <= 0:
            return

        holding_levels = [lvl for lvl in self.levels if lvl.is_holding and lvl.bought_qty > 0]
        if not holding_levels:
            return

        # ------------------------------------------------------------------
        # OPTION A: TOTAL PORTFOLIO STOP LOSS
        # ------------------------------------------------------------------
        if self.stop_loss_type == "TOTAL":
            total_invested = sum(lvl.total_cost for lvl in holding_levels)
            total_current_val = sum(lvl.bought_qty * current_price for lvl in holding_levels)
            total_unrealized_pnl = total_current_val - total_invested

            # Stop Loss threshold based on total allocated capital
            sl_threshold_usd = self.total_capital * (self.stop_loss_percent / 100.0)

            if total_unrealized_pnl <= -sl_threshold_usd:
                await broadcaster.broadcast(
                    "ERROR",
                    f"🛑 [TOTAL STOP LOSS TRIGGERED] Cumulative loss hit -${abs(total_unrealized_pnl):.2f} (Threshold: -${sl_threshold_usd:.2f} / -{self.stop_loss_percent}%). Executing emergency exit to protect capital!"
                )
                await self.emergency_liquidate_all()
                self.is_running = False
                self.save_state()

        # ------------------------------------------------------------------
        # OPTION B: PER-ZONE INDEPENDENT STOP LOSS
        # ------------------------------------------------------------------
        elif self.stop_loss_type == "PER_ZONE":
            for lvl in holding_levels:
                if lvl.buy_price <= 0:
                    continue
                drop_pct = ((lvl.buy_price - current_price) / lvl.buy_price) * 100.0
                if drop_pct >= self.stop_loss_percent:
                    loss_usd = (lvl.buy_price - current_price) * lvl.bought_qty
                    await broadcaster.broadcast(
                        "WARNING",
                        f"⚠️ [Level {lvl.index} STOP LOSS] Price dropped {drop_pct:.2f}% below entry. Closing Level {lvl.index} position (-${loss_usd:.2f}) and unlocking level."
                    )
                    try:
                        binance_service.place_market_sell(self.symbol, lvl.bought_qty)
                        lvl.is_holding = False
                        lvl.bought_qty = 0.0
                        lvl.buy_price = 0.0
                        lvl.total_cost = 0.0
                        lvl.last_trade_time = time.strftime("%H:%M:%S")
                        await broadcaster.broadcast("INFO", f"🔓 Level {lvl.index} has been reset and unlocked.")
                    except Exception as sl_err:
                        await broadcaster.broadcast("ERROR", f"Failed to execute SL for Level {lvl.index}: {str(sl_err)}")

    def get_full_status(self) -> Dict[str, Any]:
        """
        Returns full UI status payload
        """
        holding_count = sum(1 for lvl in self.levels if lvl.is_holding)
        total_invested = sum(lvl.total_cost for lvl in self.levels if lvl.is_holding)

        current_val = sum(lvl.bought_qty * self.last_price for lvl in self.levels if lvl.is_holding) if self.last_price > 0 else total_invested
        unrealized_pnl = current_val - total_invested

        return {
            "symbol": self.symbol,
            "total_capital": self.total_capital,
            "num_zones": self.num_zones,
            "per_zone_capital": self.per_zone_capital,
            "zone_step_percent": self.zone_step_percent,
            "base_price": self.base_price,
            "stop_loss_type": self.stop_loss_type,
            "stop_loss_percent": self.stop_loss_percent,
            "is_running": self.is_running,
            "last_price": self.last_price,
            "active_trades_count": holding_count,
            "total_invested": round(total_invested, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "levels": [
                {
                    **lvl.to_dict(),
                    "current_pnl": round((self.last_price - lvl.buy_price) * lvl.bought_qty, 2) if (lvl.is_holding and self.last_price > 0) else 0.0,
                    "current_pnl_pct": round(((self.last_price - lvl.buy_price) / lvl.buy_price) * 100.0, 2) if (lvl.is_holding and lvl.buy_price > 0 and self.last_price > 0) else 0.0
                }
                for lvl in self.levels
            ]
        }

zone_grid_engine = ZoneGridEngine()

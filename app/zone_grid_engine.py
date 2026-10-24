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
        sell_order_id: Optional[int] = None,
        is_partial: bool = False,
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
        self.sell_order_id = sell_order_id
        self.is_partial = is_partial
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
            "sell_order_id": self.sell_order_id,
            "is_partial": self.is_partial,
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
            sell_order_id=data.get("sell_order_id"),
            is_partial=bool(data.get("is_partial", False)),
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
        self.open_range: bool = True       # النطاق المفتوح المتحرك (Trailing Infinity Grid)
        self.demo_mode: bool = False       # وضع الحساب التجريبي الديمو
        self.demo_balance: float = 10000.0 # رصيد الديمو 10,000 دولار
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
        stop_loss_percent: float,
        open_range: bool = True,
        demo_mode: bool = False
    ):
        self.symbol = symbol.upper().replace("/", "").replace(" ", "").replace("-", "")
        self.total_capital = max(10.0, float(total_capital))
        self.num_zones = max(2, min(50, int(num_zones)))
        self.zone_step_percent = max(0.1, float(zone_step_percent))
        self.stop_loss_type = stop_loss_type.upper()
        self.stop_loss_percent = max(0.5, float(stop_loss_percent))
        self.open_range = bool(open_range)
        self.demo_mode = bool(demo_mode)

        if base_price > 0:
            self.generate_levels(base_price)
        self.save_state()

    def reset_demo_balance(self, amount: float = 10000.0):
        self.demo_balance = float(amount)
        for lvl in self.levels:
            lvl.is_holding = False
            lvl.bought_qty = 0.0
            lvl.buy_price = 0.0
            lvl.total_cost = 0.0
            lvl.buy_order_id = None
            lvl.sell_order_id = None
            lvl.is_partial = False
        self.save_state()
        broadcaster.log_sync("SUCCESS", f"🎮 تم إعادة تعيين رصيد الحساب التجريبي إلى ${amount:,.2f} USDT بنجاح!")

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
                "open_range": self.open_range,
                "demo_mode": self.demo_mode,
                "demo_balance": self.demo_balance,
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
            self.open_range = bool(data.get("open_range", True))
            self.demo_mode = bool(data.get("demo_mode", False))
            self.demo_balance = float(data.get("demo_balance", 10000.0))
            self.is_running = bool(data.get("is_running", False))
            self.last_price = float(data.get("last_price", 0.0))
            self.levels = [ZoneLevel.from_dict(d) for d in data.get("levels", [])]
        except Exception as e:
            broadcaster.log_sync("WARNING", f"Could not load zone grid state: {str(e)}")

    async def start(self):
        if not self.demo_mode and not binance_service.is_connected():
            raise Exception("Cannot start Real Bot: Binance is not connected. Add API keys first or switch to Demo Mode.")

        cur_price = binance_service.get_ticker_price(self.symbol)
        if not self.levels or len(self.levels) != self.num_zones:
            self.generate_levels(cur_price)

        self.is_running = True
        self.save_state()

        mode_str = "🎮 DEMO PAPER TRADING ($10,000)" if self.demo_mode else "⚡ LIVE BINANCE SPOT"
        range_str = "🌐 OPEN RANGE (Trailing Infinity)" if self.open_range else "🔒 FIXED RANGE"
        await broadcaster.broadcast(
            "SUCCESS",
            f"🚀 Shark Zone Grid STARTED for {self.symbol}! Mode: {mode_str} | Range: {range_str} | Capital: ${self.total_capital:,.2f} ({self.num_zones} levels @ ${self.per_zone_capital:,.2f} each | Gap: {self.zone_step_percent}%)"
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
                    # Cancel any pre-placed sell or buy orders
                    if not self.demo_mode:
                        if lvl.sell_order_id:
                            binance_service.cancel_order(self.symbol, lvl.sell_order_id)
                        if lvl.buy_order_id:
                            binance_service.cancel_order(self.symbol, lvl.buy_order_id)
                    lvl.is_holding = False
                    lvl.bought_qty = 0.0
                    lvl.buy_price = 0.0
                    lvl.total_cost = 0.0
                    lvl.sell_order_id = None
                    lvl.buy_order_id = None
                    sold_count += 1

            self.is_running = False
            self.save_state()

            if total_qty_to_sell > 0:
                if self.demo_mode:
                    cur_p = binance_service.get_ticker_price(self.symbol)
                    recovered = total_qty_to_sell * cur_p
                    self.demo_balance += recovered
                    self.save_state()
                    await broadcaster.broadcast("SUCCESS", f"🎮 [DEMO] Emergency liquidated {sold_count} levels. Recovered ${recovered:,.2f} USDT to Demo Wallet.")
                    return {"status": "success", "sold_count": sold_count}
                else:
                    await broadcaster.broadcast(
                        "WARNING",
                        f"🚨 EMERGENCY LIQUIDATION: Selling {total_qty_to_sell:.6f} across {sold_count} active levels for {self.symbol}..."
                    )
                    try:
                        res = binance_service.place_market_sell(self.symbol, total_qty_to_sell)
                        await broadcaster.broadcast("SUCCESS", f"✅ Emergency liquidation completed on Binance Spot.")
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
                current_price = binance_service.get_ticker_price(self.symbol)
                await self.on_price_tick(current_price)
                await asyncio.sleep(1.2)

            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(2.5)

    async def on_price_tick(self, current_price: float):
        """
        Core State Machine:
        - Open Range Trailing (expands upwards if price keeps rising)
        - Dual-action on rise
        - Pre-placed Limit Sell order execution
        - Partial fill cancel & sell handling
        - Strict one-shot per level rule
        """
        async with self._lock:
            prev_price = self.last_price if self.last_price > 0 else current_price
            self.last_price = current_price

            # ------------------------------------------------------------------
            # 1. OPEN RANGE ENGINE: DYNAMIC TRAILING UPWARDS
            # ------------------------------------------------------------------
            if self.open_range and len(self.levels) > 0:
                top_level = self.levels[-1]
                # If price is rising and touching/exceeding top level's target price:
                if current_price >= top_level.target_price:
                    step_factor = 1.0 + (self.zone_step_percent / 100.0)
                    new_idx = len(self.levels) + 1
                    new_price = round(top_level.target_price, 4)
                    new_target = round(new_price * step_factor, 4)

                    new_lvl = ZoneLevel(
                        index=new_idx,
                        price=new_price,
                        target_price=new_target,
                        is_holding=False
                    )
                    self.levels.append(new_lvl)
                    await broadcaster.broadcast(
                        "INFO",
                        f"🌐 [OPEN RANGE TRAILING] Price broke above top level! Added Level {new_idx:02d} @ ${new_price:,.4f} (Target: ${new_target:,.4f}) 🚀"
                    )

            # 2. Check Stop Losses
            await self._check_stop_loss(current_price)
            if not self.is_running:
                return

            # Tolerance band around level line (e.g. 0.20% of step)
            band = self.zone_step_percent * 0.20

            # 3. Check Level Triggers
            for i, lvl in enumerate(self.levels):
                lvl_idx = lvl.index
                lvl_price = lvl.price
                target_p = lvl.target_price

                # Check if target hit for holding level:
                if lvl.is_holding and current_price >= target_p:
                    await self._sell_level(lvl, current_price, reason="TARGET_HIT")
                    continue

                # Check if price is touching/crossing Level lvl_idx:
                has_touched = (
                    abs(current_price - lvl_price) / lvl_price <= (band / 100.0)
                    or (prev_price < lvl_price <= current_price)
                    or (prev_price > lvl_price >= current_price)
                )

                if not has_touched:
                    continue

                is_rising = current_price >= prev_price

                # ========================================================
                # CASE A: RISING SCENARIO (الصعود)
                # ========================================================
                if is_rising:
                    # 1. Previous level selling:
                    if lvl_idx > 1:
                        prev_lvl = self.levels[lvl_idx - 2]
                        if prev_lvl.is_holding:
                            await self._sell_level(prev_lvl, current_price, reason="TP_REACHED_HIGHER_LEVEL")

                    # 2. Current level buying:
                    if not lvl.is_holding:
                        # Max active concurrent trades safeguard:
                        active_count = sum(1 for x in self.levels if x.is_holding)
                        if active_count < self.num_zones:
                            await self._buy_level(lvl, current_price)

                # ========================================================
                # CASE B: FALLING SCENARIO (الهبوط والتراجع)
                # ========================================================
                else:
                    if not lvl.is_holding:
                        active_count = sum(1 for x in self.levels if x.is_holding)
                        if active_count < self.num_zones:
                            await self._buy_level(lvl, current_price)
                    else:
                        # STRICT ONE-SHOT RULE: Never re-buy a holding level!
                        pass

            self.save_state()

    async def _buy_level(self, lvl: ZoneLevel, current_price: float):
        """
        Execute dedicated buy for this level, and IMMEDIATELY pre-place limit sell order!
        """
        amount = self.per_zone_capital
        lvl_num = lvl.index

        prefix = "🎮 [DEMO]" if self.demo_mode else "⚡ [REAL]"
        await broadcaster.broadcast(
            "INFO",
            f"{prefix} Level {lvl_num:02d} touched @ ${current_price:,.4f} -> Executing BUY for ${amount:.2f} (Target: Level {lvl_num+1:02d} @ ${lvl.target_price:,.4f})"
        )

        # -------------------------------------------------------------
        # DEMO MODE EXECUTION
        # -------------------------------------------------------------
        if self.demo_mode:
            if self.demo_balance < amount:
                await broadcaster.broadcast("WARNING", f"🎮 [DEMO] Insufficient demo balance (${self.demo_balance:.2f}) to buy Level {lvl_num}.")
                return

            self.demo_balance -= amount
            executed_qty = amount / current_price
            lvl.is_holding = True
            lvl.bought_qty = executed_qty
            lvl.buy_price = current_price
            lvl.total_cost = amount
            lvl.buy_order_id = int(time.time() * 1000)
            lvl.sell_order_id = int(time.time() * 1000) + 1  # Pre-placed virtual limit sell
            lvl.is_partial = False
            lvl.last_trade_time = time.strftime("%H:%M:%S")

            await broadcaster.broadcast(
                "SUCCESS",
                f"✅ {prefix} Level {lvl_num:02d} LOCKED 🔒 | Bought {executed_qty:.6f} {self.symbol} @ ${current_price:,.4f} | Pre-placed Target Sell @ ${lvl.target_price:,.4f} (+{self.zone_step_percent}%) | Demo Wallet: ${self.demo_balance:,.2f}"
            )
            return

        # -------------------------------------------------------------
        # REAL BINANCE SPOT EXECUTION
        # -------------------------------------------------------------
        try:
            buy_order = binance_service.place_market_buy(self.symbol, quote_quantity=amount)
            executed_qty = float(buy_order.get("executedQty", 0.0))
            cummulative_cost = float(buy_order.get("cummulativeQuoteQty", 0.0))

            fills = buy_order.get("fills", [])
            if fills:
                avg_price = sum(float(f["price"]) * float(f["qty"]) for f in fills) / executed_qty
            else:
                avg_price = cummulative_cost / executed_qty if executed_qty > 0 else current_price

            # Check if partially filled
            is_partial = (cummulative_cost < amount * 0.95)

            lvl.is_holding = True
            lvl.bought_qty = executed_qty
            lvl.buy_price = avg_price
            lvl.total_cost = cummulative_cost if cummulative_cost > 0 else amount
            lvl.buy_order_id = buy_order.get("orderId")
            lvl.is_partial = is_partial
            lvl.last_trade_time = time.strftime("%H:%M:%S")

            await broadcaster.broadcast(
                "SUCCESS",
                f"✅ Level {lvl_num:02d} LOCKED 🔒 | Filled {executed_qty:.6f} @ ${avg_price:,.4f} (Total: ${cummulative_cost:,.2f})"
            )

            # IMMEDIATELY PRE-PLACE LIMIT SELL ORDER AT TARGET PRICE!
            try:
                sell_limit = binance_service.place_limit_sell(
                    symbol=self.symbol,
                    quantity=executed_qty,
                    price=lvl.target_price
                )
                lvl.sell_order_id = sell_limit.get("orderId")
                await broadcaster.broadcast(
                    "SUCCESS",
                    f"📌 [Level {lvl_num:02d}] Pre-placed Limit Sell order active on Binance @ ${lvl.target_price:,.4f} (Order #{lvl.sell_order_id})"
                )
            except Exception as limit_err:
                await broadcaster.broadcast(
                    "INFO",
                    f"ℹ️ [Level {lvl_num:02d}] Watcher will trigger Market Sell at target (${lvl.target_price:,.4f})."
                )

            # Sync live balance
            try:
                fresh_bal = binance_service.get_balances()
                await broadcaster.broadcast_event("balance_updated", fresh_bal)
            except Exception:
                pass

        except Exception as e:
            await broadcaster.broadcast("ERROR", f"❌ [Level {lvl_num:02d}] BUY failed: {str(e)}")

    async def _sell_level(self, lvl: ZoneLevel, current_price: float, reason: str = "TP"):
        """
        Execute sell for this level, taking profit, cancelling any remaining partial orders, and freeing the level
        """
        lvl_num = lvl.index
        qty_to_sell = lvl.bought_qty

        if qty_to_sell <= 0:
            lvl.is_holding = False
            return

        prefix = "🎮 [DEMO]" if self.demo_mode else "⚡ [REAL]"
        pnl_usd = (current_price - lvl.buy_price) * qty_to_sell
        pnl_percent = ((current_price - lvl.buy_price) / lvl.buy_price) * 100.0 if lvl.buy_price > 0 else 0.0

        await broadcaster.broadcast(
            "INFO",
            f"💰 {prefix} Level {lvl_num:02d} Target Reached! Selling {qty_to_sell:.6f} @ ${current_price:,.4f} | Est. PnL: +{pnl_percent:.2f}% (+${pnl_usd:.2f})"
        )

        # -------------------------------------------------------------
        # DEMO MODE SELL
        # -------------------------------------------------------------
        if self.demo_mode:
            revenue = qty_to_sell * current_price
            self.demo_balance += revenue

            lvl.is_holding = False
            lvl.bought_qty = 0.0
            lvl.buy_price = 0.0
            lvl.total_cost = 0.0
            lvl.buy_order_id = None
            lvl.sell_order_id = None
            lvl.is_partial = False
            lvl.last_trade_time = time.strftime("%H:%M:%S")

            await broadcaster.broadcast(
                "SUCCESS",
                f"🎉 {prefix} Level {lvl_num:02d} UNLOCKED 🔓 | Sold for ${revenue:,.2f} USDT (+{pnl_percent:.2f}%). Demo Wallet: ${self.demo_balance:,.2f}"
            )
            return

        # -------------------------------------------------------------
        # REAL BINANCE SPOT SELL (Handling Pre-Placed Orders & Partial Fills)
        # -------------------------------------------------------------
        try:
            # 1. If there was a partially filled buy order still open, cancel the remainder!
            if lvl.buy_order_id and lvl.is_partial:
                try:
                    binance_service.cancel_order(self.symbol, lvl.buy_order_id)
                    await broadcaster.broadcast("INFO", f"🧹 [Level {lvl_num:02d}] Cancelled remaining unfilled buy order #{lvl.buy_order_id}.")
                except Exception:
                    pass

            # 2. Check if pre-placed Limit Sell already filled on Binance:
            pre_placed_filled = False
            if lvl.sell_order_id:
                try:
                    order_status = binance_service.get_order(self.symbol, lvl.sell_order_id)
                    if order_status and order_status.get("status") == "FILLED":
                        pre_placed_filled = True
                        received_quote = float(order_status.get("cummulativeQuoteQty", 0.0))
                    elif order_status and order_status.get("status") in ("NEW", "PARTIALLY_FILLED"):
                        # Cancel limit order so we can execute immediate clean market sell
                        binance_service.cancel_order(self.symbol, lvl.sell_order_id)
                except Exception:
                    pass

            if not pre_placed_filled:
                # Execute Market Sell for exact holding quantity
                actual_free = binance_service.get_asset_free_balance(self.symbol.replace("USDT", ""))
                sell_qty = min(qty_to_sell, actual_free) if actual_free > 0 else qty_to_sell

                sell_order = binance_service.place_market_sell(self.symbol, quantity=sell_qty)
                received_quote = float(sell_order.get("cummulativeQuoteQty", 0.0))

            # Mark level as UNLOCKED / FREE
            lvl.is_holding = False
            lvl.bought_qty = 0.0
            lvl.buy_price = 0.0
            lvl.total_cost = 0.0
            lvl.buy_order_id = None
            lvl.sell_order_id = None
            lvl.is_partial = False
            lvl.last_trade_time = time.strftime("%H:%M:%S")

            await broadcaster.broadcast(
                "SUCCESS",
                f"🎉 [Level {lvl_num:02d} UNLOCKED 🔓] Profit Locked! Received ${received_quote:,.2f} USDT (+{pnl_percent:.2f}%). Level is now FREE for new cycles."
            )

            # Sync balance to UI
            try:
                fresh_bal = binance_service.get_balances()
                await broadcaster.broadcast_event("balance_updated", fresh_bal)
            except Exception:
                pass

        except Exception as e:
            await broadcaster.broadcast("ERROR", f"❌ [Level {lvl_num:02d}] SELL failed: {str(e)}")

    async def _check_stop_loss(self, current_price: float):
        """
        Evaluate Stop Loss (Option A: Total Portfolio vs Option B: Per-Zone)
        """
        if self.stop_loss_type == "NONE" or self.stop_loss_percent <= 0:
            return

        holding_levels = [lvl for lvl in self.levels if lvl.is_holding and lvl.bought_qty > 0]
        if not holding_levels:
            return

        # OPTION A: TOTAL PORTFOLIO STOP LOSS
        if self.stop_loss_type == "TOTAL":
            total_invested = sum(lvl.total_cost for lvl in holding_levels)
            total_current_val = sum(lvl.bought_qty * current_price for lvl in holding_levels)
            total_unrealized_pnl = total_current_val - total_invested

            sl_threshold_usd = self.total_capital * (self.stop_loss_percent / 100.0)

            if total_unrealized_pnl <= -sl_threshold_usd:
                await broadcaster.broadcast(
                    "ERROR",
                    f"🛑 [TOTAL STOP LOSS TRIGGERED] Cumulative loss reached -${abs(total_unrealized_pnl):.2f} (Threshold: -${sl_threshold_usd:.2f} / -{self.stop_loss_percent}%). Executing emergency exit to protect capital!"
                )
                await self.emergency_liquidate_all()
                self.is_running = False
                self.save_state()

        # OPTION B: PER-ZONE INDEPENDENT STOP LOSS
        elif self.stop_loss_type == "PER_ZONE":
            for lvl in holding_levels:
                if lvl.buy_price <= 0:
                    continue
                drop_pct = ((lvl.buy_price - current_price) / lvl.buy_price) * 100.0
                if drop_pct >= self.stop_loss_percent:
                    loss_usd = (lvl.buy_price - current_price) * lvl.bought_qty
                    await broadcaster.broadcast(
                        "WARNING",
                        f"⚠️ [Level {lvl.index:02d} STOP LOSS] Price dropped {drop_pct:.2f}% below entry. Closing Level {lvl.index:02d} position (-${loss_usd:.2f}) and unlocking level."
                    )
                    if self.demo_mode:
                        revenue = lvl.bought_qty * current_price
                        self.demo_balance += revenue
                        lvl.is_holding = False
                        lvl.bought_qty = 0.0
                        lvl.buy_price = 0.0
                        lvl.total_cost = 0.0
                    else:
                        try:
                            if lvl.sell_order_id:
                                binance_service.cancel_order(self.symbol, lvl.sell_order_id)
                            binance_service.place_market_sell(self.symbol, lvl.bought_qty)
                            lvl.is_holding = False
                            lvl.bought_qty = 0.0
                            lvl.buy_price = 0.0
                            lvl.total_cost = 0.0
                        except Exception as sl_err:
                            await broadcaster.broadcast("ERROR", f"Failed to execute SL for Level {lvl.index:02d}: {str(sl_err)}")

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
            "open_range": self.open_range,
            "demo_mode": self.demo_mode,
            "demo_balance": round(self.demo_balance, 2),
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

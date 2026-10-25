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

def get_precision(price: float) -> int:
    """
    Returns decimal precision:
    - 5 decimal places for standard prices (user requirement: 5 digits after comma)
    - Up to 8 decimal places for micro-value coins (< 0.0001 e.g. PEPE, SHIB)
    """
    if price <= 0:
        return 5
    if price < 0.0001:
        return 8
    elif price < 0.01:
        return 6
    return 5

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
        self.capital_divisions: int = 10   # رأس المال مقسم إلى 10 أجزاء فقط (10 صفقات كحد أقصى)
        self.zones_above: int = 100
        self.zones_below: int = 100
        self.num_zones: int = 200  # zones_above + zones_below (مستويات الشارت)
        self.custom_per_zone_capital: Optional[float] = 20.0
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
        self.trade_history: List[Dict[str, Any]] = []
        self._watcher_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.load_state()

    @property
    def per_zone_capital(self) -> float:
        """
        رأس مال الصفقة الواحدة:
        يُقسم رأس المال على عدد أجزاء رأس المال (10 افتراضياً)،
        ولا يُقسم أبداً على عدد مستويات الشارت (200)!
        """
        if self.custom_per_zone_capital and self.custom_per_zone_capital > 0:
            return round(self.custom_per_zone_capital, 2)
        divs = self.capital_divisions if (self.capital_divisions and self.capital_divisions > 0) else 10
        return round(max(5.0, self.total_capital / divs), 2)

    @property
    def max_active_trades(self) -> int:
        """
        أقصى عدد صفقات نشطة مفتوحة بالتزامن:
        لا يمكن فتح أكثر من 10 صفقات (أو عدد الأجزاء المحددة).
        """
        if self.per_zone_capital <= 0:
            return self.capital_divisions if self.capital_divisions > 0 else 10
        return max(1, int(self.total_capital / self.per_zone_capital))

    def generate_levels(self, base_price: float):
        """
        Generate complete zone mesh centered around base_price:
        ~100 zones below and ~100 zones above.
        Prices formatted with 5 decimal places (or 8 for micro-tokens).
        """
        prec = get_precision(base_price)
        self.base_price = round(base_price, prec)
        self.levels = []
        step_factor = 1.0 + (self.zone_step_percent / 100.0)

        # Lowest starting price: base_price / (step_factor ^ zones_below)
        lowest_p = self.base_price / (step_factor ** self.zones_below)

        total_zones = self.zones_below + self.zones_above
        current_p = lowest_p
        for i in range(1, total_zones + 1):
            next_p = current_p * step_factor
            lvl = ZoneLevel(
                index=i,
                price=round(current_p, prec),
                target_price=round(next_p, prec),
                is_holding=False
            )
            self.levels.append(lvl)
            current_p = next_p

        self.num_zones = len(self.levels)
        self.save_state()

    def configure(
        self,
        symbol: str,
        total_capital: float,
        num_zones: Optional[int] = None,
        zone_step_percent: float = 1.0,
        base_price: float = 0.0,
        stop_loss_type: str = "TOTAL",
        stop_loss_percent: float = 10.0,
        open_range: bool = True,
        demo_mode: bool = False,
        zones_above: int = 100,
        zones_below: int = 100,
        per_zone_capital: Optional[float] = 20.0,
        capital_divisions: Optional[int] = 10
    ):
        self.symbol = symbol.upper().replace("/", "").replace(" ", "").replace("-", "")
        self.total_capital = max(10.0, float(total_capital))
        self.capital_divisions = max(1, int(capital_divisions)) if capital_divisions else 10
        self.zones_above = max(5, min(300, int(zones_above)))
        self.zones_below = max(5, min(300, int(zones_below)))
        self.num_zones = self.zones_above + self.zones_below
        self.zone_step_percent = max(0.01, float(zone_step_percent))
        self.stop_loss_type = stop_loss_type.upper()
        self.stop_loss_percent = max(0.5, float(stop_loss_percent))
        self.open_range = bool(open_range)
        self.demo_mode = bool(demo_mode)
        if per_zone_capital and float(per_zone_capital) > 0:
            self.custom_per_zone_capital = float(per_zone_capital)
        else:
            self.custom_per_zone_capital = round(max(5.0, self.total_capital / self.capital_divisions), 2)

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

    def clear_history(self):
        self.trade_history = []
        self.save_state()
        broadcaster.log_sync("INFO", "🗑️ تم مسح سجل صفقات الزونات بالكامل.")

    def save_state(self):
        try:
            data = {
                "symbol": self.symbol,
                "total_capital": self.total_capital,
                "capital_divisions": self.capital_divisions,
                "zones_above": self.zones_above,
                "zones_below": self.zones_below,
                "num_zones": self.num_zones,
                "custom_per_zone_capital": self.custom_per_zone_capital,
                "zone_step_percent": self.zone_step_percent,
                "base_price": self.base_price,
                "stop_loss_type": self.stop_loss_type,
                "stop_loss_percent": self.stop_loss_percent,
                "open_range": self.open_range,
                "demo_mode": self.demo_mode,
                "demo_balance": self.demo_balance,
                "is_running": self.is_running,
                "last_price": self.last_price,
                "levels": [lvl.to_dict() for lvl in self.levels],
                "trade_history": self.trade_history[:500]
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
            self.capital_divisions = int(data.get("capital_divisions", 10))
            self.zones_above = int(data.get("zones_above", 100))
            self.zones_below = int(data.get("zones_below", 100))
            self.num_zones = int(data.get("num_zones", self.zones_above + self.zones_below))
            self.custom_per_zone_capital = data.get("custom_per_zone_capital", 20.0)
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
            self.trade_history = data.get("trade_history", [])
        except Exception as e:
            broadcaster.log_sync("WARNING", f"Could not load zone grid state: {str(e)}")

    async def start(self):
        if not self.demo_mode and not binance_service.is_connected():
            raise Exception("Cannot start Real Bot: Binance is not connected. Add API keys first or switch to Demo Mode.")

        try:
            cur_price = binance_service.get_ticker_price(self.symbol)
        except Exception as e:
            if self.base_price > 0:
                cur_price = self.base_price
            else:
                raise e

        if not self.levels or len(self.levels) != self.num_zones or self.base_price <= 0:
            self.generate_levels(cur_price)

        self.is_running = True
        self.save_state()

        mode_str = "🎮 DEMO PAPER TRADING ($10,000)" if self.demo_mode else "⚡ LIVE BINANCE SPOT"
        range_str = "🌐 OPEN RANGE (Trailing Infinity)" if self.open_range else "🔒 FIXED RANGE"
        await broadcaster.broadcast(
            "SUCCESS",
            f"🚀 Shark Zone Grid STARTED for {self.symbol}! Mode: {mode_str} | Range: {range_str} | Capital: ${self.total_capital:,.2f} ({self.num_zones} levels [~{self.zones_below} Below, ~{self.zones_above} Above] @ ${self.per_zone_capital:,.2f}/trade | Max Active: {self.max_active_trades} | Gap: {self.zone_step_percent}%)"
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
            cur_p = self.last_price
            prec = get_precision(cur_p)

            for lvl in self.levels:
                if lvl.is_holding and lvl.bought_qty > 0:
                    sold_count += 1
                    total_qty_to_sell += lvl.bought_qty
                    loss_usd = (cur_p - lvl.buy_price) * lvl.bought_qty
                    loss_pct = ((cur_p - lvl.buy_price) / lvl.buy_price) * 100.0 if lvl.buy_price > 0 else 0.0

                    # Record in trade history
                    trade_rec = {
                        "id": f"TRD-{int(time.time() * 1000)}-{lvl.index}",
                        "level": lvl.index,
                        "symbol": self.symbol,
                        "buy_price": round(lvl.buy_price, prec),
                        "sell_price": round(cur_p, prec),
                        "qty": round(lvl.bought_qty, 6),
                        "cost": round(lvl.total_cost, 2),
                        "revenue": round(lvl.bought_qty * cur_p, 2),
                        "profit_usd": round(loss_usd, 2),
                        "profit_pct": round(loss_pct, 2),
                        "buy_time": lvl.last_trade_time or time.strftime("%H:%M:%S"),
                        "sell_time": time.strftime("%H:%M:%S"),
                        "date": time.strftime("%Y-%m-%d"),
                        "mode": "DEMO" if self.demo_mode else "REAL",
                        "type": "EMERGENCY_CLOSE"
                    }
                    self.trade_history.insert(0, trade_rec)

                    # Cancel any pre-placed sell or buy orders
                    if not self.demo_mode:
                        if lvl.sell_order_id:
                            binance_service.cancel_order(self.symbol, lvl.sell_order_id)
                        if lvl.buy_order_id:
                            binance_service.cancel_order(self.symbol, lvl.buy_order_id)

                    if self.demo_mode:
                        self.demo_balance += (lvl.bought_qty * cur_p)

                    lvl.is_holding = False
                    lvl.bought_qty = 0.0
                    lvl.buy_price = 0.0
                    lvl.total_cost = 0.0
                    lvl.sell_order_id = None
                    lvl.buy_order_id = None

            if len(self.trade_history) > 500:
                self.trade_history = self.trade_history[:500]

            self.is_running = False
            self.save_state()

            if total_qty_to_sell > 0:
                if self.demo_mode:
                    await broadcaster.broadcast("WARNING", f"🚨 [DEMO EMERGENCY CLOSE] Liquidated {sold_count} positions. Demo Wallet: ${self.demo_balance:,.2f} USDT.")
                    return {"status": "success", "mode": "demo", "sold_count": sold_count}
                else:
                    try:
                        clean_symbol = self.symbol.replace("USDT", "")
                        free_bal = binance_service.get_asset_free_balance(clean_symbol)
                        final_qty = min(total_qty_to_sell, free_bal) if free_bal > 0 else total_qty_to_sell
                        res = binance_service.place_market_sell(self.symbol, quantity=final_qty)
                        await broadcaster.broadcast("WARNING", f"🚨 [EMERGENCY CLOSE] Liquidated {sold_count} positions ({final_qty:.6f} {self.symbol}) at market price.")
                        return {"status": "success", "mode": "real", "sold_count": sold_count, "order": res}
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
            prec = get_precision(current_price)

            # ------------------------------------------------------------------
            # 1. OPEN RANGE ENGINE: DYNAMIC TRAILING UPWARDS
            # ------------------------------------------------------------------
            if self.open_range and len(self.levels) > 0:
                top_level = self.levels[-1]
                if current_price >= top_level.target_price:
                    step_factor = 1.0 + (self.zone_step_percent / 100.0)
                    new_idx = len(self.levels) + 1
                    new_price = round(top_level.target_price, prec)
                    new_target = round(new_price * step_factor, prec)

                    new_lvl = ZoneLevel(
                        index=new_idx,
                        price=new_price,
                        target_price=new_target,
                        is_holding=False
                    )
                    self.levels.append(new_lvl)
                    self.zones_above += 1
                    self.num_zones = len(self.levels)
                    await broadcaster.broadcast(
                        "INFO",
                        f"🌐 [OPEN RANGE TRAILING] Price broke above top level! Added Level {new_idx:02d} @ ${new_price:,.5f} (Target: ${new_target:,.5f}) 🚀"
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
                    if lvl_idx > 1 and (i - 1) >= 0:
                        prev_lvl = self.levels[i - 1]
                        if prev_lvl.is_holding:
                            await self._sell_level(prev_lvl, current_price, reason="TP_REACHED_HIGHER_LEVEL")

                    # 2. Current level buying:
                    if not lvl.is_holding:
                        active_count = sum(1 for x in self.levels if x.is_holding)
                        if active_count < self.max_active_trades:
                            await self._buy_level(lvl, current_price)

                # ========================================================
                # CASE B: FALLING SCENARIO (الهبوط والتراجع)
                # ========================================================
                else:
                    if not lvl.is_holding:
                        active_count = sum(1 for x in self.levels if x.is_holding)
                        if active_count < self.max_active_trades:
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
        prec = get_precision(current_price)

        prefix = "🎮 [DEMO]" if self.demo_mode else "⚡ [REAL]"
        target_idx = lvl_num + 1
        await broadcaster.broadcast(
            "INFO",
            f"{prefix} Level {lvl_num:02d} touched @ ${current_price:,.5f} -> Executing BUY for ${amount:.2f} (Target: Level {target_idx:02d} @ ${lvl.target_price:,.5f})"
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
                f"✅ {prefix} Level {lvl_num:02d} LOCKED 🔒 | Bought {executed_qty:.6f} {self.symbol} @ ${current_price:,.5f} | Pre-placed Target Sell @ ${lvl.target_price:,.5f} (+{self.zone_step_percent}%) | Demo Wallet: ${self.demo_balance:,.2f}"
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

            is_partial = (cummulative_cost < amount * 0.95)

            lvl.is_holding = True
            lvl.bought_qty = executed_qty
            lvl.buy_price = avg_price
            lvl.total_cost = cummulative_cost
            lvl.buy_order_id = buy_order.get("orderId")
            lvl.is_partial = is_partial
            lvl.last_trade_time = time.strftime("%H:%M:%S")

            # ---------------------------------------------------------
            # IMMEDIATELY PRE-PLACE LIMIT SELL ORDER ON BINANCE AT TARGET!
            # ---------------------------------------------------------
            target_sell_price = lvl.target_price
            try:
                limit_sell = binance_service.place_limit_sell(
                    symbol=self.symbol,
                    quantity=executed_qty,
                    price=target_sell_price
                )
                lvl.sell_order_id = limit_sell.get("orderId")
                await broadcaster.broadcast(
                    "SUCCESS",
                    f"✅ [Level {lvl_num:02d} LOCKED 🔒] Bought {executed_qty:.6f} {self.symbol} @ ${avg_price:,.5f} | Pre-placed Limit Sell #{lvl.sell_order_id} @ ${target_sell_price:,.5f} (+{self.zone_step_percent}%)"
                )
            except Exception as e_limit:
                lvl.sell_order_id = None
                await broadcaster.broadcast(
                    "WARNING",
                    f"⚠️ [Level {lvl_num:02d}] Buy succeeded, but pre-placing Limit Sell failed ({str(e_limit)}). Will monitor and sell via market execution."
                )

        except Exception as e:
            lvl.is_holding = False
            await broadcaster.broadcast("ERROR", f"❌ [Level {lvl_num:02d}] Market BUY failed: {str(e)}")

    async def _sell_level(self, lvl: ZoneLevel, current_price: float, reason: str = "TARGET_HIT"):
        """
        Execute sell for this level, realizing profit and freeing up the level.
        Handles both full fills and partial fills (cancelling unfilled remainder).
        Records trade into trade_history.
        """
        lvl_num = lvl.index
        qty_to_sell = lvl.bought_qty
        prec = get_precision(current_price)

        if qty_to_sell <= 0 or not lvl.is_holding:
            return

        prefix = "🎮 [DEMO]" if self.demo_mode else "⚡ [REAL]"
        pnl_usd = (current_price - lvl.buy_price) * qty_to_sell
        pnl_percent = ((current_price - lvl.buy_price) / lvl.buy_price) * 100.0 if lvl.buy_price > 0 else 0.0

        await broadcaster.broadcast(
            "INFO",
            f"💰 {prefix} Level {lvl_num:02d} Target Reached! Selling {qty_to_sell:.6f} @ ${current_price:,.5f} | Est. PnL: +{pnl_percent:.2f}% (+${pnl_usd:.2f})"
        )

        # -------------------------------------------------------------
        # DEMO MODE SELL
        # -------------------------------------------------------------
        if self.demo_mode:
            revenue = qty_to_sell * current_price
            self.demo_balance += revenue

            # Record in Trade History
            trade_rec = {
                "id": f"TRD-{int(time.time() * 1000)}",
                "level": lvl_num,
                "symbol": self.symbol,
                "buy_price": round(lvl.buy_price, prec),
                "sell_price": round(current_price, prec),
                "qty": round(qty_to_sell, 6),
                "cost": round(lvl.total_cost, 2),
                "revenue": round(revenue, 2),
                "profit_usd": round(pnl_usd, 2),
                "profit_pct": round(pnl_percent, 2),
                "buy_time": lvl.last_trade_time or time.strftime("%H:%M:%S"),
                "sell_time": time.strftime("%H:%M:%S"),
                "date": time.strftime("%Y-%m-%d"),
                "mode": "DEMO",
                "type": "TAKE_PROFIT"
            }
            self.trade_history.insert(0, trade_rec)
            if len(self.trade_history) > 500:
                self.trade_history = self.trade_history[:500]

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
                        binance_service.cancel_order(self.symbol, lvl.sell_order_id)
                except Exception:
                    pass

            if not pre_placed_filled:
                actual_free = binance_service.get_asset_free_balance(self.symbol.replace("USDT", ""))
                sell_qty = min(qty_to_sell, actual_free) if actual_free > 0 else qty_to_sell

                sell_order = binance_service.place_market_sell(self.symbol, quantity=sell_qty)
                received_quote = float(sell_order.get("cummulativeQuoteQty", 0.0))

            actual_profit_usd = received_quote - lvl.total_cost
            actual_profit_pct = (actual_profit_usd / lvl.total_cost) * 100.0 if lvl.total_cost > 0 else 0.0

            # Record in Trade History
            trade_rec = {
                "id": f"TRD-{int(time.time() * 1000)}",
                "level": lvl_num,
                "symbol": self.symbol,
                "buy_price": round(lvl.buy_price, prec),
                "sell_price": round(current_price, prec),
                "qty": round(qty_to_sell, 6),
                "cost": round(lvl.total_cost, 2),
                "revenue": round(received_quote, 2),
                "profit_usd": round(actual_profit_usd, 2),
                "profit_pct": round(actual_profit_pct, 2),
                "buy_time": lvl.last_trade_time or time.strftime("%H:%M:%S"),
                "sell_time": time.strftime("%H:%M:%S"),
                "date": time.strftime("%Y-%m-%d"),
                "mode": "REAL",
                "type": "TAKE_PROFIT"
            }
            self.trade_history.insert(0, trade_rec)
            if len(self.trade_history) > 500:
                self.trade_history = self.trade_history[:500]

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
                f"🎉 [Level {lvl_num:02d} UNLOCKED 🔓] Profit Locked! Received ${received_quote:,.2f} USDT (+{actual_profit_pct:.2f}%). Level is now FREE for new cycles."
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

        prec = get_precision(current_price)

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
                    trade_rec = {
                        "id": f"TRD-{int(time.time() * 1000)}-{lvl.index}",
                        "level": lvl.index,
                        "symbol": self.symbol,
                        "buy_price": round(lvl.buy_price, prec),
                        "sell_price": round(current_price, prec),
                        "qty": round(lvl.bought_qty, 6),
                        "cost": round(lvl.total_cost, 2),
                        "revenue": round(lvl.bought_qty * current_price, 2),
                        "profit_usd": round(-loss_usd, 2),
                        "profit_pct": round(-drop_pct, 2),
                        "buy_time": lvl.last_trade_time or time.strftime("%H:%M:%S"),
                        "sell_time": time.strftime("%H:%M:%S"),
                        "date": time.strftime("%Y-%m-%d"),
                        "mode": "DEMO" if self.demo_mode else "REAL",
                        "type": "STOP_LOSS"
                    }
                    self.trade_history.insert(0, trade_rec)
                    if len(self.trade_history) > 500:
                        self.trade_history = self.trade_history[:500]

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

        prec = get_precision(self.last_price if self.last_price > 0 else self.base_price)

        total_realized_profit = round(sum(t.get("profit_usd", 0.0) for t in self.trade_history), 2)
        win_count = sum(1 for t in self.trade_history if t.get("profit_usd", 0.0) > 0)
        win_rate = round((win_count / len(self.trade_history)) * 100.0, 1) if self.trade_history else 100.0

        return {
            "symbol": self.symbol,
            "total_capital": self.total_capital,
            "capital_divisions": self.capital_divisions,
            "zones_above": self.zones_above,
            "zones_below": self.zones_below,
            "num_zones": self.num_zones,
            "per_zone_capital": self.per_zone_capital,
            "max_active_trades": self.max_active_trades,
            "zone_step_percent": self.zone_step_percent,
            "base_price": round(self.base_price, prec),
            "base_level_index": self.zones_below + 1,
            "stop_loss_type": self.stop_loss_type,
            "stop_loss_percent": self.stop_loss_percent,
            "open_range": self.open_range,
            "demo_mode": self.demo_mode,
            "demo_balance": round(self.demo_balance, 2),
            "is_running": self.is_running,
            "last_price": round(self.last_price, prec),
            "active_trades_count": holding_count,
            "total_invested": round(total_invested, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_realized_profit": total_realized_profit,
            "completed_trades_count": len(self.trade_history),
            "win_rate": win_rate,
            "trade_history": self.trade_history[:100],
            "levels": [
                {
                    **lvl.to_dict(),
                    "price": round(lvl.price, prec),
                    "target_price": round(lvl.target_price, prec),
                    "buy_price": round(lvl.buy_price, prec) if lvl.buy_price > 0 else 0.0,
                    "current_pnl": round((self.last_price - lvl.buy_price) * lvl.bought_qty, 2) if (lvl.is_holding and self.last_price > 0) else 0.0,
                    "current_pnl_pct": round(((self.last_price - lvl.buy_price) / lvl.buy_price) * 100.0, 2) if (lvl.is_holding and lvl.buy_price > 0 and self.last_price > 0) else 0.0
                }
                for lvl in self.levels
            ]
        }

zone_grid_engine = ZoneGridEngine()

import math
from typing import Dict, Any, Optional, Tuple, List
from binance.client import Client
from binance.enums import *
from app.config import settings
from app.logger import broadcaster

class BinanceSpotService:
    def __init__(self):
        self.client: Optional[Client] = None
        self.symbol_info_cache: Dict[str, Dict[str, Any]] = {}
        self._init_client()

    def _init_client(self):
        if settings.binance_api_key and settings.binance_api_secret:
            try:
                self.client = Client(
                    api_key=settings.binance_api_key,
                    api_secret=settings.binance_api_secret,
                    testnet=settings.use_testnet
                )
            except Exception as e:
                self.client = None
                broadcaster.log_sync("ERROR", f"فشل تهيئة عميل بينانس: {str(e)}")
        else:
            self.client = None

    def reload(self):
        self.symbol_info_cache.clear()
        self._init_client()

    def is_connected(self) -> bool:
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            return False

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        symbol = symbol.upper()
        if symbol in self.symbol_info_cache:
            return self.symbol_info_cache[symbol]

        if not self.client:
            return None

        try:
            info = self.client.get_symbol_info(symbol)
            if info:
                self.symbol_info_cache[symbol] = info
                return info
        except Exception as e:
            broadcaster.log_sync("ERROR", f"تعذر جلب معلومات الزوج {symbol}: {str(e)}")
        return None

    def get_symbol_filters(self, symbol: str) -> Dict[str, float]:
        info = self.get_symbol_info(symbol)
        filters = {
            "step_size": 0.000001,
            "min_qty": 0.000001,
            "tick_size": 0.01,
            "min_notional": 5.0
        }
        if not info or "filters" not in info:
            return filters

        for f in info["filters"]:
            f_type = f.get("filterType")
            if f_type == "LOT_SIZE":
                filters["step_size"] = float(f.get("stepSize", 0.000001))
                filters["min_qty"] = float(f.get("minQty", 0.000001))
            elif f_type == "PRICE_FILTER":
                filters["tick_size"] = float(f.get("tickSize", 0.01))
            elif f_type in ("NOTIONAL", "MIN_NOTIONAL"):
                filters["min_notional"] = float(f.get("minNotional", 5.0))

        return filters

    def round_step(self, value: float, step: float) -> float:
        if step == 0:
            return value
        precision = int(round(-math.log10(step))) if step < 1 else 0
        factor = 10 ** precision
        return math.floor(value * factor) / factor

    def round_tick(self, value: float, tick: float) -> float:
        if tick == 0:
            return value
        precision = int(round(-math.log10(tick))) if tick < 1 else 0
        return round(value, precision)

    def _refresh_price_cache(self) -> bool:
        """
        Refresh global price cache of all Binance tickers using persistent session and multiple fallback endpoints.
        """
        import time, requests
        if not hasattr(self, "_http_session") or self._http_session is None:
            self._http_session = requests.Session()
            self._http_session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "application/json"
            })

        endpoints = [
            "https://api.binance.com/api/v3/ticker/price",
            "https://api1.binance.com/api/v3/ticker/price",
            "https://api3.binance.com/api/v3/ticker/price",
            "https://data-api.binance.vision/api/v3/ticker/price",
            "https://testnet.binance.vision/api/v3/ticker/price"
        ]

        for ep in endpoints:
            try:
                r = self._http_session.get(ep, timeout=6)
                if r.status_code == 200:
                    data = r.json()
                    cache = {}
                    for item in data:
                        sym = item.get("symbol")
                        p = item.get("price")
                        if sym and p:
                            try:
                                cache[sym] = float(p)
                            except ValueError:
                                pass
                    if cache:
                        self._price_cache = cache
                        self._last_price_cache_time = time.time()
                        return True
            except Exception:
                continue
        return False

    def get_ticker_price(self, symbol: str) -> float:
        import time
        clean_symbol = symbol.upper().replace("/", "").replace("-", "").replace(" ", "").strip()
        if not clean_symbol.endswith("USDT") and not any(clean_symbol.endswith(q) for q in ("BTC", "ETH", "BNB", "FDUSD", "EUR", "TRY", "BUSD")):
            clean_symbol = f"{clean_symbol}USDT"

        # 1. Try official client if connected
        if self.client:
            try:
                ticker = self.client.get_symbol_ticker(symbol=clean_symbol)
                return float(ticker["price"])
            except Exception:
                pass

        # 2. Check in-memory price cache (valid for 5 seconds)
        now = time.time()
        cache = getattr(self, "_price_cache", {})
        cache_time = getattr(self, "_last_price_cache_time", 0)
        if cache and clean_symbol in cache and (now - cache_time) < 5:
            return cache[clean_symbol]

        # 3. Try direct symbol query with persistent session and multiple endpoints
        if not hasattr(self, "_http_session") or self._http_session is None:
            import requests
            self._http_session = requests.Session()
            self._http_session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "application/json"
            })

        direct_endpoints = [
            f"https://api.binance.com/api/v3/ticker/price?symbol={clean_symbol}",
            f"https://api1.binance.com/api/v3/ticker/price?symbol={clean_symbol}",
            f"https://api3.binance.com/api/v3/ticker/price?symbol={clean_symbol}",
            f"https://data-api.binance.vision/api/v3/ticker/price?symbol={clean_symbol}",
            f"https://testnet.binance.vision/api/v3/ticker/price?symbol={clean_symbol}"
        ]
        for url in direct_endpoints:
            try:
                res = self._http_session.get(url, timeout=5)
                if res.status_code == 200:
                    val = float(res.json()["price"])
                    if not hasattr(self, "_price_cache"):
                        self._price_cache = {}
                    self._price_cache[clean_symbol] = val
                    self._last_price_cache_time = now
                    return val
            except Exception:
                continue

        # 4. Fallback: Refresh full market cache and look up
        if self._refresh_price_cache():
            if clean_symbol in self._price_cache:
                return self._price_cache[clean_symbol]

        # 5. Last-ditch: If cache has old price, return it rather than failing
        if cache and clean_symbol in cache:
            return cache[clean_symbol]

        raise Exception(f"تعذر جلب سعر الزوج {clean_symbol}. تأكد من الاتصال بالإنترنت أو صحة اسم الزوج.")

    def get_balances(self) -> Dict[str, Any]:
        if not self.client:
            return {"connected": False, "balances": [], "usdt_free": 0.0, "total_wallet_estimate": 0.0}

        try:
            account = self.client.get_account()
            balances = account.get("balances", [])
            usdt_free = 0.0
            non_zero_balances = []

            for b in balances:
                free = float(b.get("free", 0.0))
                locked = float(b.get("locked", 0.0))
                asset = b.get("asset")

                if asset == "USDT":
                    usdt_free = free

                if free > 0.00000001 or locked > 0.00000001:
                    non_zero_balances.append({
                        "asset": asset,
                        "free": free,
                        "locked": locked,
                        "total": free + locked
                    })

            return {
                "connected": True,
                "can_trade": account.get("canTrade", False),
                "usdt_free": usdt_free,
                "balances": non_zero_balances
            }
        except Exception as e:
            return {"connected": False, "error": str(e), "balances": [], "usdt_free": 0.0}

    def get_asset_free_balance(self, asset: str) -> float:
        if not self.client:
            return 0.0
        try:
            balance = self.client.get_asset_balance(asset=asset.upper())
            return float(balance["free"]) if balance else 0.0
        except Exception:
            return 0.0

    def place_market_buy(self, symbol: str, quote_quantity: float) -> Dict[str, Any]:
        """
        شراء فوري عبر تحديد كمية العملة المقابلة (USDT)
        quote_order_qty يتيح شراء بقيمة دولارية محددة مباشرة دون حساب يدوي معقد.
        """
        if not self.client:
            raise Exception("عميل بينانس غير متصل")

        symbol = symbol.upper()
        order = self.client.order_market_buy(
            symbol=symbol,
            quoteOrderQty=round(quote_quantity, 2)
        )
        return order

    def place_market_sell(self, symbol: str, quantity: float) -> Dict[str, Any]:
        """
        بيع فوري لكمية محددة من العملة
        """
        if not self.client:
            raise Exception("عميل بينانس غير متصل")

        symbol = symbol.upper()
        filters = self.get_symbol_filters(symbol)
        adjusted_qty = self.round_step(quantity, filters["step_size"])

        if adjusted_qty < filters["min_qty"]:
            raise Exception(f"الكمية {adjusted_qty} أقل من الحد الأدنى للطلب {filters['min_qty']}")

        # تنسيق الكمية كسلسلة رقمية دقيقة لتجنب الأخطاء
        step_precision = max(0, int(round(-math.log10(filters["step_size"])))) if filters["step_size"] < 1 else 0
        qty_str = f"{adjusted_qty:.{step_precision}f}"

        order = self.client.order_market_sell(
            symbol=symbol,
            quantity=qty_str
        )
        return order

    def place_oco_sell(self, symbol: str, quantity: float, tp_price: float, sl_stop_price: float, sl_limit_price: float) -> Dict[str, Any]:
        """
        إنشاء أمر OCO (أمر يلغي الآخر) على Spot:
        - أمر بيع محدد لأخذ الربح (Take Profit Limit)
        - أمر وقف خسارة محدد (Stop Loss Limit)
        """
        if not self.client:
            raise Exception("عميل بينانس غير متصل")

        symbol = symbol.upper()
        filters = self.get_symbol_filters(symbol)

        adjusted_qty = self.round_step(quantity, filters["step_size"])
        step_precision = max(0, int(round(-math.log10(filters["step_size"])))) if filters["step_size"] < 1 else 0
        qty_str = f"{adjusted_qty:.{step_precision}f}"

        tick_precision = max(0, int(round(-math.log10(filters["tick_size"])))) if filters["tick_size"] < 1 else 2
        tp_price_rounded = self.round_tick(tp_price, filters["tick_size"])
        sl_stop_rounded = self.round_tick(sl_stop_price, filters["tick_size"])
        sl_limit_rounded = self.round_tick(sl_limit_price, filters["tick_size"])

        tp_str = f"{tp_price_rounded:.{tick_precision}f}"
        sl_stop_str = f"{sl_stop_rounded:.{tick_precision}f}"
        sl_limit_str = f"{sl_limit_rounded:.{tick_precision}f}"

        order = self.client.create_oco_order(
            symbol=symbol,
            side=SIDE_SELL,
            quantity=qty_str,
            price=tp_str,
            stopPrice=sl_stop_str,
            stopLimitPrice=sl_limit_str,
            stopLimitTimeInForce=TIME_IN_FORCE_GTC
        )
        return order

    def place_limit_sell(self, symbol: str, quantity: float, price: float) -> Dict[str, Any]:
        """
        تعليق أمر بيع محدد (Limit Sell) مسبقاً عند سعر الهدف فور شراء المستوى
        """
        if not self.client:
            raise Exception("عميل بينانس غير متصل")

        symbol = symbol.upper()
        filters = self.get_symbol_filters(symbol)
        adjusted_qty = self.round_step(quantity, filters["step_size"])
        step_precision = max(0, int(round(-math.log10(filters["step_size"])))) if filters["step_size"] < 1 else 0
        qty_str = f"{adjusted_qty:.{step_precision}f}"

        tick_precision = max(0, int(round(-math.log10(filters["tick_size"])))) if filters["tick_size"] < 1 else 2
        price_rounded = self.round_tick(price, filters["tick_size"])
        price_str = f"{price_rounded:.{tick_precision}f}"

        return self.client.order_limit_sell(
            symbol=symbol,
            quantity=qty_str,
            price=price_str,
            timeInForce=TIME_IN_FORCE_GTC
        )

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """
        إلغاء أمر محدد عبر معرف الطلب (مثال: إلغاء المتبقي من أمر شراء جزئي)
        """
        if not self.client:
            return {}
        try:
            return self.client.cancel_order(symbol=symbol.upper(), orderId=order_id)
        except Exception:
            return {}

    def get_order(self, symbol: str, order_id: int) -> Optional[Dict[str, Any]]:
        """
        جلب حالة أمر محدد لفحص هل نُفّذ جزئياً أم كلياً
        """
        if not self.client:
            return None
        try:
            return self.client.get_order(symbol=symbol.upper(), orderId=order_id)
        except Exception:
            return None

    def cancel_open_orders_for_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """
        إلغاء جميع الأوامر المفتوحة للزوج (مثل أوامر OCO السابقة عند صدور إشارة بيع جديدة)
        """
        if not self.client:
            return []

        symbol = symbol.upper()
        try:
            open_orders = self.client.get_open_orders(symbol=symbol)
            canceled = []
            for order in open_orders:
                try:
                    c = self.client.cancel_order(symbol=symbol, orderId=order["orderId"])
                    canceled.append(c)
                except Exception:
                    pass
            return canceled
        except Exception as e:
            broadcaster.log_sync("WARNING", f"تعذر إلغاء الأوامر المفتوحة للزوج {symbol}: {str(e)}")
            return []

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        try:
            if symbol:
                return self.client.get_open_orders(symbol=symbol.upper())
            return self.client.get_open_orders()
        except Exception:
            return []

    def get_all_usdt_symbols(self) -> List[str]:
        """
        Fetch all active Binance Spot USDT symbols (700+ pairs) with in-memory caching.
        """
        import time
        now = time.time()
        if hasattr(self, "_cached_symbols") and self._cached_symbols and (now - getattr(self, "_cached_symbols_time", 0)) < 1800:
            return self._cached_symbols

        symbols = []
        priority = [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "PEPEUSDT",
            "SHIBUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "SUIUSDT", "NEARUSDT", "FETUSDT",
            "LTCUSDT", "DOTUSDT", "APTUSDT", "RENDERUSDT", "WIFUSDT", "FLOKIUSDT",
            "BONKUSDT", "TAOUSDT", "INJUSDT", "ARBUSDT", "OPUSDT", "TIAUSDT", "SEIUSDT"
        ]

        # 1. Try via official client if connected
        if self.client:
            try:
                tickers = self.client.get_all_tickers()
                for t in tickers:
                    s = t.get("symbol", "")
                    if s.endswith("USDT") and not any(s.endswith(x) for x in ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")):
                        symbols.append(s)
            except Exception:
                pass

        # 2. Try via public REST endpoint
        if not symbols:
            for all_url in [
                "https://api.binance.com/api/v3/ticker/price",
                "https://api1.binance.com/api/v3/ticker/price",
                "https://api3.binance.com/api/v3/ticker/price",
                "https://data-api.binance.vision/api/v3/ticker/price"
            ]:
                try:
                    import requests
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    r = requests.get(all_url, headers=headers, timeout=6)
                    if r.status_code == 200:
                        for t in r.json():
                            s = t.get("symbol", "")
                            if s.endswith("USDT") and not any(s.endswith(x) for x in ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")):
                                symbols.append(s)
                        if symbols:
                            break
                except Exception:
                    pass

        if not symbols:
            symbols = list(priority)

        symbols = sorted(list(set(symbols)))
        sorted_symbols = [s for s in priority if s in symbols] + [s for s in symbols if s not in priority]
        self._cached_symbols = sorted_symbols
        self._cached_symbols_time = now
        return sorted_symbols

binance_service = BinanceSpotService()

let ws = null;
let autoScroll = true;
let currentConfig = {};
let currentLanguage = localStorage.getItem("shark_bot_lang") || "en";
let currentView = "dashboard";

// Comprehensive Bilingual Translations
const translations = {
    en: {
        market_predator: "Market Predator",
        nav_section_main: "MAIN",
        nav_dashboard: "Dashboard",
        nav_exchanges: "My Exchanges",
        nav_positions: "Positions",
        nav_section_bots: "TRADING BOTS",
        nav_signal_bot: "Signal Bot (Webhook)",
        nav_section_manual: "MANUAL TRADING",
        nav_terminal: "Live Terminal",
        nav_section_other: "SYSTEM",
        nav_guide: "Beginner Guide",
        language_label: "Language:",
        dashboard_subtitle: "Overview & Real-Time Performance",
        exchanges_subtitle: "Manage Binance API Connections & Keys",
        positions_subtitle: "Live Spot Portfolio & Active OCO Orders",
        signal_bot_subtitle: "TradingView Webhook Configuration & Sizing",
        terminal_subtitle: "Real-Time WebSocket Stream & Trade Logs",
        guide_subtitle: "Step-by-Step Platform Manual",
        available_usdt: "Available USDT",
        capital_allocation: "Capital Allocation",
        order_protection: "Order Protection",
        webhook_endpoint: "Webhook Endpoint",
        copy_url: "Copy Webhook URL",
        binance_online: "Binance: Connected ✅",
        binance_offline: "Binance: Offline ⚠️",
        mode_testnet: "Testnet (Demo)",
        mode_live: "Live (Real Money)",
        bot_running: "Bot: Active",
        bot_paused: "Bot: Paused",
        hero_status_tag: "PREDATOR EXECUTION ENGINE ACTIVE",
        hero_title: "Rule The Markets with Shark Bot Pro",
        hero_desc: "Lightning-fast Binance Spot execution driven by TradingView alerts. Designed with intuitive simplicity so beginners can start in minutes, backed by institutional speed.",
        btn_configure_bot: "Configure Signal Bot",
        btn_view_terminal: "Open Live Terminal",
        how_it_works_title: "How It Works in 3 Simple Steps (Intuitive Simplicity)",
        step_1_title: "1. Connect Binance",
        step_1_desc: "Add your Binance API Key & Secret (Testnet or Live) in the Exchanges tab.",
        step_2_title: "2. Setup Signal Bot",
        step_2_desc: "Set your Capital % (e.g. 100%) and TP/SL goals, then copy your Alert JSON.",
        step_3_title: "3. Automate Trading",
        step_3_desc: "Paste into TradingView. Shark Bot executes trades and locks TP/SL instantly.",
        card_trading_title: "Trading & Capital Settings",
        capital_slider_label: "Purchase Capital Percentage:",
        capital_full: "100% (Full Balance)",
        default_tp_label: "Take Profit Target (TP %)",
        default_sl_label: "Stop Loss Target (SL %)",
        save_settings_btn: "Save Trading Settings",
        card_binance_title: "Binance API Connection",
        binance_desc: "Official REST & WebSocket integration",
        api_key_label: "Binance API Key",
        api_secret_label: "Binance API Secret",
        testnet_toggle_label: "Enable Testnet (Uncheck for Real Live Trading)",
        save_connect_btn: "Save & Verify Connection",
        card_tv_title: "TradingView Webhook Integration",
        webhook_setup_title: "Webhook Connection & Endpoint",
        webhook_url_label: "Webhook URL (Paste in TradingView):",
        webhook_security_tip: "This passphrase protects your bot. Any alert without this exact passphrase will be rejected immediately.",
        preset_100: "100% (Full)",
        calc_available: "Available USDT:",
        calc_per_trade: "Estimated Trade Allocation:",
        buy_signal_title: "1. BUY Signal Setup (Entry)",
        action_buy: "MARKET BUY",
        buy_signal_desc: "When your indicator triggers BUY, Shark Bot executes a Market Buy using your allocated capital % and instantly places Take Profit & Stop Loss (OCO) orders on Binance.",
        buy_payload_label: "TradingView Alert Message (BUY):",
        copy_buy_btn: "Copy BUY JSON",
        test_buy_btn: "Test BUY",
        sell_signal_title: "2. SELL Signal Setup (Exit)",
        action_sell: "MARKET SELL",
        sell_signal_desc: "When your indicator triggers SELL/CLOSE, Shark Bot cancels pending OCO orders and executes a Market Sell for 100% of the coin, returning capital to USDT immediately.",
        sell_payload_label: "TradingView Alert Message (SELL):",
        copy_sell_btn: "Copy SELL JSON",
        test_sell_btn: "Test SELL",
        pinescript_title: "Ready-to-Use Pine Script v5 Code (TradingView Indicator)",
        copy_code_btn: "Copy Full Pine Script",
        pinescript_desc: "Paste this code directly into the Pine Editor at the bottom of TradingView. It automatically configures buy/sell conditions and sends alerts to your Shark Bot Webhook!",
        secret_label: "Webhook Security Passphrase (Secret):",
        payload_label: "Alert Message JSON Payload:",
        copy_btn: "Copy",
        tv_tip: "In TradingView: Set <strong>Webhook URL</strong> to your endpoint, and paste the code above into the <strong>Message</strong> box.",
        chart_title: "Live TradingView Interactive Chart",
        quick_pairs_label: "Pairs:",
        terminal_title: "Live Execution Terminal",
        clear_btn: "Clear",
        autoscroll_btn: "Auto-scroll",
        sim_label: "Simulate Signal:",
        btn_buy: "BUY (Long)",
        btn_sell: "SELL (Exit)",
        portfolio_title: "Live Wallet Balances & Open Orders",
        refresh_btn: "Refresh Now",
        assets_title: "Wallet Assets",
        th_asset: "Asset",
        th_free: "Free",
        th_locked: "Locked",
        no_assets: "No assets or account not connected",
        open_orders_title: "Open Orders (OCO / Limit)",
        th_symbol: "Symbol",
        th_side: "Side",
        th_qty: "Qty",
        th_price: "Price",
        th_action: "Cancel",
        no_orders: "No active open orders",
        confirm_cancel: "Are you sure you want to cancel all open orders for ",
        keys_saved_success: "Connected to Binance successfully! ✅",
        keys_saved_failed: "API keys saved, but connection failed. Please check permissions & IP restrictions.",
        guide_title: "Quick Beginner Manual (\"السهل الممتنع\")",
        guide_q1: "1. How does Shark Bot Pro work?",
        guide_a1: "Shark Bot connects your TradingView strategy directly to Binance Spot. When your indicator fires a BUY signal, Shark Bot uses your chosen capital percentage (e.g. 100%) to buy immediately, and instantly places Take Profit (TP) and Stop Loss (SL) OCO orders on Binance.",
        guide_q2: "2. What is an OCO Order?",
        guide_a2: "OCO stands for \"One-Cancels-the-Other\". It places both your Target Profit order and your Stop Loss order at the same time. If the price hits your target, profit is taken and the stop loss is automatically removed. Your funds are protected 24/7 without needing you to watch the screen.",
        guide_q3: "3. How does balance synchronization work?",
        guide_a3: "Whenever you enter or exit a trade, Shark Bot immediately queries Binance and broadcasts your fresh USDT and asset balance via WebSocket. You can also click the \"Refresh Now\" button at any time to instantly update.",
        nav_zone_grid: "Shark Zone Grid",
        zone_grid_subtitle: "Independent Cascading Levels Grid with Dual Execution",
        zone_bot_badge: "SHARK SMART-ZONE MESH ENGINE",
        zone_hero_title: "Shark Independent Zone Grid",
        zone_hero_desc: "Divide capital equally across 10 independent levels. On rise: sell previous + buy current. On drop: sequential single-buy. Never re-buys a holding level until closed.",
        btn_view_blueprint: "View Architectural Diagram",
        blueprint_title: "System Architecture & Execution Flowchart",
        zone_stat_total: "Total Capital",
        zone_stat_per_zone: "Per Zone Capital",
        zone_stat_active: "Active Positions",
        zone_stat_pnl: "Unrealized PnL",
        zone_config_title: "Zone Grid Parameters & Capital",
        zone_symbol_label: "Trading Symbol (Pair)",
        btn_fetch_price: "Fetch Price",
        zone_total_capital_label: "Total Capital ($ USDT)",
        zone_num_zones_label: "Number of Levels / Zones",
        zone_step_label: "Distance Between Levels (%)",
        zone_base_price_label: "Base Starting Price ($)",
        zone_calc_per_zone: "Capital per Level:",
        zone_calc_max_orders: "Max Concurrent Orders:",
        zone_sl_type_label: "Stop Loss Strategy",
        opt_sl_total: "Option A: Total Portfolio SL (-10% of total capital)",
        opt_sl_per_zone: "Option B: Per-Zone Independent SL (-10% from entry price per level)",
        opt_sl_none: "Disabled / No Stop Loss",
        zone_sl_percent_label: "Stop Loss Percentage (%)",
        btn_preview_levels: "Calculate & Preview Levels",
        btn_start_zone_bot: "Start Shark Zone Bot",
        btn_pause_zone_bot: "Pause Bot",
        btn_emergency_close: "Emergency Close All",
        zone_rules_title: "How This Engine Protects & Trades",
        rf1_title: "Dual Action On Rise",
        rf1_desc: "When price hits Level K, it sells Level K-1 for profit (+1%), and simultaneously buys Level K with target Level K+1.",
        rf2_title: "Sequential Single-Buy On Retrace",
        rf2_desc: "When price drops from 10 to 9, it buys Level 9 (because it was freed previously). If it falls to 8, it buys Level 8.",
        rf3_title: "Strict One-Shot Rule",
        rf3_desc: "If price oscillates around Level 1, it will NEVER buy twice from Level 1 until that trade is sold at profit or stopped out.",
        rf4_title: "100% Guaranteed Capital Protection",
        rf4_desc: "With 10 levels at $20 each, total exposure can never exceed $200 under any market crash or fluctuation.",
        zone_levels_table_title: "Live Independent Levels Monitor",
        zone_no_levels: "Click 'Calculate & Preview Levels' or 'Start Shark Zone Bot' to initialize grid levels.",
        zone_stat_mode: "Mode & Wallet",
        zone_mode_label: "Trading Mode:",
        zone_mode_demo: "Demo Paper ($10,000 USDT)",
        zone_mode_live: "Live Binance Spot",
        demo_balance_label: "Demo Balance:",
        btn_reset_demo: "Reset $10,000",
        opt_open_range_title: "🌐 Trailing Infinity Open Range",
        opt_open_range_desc: "Automatically expands grid upwards without ceiling when price rises.",
        rf5_title: "Trailing Infinity Open Range",
        rf5_desc: "No fixed ceiling! If price trends upward continuously, the grid generates new zones automatically and rides the trend with pre-placed limit sells.",
        rf6_title: "Pre-placed Limit Sell & Partial Fill Safety",
        rf6_desc: "Limit sell is instantly pre-placed at the next zone. If an order fills partially and price rallies, remaining buy order is cancelled and actual filled amount is sold at target.",
        demo_reset_success: "Demo wallet reset to $10,000.00 USDT successfully!",
        demo_mode_changed: "Trading mode switched to: "
    },
    ar: {
        market_predator: "المفترس في أسواق المال",
        nav_section_main: "الرئيسية",
        nav_dashboard: "الداشبورد",
        nav_exchanges: "منصات التداول",
        nav_positions: "المراكز والصفقات",
        nav_section_bots: "بوتات التداول",
        nav_signal_bot: "بوت الإشارات (Webhook)",
        nav_section_manual: "التداول اليدوي",
        nav_terminal: "التيرمينال الحي",
        nav_section_other: "النظام",
        nav_guide: "دليل المبتدئين",
        language_label: "اللغة:",
        dashboard_subtitle: "نظرة عامة والأداء اللحظي",
        exchanges_subtitle: "إدارة والربط بحساب بينانس ومفاتيح API",
        positions_subtitle: "المحفظة الفورية وأوامر OCO المعلقة",
        signal_bot_subtitle: "إعدادات إشارات TradingView وحجم رأس المال",
        terminal_subtitle: "البث الحي وسجلات الصفقات عبر WebSocket",
        guide_subtitle: "شرح استخدام المنصة خطوة بخطوة",
        available_usdt: "رصيد USDT المتاح",
        capital_allocation: "نسبة الدخول من رأس المال",
        order_protection: "حماية الأوامر (Spot)",
        webhook_endpoint: "رابط Webhook",
        copy_url: "نسخ رابط الـ Webhook",
        binance_online: "بينانس: متصل ✅",
        binance_offline: "بينانس: غير متصل ⚠️",
        mode_testnet: "تجريبي (Testnet)",
        mode_live: "حقيقي (Live)",
        bot_running: "البوت: يعمل",
        bot_paused: "البوت: متوقف مؤقتاً",
        hero_status_tag: "محرك الاقتناص الفوري نشط",
        hero_title: "سيطر على أسواق المال مع Shark Bot Pro",
        hero_desc: "تنفيذ فائق السرعة على بينانس Spot مدعوماً بإشارات TradingView. صُمم بأسلوب السهل الممتنع ليبدأ المبتدئ خلال دقائق مع دقة وسرعة الأنظمة المؤسسية.",
        btn_configure_bot: "إعداد بوت الإشارات",
        btn_view_terminal: "فتح التيرمينال الحي",
        how_it_works_title: "كيف يعمل النظام في 3 خطوات بسيطة (السهل الممتنع)",
        step_1_title: "1. ربط بينانس",
        step_1_desc: "أدخل مفاتيح API الخاصة بك (تجريبي أو حقيقي) في تبويب منصات التداول.",
        step_2_title: "2. إعداد البوت ورأس المال",
        step_2_desc: "حدد نسبة رأس المال (مثلاً 100%) وأهداف الربح والخسارة وانسخ كود التنبيه.",
        step_3_title: "3. أتمتة التداول",
        step_3_desc: "الصق الكود في تريدينغ فيو. سينفذ شارك بوت الصفقات ويضع أهداف الربح والخسارة فوراً.",
        card_trading_title: "إعدادات التداول ورأس المال",
        capital_slider_label: "نسبة الشراء من رأس المال المتاح:",
        capital_full: "100% (كامل الرصيد)",
        default_tp_label: "هدف الربح الافتراضي (TP %)",
        default_sl_label: "وقف الخسارة الافتراضي (SL %)",
        save_settings_btn: "حفظ إعدادات التداول",
        card_binance_title: "ربط حساب بينانس (Binance API)",
        binance_desc: "الربط الرسمي عبر REST & WebSocket",
        api_key_label: "Binance API Key",
        api_secret_label: "Binance API Secret",
        testnet_toggle_label: "استخدام الحساب التجريبي (قم بإلغاء التحديد للتداول الحقيقي)",
        save_connect_btn: "حفظ واختبار الاتصال",
        card_tv_title: "إعدادات تنبيهات TradingView",
        webhook_setup_title: "نقطة اتصال ورابط الـ Webhook",
        webhook_url_label: "رابط الـ Webhook (يُلصق في TradingView):",
        webhook_security_tip: "كلمة السر هذه تحمي بوتك. سيتم رفض أي إشارة لا تحتوي على كلمة السر هذه فورياً.",
        preset_100: "100% (كامل الرصيد)",
        calc_available: "رصيد USDT المتاح:",
        calc_per_trade: "المبلغ المخصص للصفقة:",
        buy_signal_title: "1. إعداد إشارة الشراء (BUY - الدخول)",
        action_buy: "شراء فوري (BUY)",
        buy_signal_desc: "عند إطلاق إشارة BUY، يشتري البوت فورياً بالنسبة المحددة من رأس المال، ويضع فوراً أهداف الربح ووقف الخسارة (OCO) على بينانس.",
        buy_payload_label: "رسالة تنبيه الشراء (Message في TradingView):",
        copy_buy_btn: "نسخ كود الشراء (JSON)",
        test_buy_btn: "تجربة الشراء",
        sell_signal_title: "2. إعداد إشارة البيع (SELL - الخروج)",
        action_sell: "بيع فوري (SELL)",
        sell_signal_desc: "عند إطلاق إشارة SELL/CLOSE، يلغي البوت أوامر OCO السابقة ويبيع كامل كمية العملة بالدولار فورياً لتكون جاهزة للصفقة القادمة.",
        sell_payload_label: "رسالة تنبيه البيع (Message في TradingView):",
        copy_sell_btn: "نسخ كود البيع (JSON)",
        test_sell_btn: "تجربة البيع",
        pinescript_title: "كود Pine Script v5 الجاهز (مؤشر TradingView المتكامل)",
        copy_code_btn: "نسخ كود Pine Script بالكامل",
        pinescript_desc: "الصق هذا الكود مباشرة في محرر (Pine Editor) أسفل منصة TradingView. سيقوم المؤشر بإرسال إشارات الشراء والبيع تلقائياً إلى بوتك!",
        secret_label: "كلمة السر الأمنية للـ Webhook (Secret):",
        payload_label: "صيغة رسالة التنبيه (Alert Message JSON):",
        copy_btn: "نسخ",
        tv_tip: "في تريدينغ فيو: في خانة <strong>Webhook URL</strong> ضع الرابط أعلاه، وفي خانة <strong>Message</strong> الصق الكود أعلاه.",
        chart_title: "شارت TradingView التفاعلي المباشر",
        quick_pairs_label: "الأزواج السريعة:",
        terminal_title: "تيرمينال البث المباشر (Live Terminal)",
        clear_btn: "مسح",
        autoscroll_btn: "تثبيت بالأسفل",
        sim_label: "محاكاة إشارة:",
        btn_buy: "شراء (BUY)",
        btn_sell: "بيع (SELL)",
        portfolio_title: "الأصول المتاحة والأوامر المعلقة في بينانس",
        refresh_btn: "تحديث فوري",
        assets_title: "العملات في المحفظة",
        th_asset: "العملة",
        th_free: "المتاح (Free)",
        th_locked: "المحجوز (Locked)",
        no_assets: "لا توجد أصول أو الحساب غير متصل",
        open_orders_title: "الأوامر المفتوحة (OCO / Limit)",
        th_symbol: "الزوج",
        th_side: "النوع",
        th_qty: "الكمية",
        th_price: "السعر",
        th_action: "إلغاء",
        no_orders: "لا توجد أوامر معلقة حالياً",
        confirm_cancel: "هل أنت متأكد من إلغاء جميع الأوامر المفتوحة للزوج ",
        keys_saved_success: "تم الاتصال ببينانس بنجاح! ✅",
        keys_saved_failed: "تم حفظ المفاتيح، ولكن فشل الاتصال. تأكد من صحتها وصلاحيات الـ IP.",
        guide_title: "دليل المبتدئين السريع (\"السهل الممتنع\")",
        guide_q1: "1. كيف يعمل Shark Bot Pro؟",
        guide_a1: "يقوم شارك بوت بربط استراتيجيتك أو مؤشرك على تريدينغ فيو بحسابك على بينانس Spot مباشرة. عند صدور إشارة شراء، يشتري البوت بالنسبة المحددة (مثلاً 100%) ويضع فوراً أمر OCO يجمع بين أخذ الربح ووقف الخسارة.",
        guide_q2: "2. ما هو أمر OCO؟",
        guide_a2: "هو أمر (أمر يلغي الآخر) معتمد رسمياً في بينانس، يضع هدف الربح ووقف الخسارة في وقت واحد. إذا تحقق الهدف تُباع العملة بربح ويُلغى وقف الخسارة تلقائياً، لحماية رأس مالك دون الحاجة لمتابعة الشاشة.",
        guide_q3: "3. كيف يعمل تحديث الرصيد السريع؟",
        guide_a3: "بمجرد دخول أو خروج البوت من أي صفقة، يستعلم فوراً عن رصيد USDT الجديد ويبثه عبر الـ WebSocket في أجزاء من الثانية، لتكون أموالك جاهزة للصفقة القادمة.",
        nav_zone_grid: "بوت الزونات المستقلة",
        zone_grid_subtitle: "شبكة المستويات المستقلة والمتسلسلة بأمر مزدوج بالصعود وشراء متسلسل بالهبوط",
        zone_bot_badge: "محرك شبكة الزونات الذكية",
        zone_hero_title: "Shark Independent Zone Grid (شبكة الزونات المستقلة)",
        zone_hero_desc: "تقسيم رأس المال بالتساوي على 10 مستويات مستقلة. عند الصعود: بيع السابق وشراء الحالي. عند الهبوط: شراء متسلسل لمرة واحدة. ممنوع تكرار الشراء حتى إغلاق الصفقة.",
        btn_view_blueprint: "عرض المخطط الهندسي التوضيحي",
        blueprint_title: "المخطط المعماري وخريطة التدفق البرمجي",
        zone_stat_total: "رأس المال الإجمالي",
        zone_stat_per_zone: "مخصص كل مستوى",
        zone_stat_active: "الصفقات المفتوحة",
        zone_stat_pnl: "الربح / الخسارة غير المحققة",
        zone_config_title: "إعدادات رأس المال والزونات",
        zone_symbol_label: "زوج التداول",
        btn_fetch_price: "جلب السعر الحي",
        zone_total_capital_label: "رأس المال المخصص ($ USDT)",
        zone_num_zones_label: "عدد المستويات (الزونات)",
        zone_step_label: "الفارق بين الخطوط (%)",
        zone_base_price_label: "سعر خط البداية (0 = سعر السوق)",
        zone_calc_per_zone: "المبلغ المخصص لكل مستوى:",
        zone_calc_max_orders: "أقصى صفقات مفتوحة معاً:",
        zone_sl_type_label: "استراتيجية وقف الخسارة",
        opt_sl_total: "الخيار A: وقف خسارة كلي للمحفظة (-10% من إجمالي رأس المال)",
        opt_sl_per_zone: "الخيار B: وقف خسارة جزئي (لكل مستوى على حدة)",
        opt_sl_none: "معطل / بدون وقف خسارة",
        zone_sl_percent_label: "نسبة وقف الخسارة (%)",
        btn_preview_levels: "معاينة وتوليد المستويات",
        btn_start_zone_bot: "بدء تشغيل بوت الزونات",
        btn_pause_zone_bot: "إيقاف مؤقت للبوت",
        btn_emergency_close: "إغلاق طارئ لجميع الصفقات",
        zone_rules_title: "آلية عمل المحرك والحماية التامة",
        rf1_title: "أمران متزامنان عند الصعود",
        rf1_desc: "عند لمس المستوى K، يبيع ما اشتراه من K-1 بربح (+1%)، ويشتري فوراً من K بهدف K+1.",
        rf2_title: "شراء متسلسل بالهبوط",
        rf2_desc: "عند تراجع السعر من 10 إلى 9 يشتري من 9 لكونه تحرر مسبقاً، وإذا واصل الهبوط إلى 8 يشتري من 8.",
        rf3_title: "قاعدة تجميد المستوى ومنع التكرار",
        rf3_desc: "إذا تذبذب السعر عند مستوى 1، يستحيل الشراء منه ثانية حتى يبيع صفقته السابقة بربح أو وقف.",
        rf4_title: "أمان مطلق لرأس المال",
        rf4_desc: "مع 10 مستويات بـ 20$ لكل مستوى، يستحيل استنزاف أكثر من 200$ تحت أي تقلب أو هبوط عنيف.",
        zone_levels_table_title: "مراقبة المستويات العشرة المباشرة",
        zone_no_levels: "اضغط على 'معاينة وتوليد المستويات' أو 'بدء تشغيل البوت' لعرض وتفعيل المستويات.",
        zone_stat_mode: "وضع التداول والمحفظة",
        zone_mode_label: "وضع التداول:",
        zone_mode_demo: "حساب تجريبي ديمو (10,000$ USDT)",
        zone_mode_live: "حقيقي (Live Binance Spot)",
        demo_balance_label: "رصيد الديمو:",
        btn_reset_demo: "إعادة ضبط 10,000$",
        opt_open_range_title: "🌐 النطاق المفتوح المتحرك (Trailing Infinity)",
        opt_open_range_desc: "توليد مستويات جديدة للأعلى تلقائياً عند صعود السعر دون سقف محدد لجني أرباح مستمرة.",
        rf5_title: "النطاق المفتوح والامتداد اللانهائي",
        rf5_desc: "بدون سقف مغلق! عندما يصعد السعر باستمرار يتم توليد مستويات 11 و12 تلقائياً لملاحقة الصعود وتعليق أوامر البيع.",
        rf6_title: "تعليق أمر البيع وإلغاء المتبقي عند التنفيذ الجزئي",
        rf6_desc: "بمجرد الشراء يُعلق فوراً أمر بيع ليمت عند المستوى الموالي، وإذا نُفذ الشراء جزئياً وصعد السعر يُلغى المتبقي ويباع المنفذ فقط.",
        demo_reset_success: "تم إعادة تعيين رصيد الحساب التجريبي إلى 10,000.00$ USDT بنجاح!",
        demo_mode_changed: "تم تغيير وضع التداول إلى: "
    }
};

// Document Ready
document.addEventListener("DOMContentLoaded", () => {
    setLanguage(currentLanguage);
    initWebSocket();
    loadBotStatus();
    loadBalancesAndOrders();
    setupEventListeners();

    // Auto-sync balance every 12 seconds
    setInterval(() => {
        loadBalancesAndOrders(false);
    }, 12000);
});

// View Switching Function
function switchView(viewName) {
    currentView = viewName;

    // Update active class on nav items
    document.querySelectorAll(".nav-item").forEach(item => {
        item.classList.toggle("active", item.getAttribute("data-view") === viewName);
    });

    // Update active class on content views
    document.querySelectorAll(".content-view").forEach(view => {
        view.classList.toggle("active", view.id === `view-${viewName}`);
    });

    // Update Topbar Title & Subtitle
    const dict = translations[currentLanguage] || translations.en;
    const titleEl = document.getElementById("currentPageTitle");
    const subtitleEl = document.getElementById("currentPageSubtitle");

    const titleKey = `nav_${viewName.replace("-", "_")}`;
    const subtitleKey = `${viewName.replace("-", "_")}_subtitle`;

    if (titleEl && dict[titleKey]) titleEl.textContent = dict[titleKey];
    if (subtitleEl && dict[subtitleKey]) subtitleEl.textContent = dict[subtitleKey];

    // Load TradingView chart when switching to terminal view
    if (viewName === "terminal") {
        setTimeout(() => loadTradingViewChart(currentChartSymbol), 100);
    }

    if (viewName === "zone-grid") {
        fetchZgStatus();
    }

    // Close mobile sidebar if open
    document.querySelector(".sidebar")?.classList.remove("open");
}

let currentChartSymbol = "BINANCE:BTCUSDT";

function loadTradingViewChart(symbol = currentChartSymbol) {
    currentChartSymbol = symbol;
    const container = document.getElementById("tv_chart_container");
    if (!container) return;

    if (typeof TradingView === "undefined") {
        container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#94a3b8;">Loading TradingView Chart Engine...</div>';
        setTimeout(() => loadTradingViewChart(symbol), 600);
        return;
    }

    container.innerHTML = "";
    try {
        new TradingView.widget({
            "autosize": true,
            "symbol": symbol,
            "interval": "15",
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": currentLanguage === "ar" ? "ar" : "en",
            "toolbar_bg": "#090d16",
            "enable_publishing": false,
            "allow_symbol_change": true,
            "save_image": false,
            "container_id": "tv_chart_container",
            "studies": [
                "STD;RSI",
                "STD;MACD"
            ]
        });
    } catch (e) {
        console.error("Failed to load TV chart:", e);
    }
}

function changeChartSymbol(symbol, btn) {
    document.querySelectorAll(".pair-pill").forEach(p => p.classList.remove("active"));
    btn?.classList.add("active");

    const simInput = document.getElementById("simSymbol");
    if (simInput) {
        simInput.value = symbol.replace("BINANCE:", "");
    }

    loadTradingViewChart(symbol);
}

function toggleSidebar() {
    document.querySelector(".sidebar")?.classList.toggle("open");
}

// Language Switcher Function
function setLanguage(lang) {
    currentLanguage = lang;
    localStorage.setItem("shark_bot_lang", lang);

    document.documentElement.lang = lang;
    document.documentElement.dir = (lang === "ar" ? "rtl" : "ltr");

    // Toggle active state on pills
    document.getElementById("langEnBtn")?.classList.toggle("active", lang === "en");
    document.getElementById("langArBtn")?.classList.toggle("active", lang === "ar");

    // Translate all elements with data-i18n
    const dict = translations[lang] || translations.en;
    document.querySelectorAll("[data-i18n]").forEach(el => {
        const key = el.getAttribute("data-i18n");
        if (dict[key]) {
            el.innerHTML = dict[key];
        }
    });

    // Update title for current view
    switchView(currentView);

    // Re-render badges
    updateStatusBadges(currentConfig);
}

// WebSocket Connection for Live Terminal & Instant Balance Updates
function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/terminal`;
    const dot = document.getElementById("wsStatusDot");
    const sideDot = document.getElementById("sidebarTerminalPulse");

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        if (dot) dot.style.backgroundColor = "var(--emerald)";
        if (sideDot) sideDot.style.display = "inline-block";
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            // Check if this is an instant balance update event
            if (data.type === "event" && data.event === "balance_updated") {
                handleLiveBalanceUpdate(data.payload);
            } else if (data.level || data.message) {
                appendTerminalLog(data);
            }
        } catch (e) {
            console.error("Failed to parse WS data:", e);
        }
    };

    ws.onclose = () => {
        if (dot) dot.style.backgroundColor = "var(--danger)";
        setTimeout(initWebSocket, 3000);
    };

    ws.onerror = () => {
        if (dot) dot.style.backgroundColor = "var(--danger)";
    };
}

// Append live log to terminal
function appendTerminalLog(log) {
    const screen = document.getElementById("terminalScreen");
    if (!screen) return;

    const row = document.createElement("div");
    const level = (log.level || "INFO").toLowerCase();
    row.className = `log-line log-${level}`;

    const time = log.timestamp ? log.timestamp.split(" ")[1] : new Date().toLocaleTimeString();
    row.innerHTML = `
        <span class="log-time">[${time}]</span>
        <span class="log-tag">[${log.level || 'INFO'}]</span>
        <span class="log-msg">${escapeHtml(log.message)}</span>
    `;

    screen.appendChild(row);

    if (autoScroll) {
        screen.scrollTop = screen.scrollHeight;
    }
}

function clearTerminalLogs() {
    const screen = document.getElementById("terminalScreen");
    if (screen) screen.innerHTML = "";
}

let lastKnownUsdt = 0;

// Instant Live Balance Update with Pulse Animation
function handleLiveBalanceUpdate(balData) {
    if (!balData) return;

    lastKnownUsdt = parseFloat(balData.usdt_free || 0);
    const amount = lastKnownUsdt.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    
    // Update both Topbar balance chip and Dashboard balance card
    const topDisplay = document.getElementById("topUsdtBalance");
    const dashDisplay = document.getElementById("usdtBalance");

    if (topDisplay) {
        topDisplay.innerHTML = `${amount} <span class="unit">USDT</span>`;
        topDisplay.classList.remove("balance-pulse");
        void topDisplay.offsetWidth;
        topDisplay.classList.add("balance-pulse");
    }

    if (dashDisplay) {
        dashDisplay.innerHTML = `${amount} <span class="unit">USDT</span>`;
        dashDisplay.classList.remove("balance-pulse");
        void dashDisplay.offsetWidth;
        dashDisplay.classList.add("balance-pulse");
    }

    updateCapitalCalculator();
    renderBalancesTable(balData.balances || []);
}

// Fetch Initial Status and Config
async function loadBotStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();
        currentConfig = data;

        updateStatusBadges(data);
        updateSlidersAndInputs(data);
        updatePayloadPreview();
    } catch (e) {
        console.error("Failed to load status:", e);
    }
}

function updateStatusBadges(data) {
    const dict = translations[currentLanguage] || translations.en;

    // Sidebar status
    const sideDot = document.getElementById("sideStatusDot");
    const sideText = document.getElementById("sideStatusText");
    const pill = document.getElementById("exchangeStatusPill");
    const pillText = document.getElementById("exchangeStatusPillText");

    if (data.binance_connected) {
        if (sideDot) sideDot.className = "mini-status-dot online";
        if (sideText) sideText.textContent = dict.binance_online;
        if (pill) pill.className = "status-badge badge-online";
        if (pillText) pillText.textContent = dict.binance_online;
    } else {
        if (sideDot) sideDot.className = "mini-status-dot offline";
        if (sideText) sideText.textContent = dict.binance_offline;
        if (pill) pill.className = "status-badge badge-offline";
        if (pillText) pillText.textContent = dict.binance_offline;
    }

    // Mode badge
    const modeBadge = document.getElementById("modeBadge");
    const modeText = document.getElementById("modeText");
    if (data.use_testnet) {
        modeBadge.className = "status-badge badge-warning";
        modeText.textContent = dict.mode_testnet;
    } else {
        modeBadge.className = "status-badge badge-online";
        modeText.textContent = dict.mode_live;
    }

    // Bot toggle button
    const toggleBtn = document.getElementById("toggleBotBtn");
    const botBtnText = document.getElementById("botBtnText");
    if (data.bot_enabled) {
        toggleBtn.className = "btn btn-sm btn-success";
        botBtnText.textContent = dict.bot_running;
    } else {
        toggleBtn.className = "btn btn-sm btn-danger";
        botBtnText.textContent = dict.bot_paused;
    }

    const capDisplay = document.getElementById("capitalPercentDisplay");
    if (capDisplay) capDisplay.textContent = `${data.capital_percent || 100}%`;
}

function updateSlidersAndInputs(data) {
    const capital = data.capital_percent || 100;
    const slider = document.getElementById("capitalSlider");
    const sliderVal = document.getElementById("sliderValue");
    if (slider) slider.value = capital;
    if (sliderVal) sliderVal.textContent = `${capital}%`;

    const tpInput = document.getElementById("defaultTp");
    if (tpInput && data.default_tp_percent) tpInput.value = data.default_tp_percent;

    const slInput = document.getElementById("defaultSl");
    if (slInput && data.default_sl_percent) slInput.value = data.default_sl_percent;

    const secretInput = document.getElementById("webhookSecret");
    if (secretInput && data.webhook_passphrase) secretInput.value = data.webhook_passphrase;

    const testnetToggle = document.getElementById("testnetToggle");
    if (testnetToggle) testnetToggle.checked = Boolean(data.use_testnet);
}

// Fetch balances and open orders
async function loadBalancesAndOrders(showAnimation = true) {
    try {
        const balRes = await fetch("/api/balances");
        const balData = await balRes.json();
        handleLiveBalanceUpdate(balData);

        const ordRes = await fetch("/api/orders");
        const ordData = await ordRes.json();
        renderOrdersTable(ordData.orders || []);
    } catch (e) {
        console.error("Failed to load balances/orders:", e);
    }
}

function renderBalancesTable(balances) {
    const balBody = document.getElementById("balancesTableBody");
    const dict = translations[currentLanguage] || translations.en;
    if (!balBody) return;

    if (balances && balances.length > 0) {
        balBody.innerHTML = balances.map(b => `
            <tr>
                <td class="text-cyan"><strong>${b.asset}</strong></td>
                <td>${parseFloat(b.free).toFixed(6)}</td>
                <td class="text-muted">${parseFloat(b.locked).toFixed(6)}</td>
            </tr>
        `).join("");
    } else {
        balBody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">${dict.no_assets}</td></tr>`;
    }
}

function renderOrdersTable(orders) {
    const ordBody = document.getElementById("ordersTableBody");
    const dict = translations[currentLanguage] || translations.en;
    if (!ordBody) return;

    if (orders && orders.length > 0) {
        ordBody.innerHTML = orders.map(o => `
            <tr>
                <td><strong>${o.symbol}</strong></td>
                <td><span class="badge ${o.side === 'BUY' ? 'text-emerald' : 'text-danger'}">${o.side} (${o.type})</span></td>
                <td>${parseFloat(o.origQty).toFixed(4)}</td>
                <td>$${parseFloat(o.price || o.stopPrice || 0).toFixed(2)}</td>
                <td>
                    <button class="btn btn-xs btn-outline text-danger" onclick="cancelOrderForSymbol('${o.symbol}')">
                        ${dict.th_action}
                    </button>
                </td>
            </tr>
        `).join("");
    } else {
        ordBody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">${dict.no_orders}</td></tr>`;
    }
}

// Manual Fast Refresh Button
async function manualRefreshBalances() {
    const btn = document.getElementById("refreshBalanceBtn");
    btn?.classList.add("spinning");
    await loadBalancesAndOrders(true);
    setTimeout(() => {
        btn?.classList.remove("spinning");
    }, 600);
}

function refreshBalancesAndOrders() {
    manualRefreshBalances();
}

// Setup Event Listeners
function setupEventListeners() {
    // Capital Slider
    const slider = document.getElementById("capitalSlider");
    const sliderVal = document.getElementById("sliderValue");
    if (slider) {
        slider.addEventListener("input", (e) => {
            sliderVal.textContent = `${e.target.value}%`;
            const capDisplay = document.getElementById("capitalPercentDisplay");
            if (capDisplay) capDisplay.textContent = `${e.target.value}%`;
            updatePayloadPreview();
        });
    }

    // Toggle Bot Master Switch
    const toggleBtn = document.getElementById("toggleBotBtn");
    if (toggleBtn) {
        toggleBtn.addEventListener("click", async () => {
            const newState = !currentConfig.bot_enabled;
            await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ bot_enabled: newState })
            });
            currentConfig.bot_enabled = newState;
            updateStatusBadges(currentConfig);
        });
    }

    // Save Trading Settings
    const saveTradeBtn = document.getElementById("saveTradingSettingsBtn");
    if (saveTradeBtn) {
        saveTradeBtn.addEventListener("click", async () => {
            const capital = parseFloat(document.getElementById("capitalSlider").value);
            const tp = parseFloat(document.getElementById("defaultTp").value);
            const sl = parseFloat(document.getElementById("defaultSl").value);

            await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    capital_percent: capital,
                    default_tp_percent: tp,
                    default_sl_percent: sl
                })
            });
            alert(currentLanguage === "ar" ? "تم حفظ إعدادات رأس المال والربح/الخسارة بنجاح!" : "Trading settings saved successfully!");
            loadBotStatus();
        });
    }

    // Save API Keys
    const saveApiBtn = document.getElementById("saveApiKeysBtn");
    if (saveApiBtn) {
        saveApiBtn.addEventListener("click", async () => {
            const apiKey = document.getElementById("binanceApiKey").value;
            const apiSecret = document.getElementById("binanceApiSecret").value;
            const useTestnet = document.getElementById("testnetToggle").checked;

            const payload = { use_testnet: useTestnet };
            if (apiKey) payload.binance_api_key = apiKey;
            if (apiSecret) payload.binance_api_secret = apiSecret;

            const res = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            const dict = translations[currentLanguage] || translations.en;
            alert(data.binance_connected ? dict.keys_saved_success : dict.keys_saved_failed);
            loadBotStatus();
            loadBalancesAndOrders();
        });
    }

    // Autoscroll button
    const autoScrollBtn = document.getElementById("autoScrollToggle");
    if (autoScrollBtn) {
        autoScrollBtn.addEventListener("click", () => {
            autoScroll = !autoScroll;
            autoScrollBtn.classList.toggle("active", autoScroll);
        });
    }
}

// Capital Preset Buttons
function setCapitalPreset(percent) {
    const slider = document.getElementById("capitalSlider");
    const sliderVal = document.getElementById("sliderValue");
    if (slider) slider.value = percent;
    if (sliderVal) sliderVal.textContent = `${percent}%`;

    const capDisplay = document.getElementById("capitalPercentDisplay");
    if (capDisplay) capDisplay.textContent = `${percent}%`;

    // Update active class on preset buttons
    document.querySelectorAll(".preset-btn").forEach(btn => {
        const text = btn.textContent.trim();
        btn.classList.toggle("active", text.startsWith(`${percent}%`));
    });

    updateCapitalCalculator();
    updatePayloadPreview();
}

// Dynamic Capital Calculator
function updateCapitalCalculator() {
    const slider = document.getElementById("capitalSlider");
    const capitalPct = parseFloat(slider?.value || 100);
    const estimated = (lastKnownUsdt * (capitalPct / 100.0));

    const availEl = document.getElementById("calcAvailableUsdt");
    const estimEl = document.getElementById("calcEstimatedTrade");

    if (availEl) {
        availEl.textContent = `${lastKnownUsdt.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} USDT`;
    }
    if (estimEl) {
        estimEl.textContent = `~${estimated.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} USDT (${capitalPct}%)`;
    }
}

// Update TradingView Code Payloads for BUY and SELL
function updatePayloadPreview() {
    const secret = document.getElementById("webhookSecret")?.value || "secure_trading_pass_2026";
    const capital = parseFloat(document.getElementById("capitalSlider")?.value || 100);
    const tp = parseFloat(document.getElementById("defaultTp")?.value || 2.5);
    const sl = parseFloat(document.getElementById("defaultSl")?.value || 1.2);

    // BUY Payload
    const buyPayload = {
        "secret": secret,
        "action": "BUY",
        "symbol": "{{ticker}}",
        "tp_percent": tp,
        "sl_percent": sl,
        "capital_percent": capital
    };

    // SELL Payload
    const sellPayload = {
        "secret": secret,
        "action": "SELL",
        "symbol": "{{ticker}}"
    };

    const buyPre = document.getElementById("tvBuyPayloadCode");
    if (buyPre) buyPre.textContent = JSON.stringify(buyPayload, null, 2);

    const sellPre = document.getElementById("tvSellPayloadCode");
    if (sellPre) sellPre.textContent = JSON.stringify(sellPayload, null, 2);

    // Webhook URL display
    const urlDisplay = document.getElementById("webhookDisplayUrl");
    if (urlDisplay) {
        urlDisplay.value = `${window.location.protocol}//${window.location.host}/api/webhook`;
    }

    // Dynamic Pine Script Code update
    const pineBox = document.getElementById("pineScriptCodeBox");
    if (pineBox) {
        pineBox.textContent = `// © Shark Bot Pro - Automated Binance Spot Strategy Template
//@version=5
indicator("Shark Bot Pro - Strategy Indicator", overlay=true)

// 1. Indicator Parameters (e.g. Fast & Slow EMAs)
fastLength = input.int(9, title="Fast EMA Length")
slowLength = input.int(21, title="Slow EMA Length")
tpPercent  = input.float(${tp}, title="Take Profit %")
slPercent  = input.float(${sl}, title="Stop Loss %")
capitalPct = input.int(${capital}, title="Capital % Allocation")
secretKey  = input.string("${secret}", title="Webhook Secret")

// 2. Calculation
fastEMA = ta.ema(close, fastLength)
slowEMA = ta.ema(close, slowLength)

plot(fastEMA, color=color.cyan, title="Fast EMA")
plot(slowEMA, color=color.orange, title="Slow EMA")

// 3. Buy and Sell Conditions
buyCondition  = ta.crossover(fastEMA, slowEMA)
sellCondition = ta.crossunder(fastEMA, slowEMA)

plotshape(buyCondition, title="Buy Signal", style=shape.triangleup, location=location.belowbar, color=color.green, size=size.small, text="BUY")
plotshape(sellCondition, title="Sell Signal", style=shape.triangledown, location=location.abovebar, color=color.red, size=size.small, text="SELL")

// 4. Send Webhook Alerts to Shark Bot Pro
if (buyCondition)
    alert('{"secret": "' + secretKey + '", "action": "BUY", "symbol": "' + syminfo.ticker + '", "tp_percent": ' + str.tostring(tpPercent) + ', "sl_percent": ' + str.tostring(slPercent) + ', "capital_percent": ' + str.tostring(capitalPct) + '}', alert.freq_once_per_bar_close)

if (sellCondition)
    alert('{"secret": "' + secretKey + '", "action": "SELL", "symbol": "' + syminfo.ticker + '"}', alert.freq_once_per_bar_close)`;
    }

    updateCapitalCalculator();
}

function copyBuyPayload() {
    const code = document.getElementById("tvBuyPayloadCode")?.textContent;
    if (code) {
        navigator.clipboard.writeText(code).then(() => {
            alert(currentLanguage === "ar" ? "تم نسخ كود إشارة الشراء (BUY JSON) بنجاح!" : "BUY Alert JSON copied successfully!");
        });
    }
}

function copySellPayload() {
    const code = document.getElementById("tvSellPayloadCode")?.textContent;
    if (code) {
        navigator.clipboard.writeText(code).then(() => {
            alert(currentLanguage === "ar" ? "تم نسخ كود إشارة البيع (SELL JSON) بنجاح!" : "SELL Alert JSON copied successfully!");
        });
    }
}

function copyPineScriptCode() {
    const code = document.getElementById("pineScriptCodeBox")?.textContent;
    if (code) {
        navigator.clipboard.writeText(code).then(() => {
            alert(currentLanguage === "ar" ? "تم نسخ كود Pine Script بالكامل! يمكنك لصقه الآن في محرر تريدينغ فيو." : "Full Pine Script code copied! You can now paste it into TradingView's Pine Editor.");
        });
    }
}

function copyAlertPayload() {
    copyBuyPayload();
}

async function cancelOrderForSymbol(symbol) {
    const dict = translations[currentLanguage] || translations.en;
    if (confirm(`${dict.confirm_cancel} ${symbol}?`)) {
        await fetch(`/api/cancel-orders?symbol=${symbol}`, { method: "POST" });
        loadBalancesAndOrders();
    }
}

// Send simulated signal from Dashboard
async function sendSimulatedSignal(action) {
    const symbol = document.getElementById("simSymbol").value.trim().toUpperCase() || "BTCUSDT";
    const tp = parseFloat(document.getElementById("simTp").value) || 2.0;
    const sl = parseFloat(document.getElementById("simSl").value) || 1.0;

    try {
        const res = await fetch("/api/test-signal", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                action: action,
                symbol: symbol,
                tp_percent: tp,
                sl_percent: sl
            })
        });
        const result = await res.json();
        console.log("Simulated Signal result:", result);
    } catch (e) {
        console.error("Error sending simulated signal:", e);
    }
}

function escapeHtml(str) {
    if (!str) return "";
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ==============================================================================
// SHARK INDEPENDENT ZONE GRID CLIENT FUNCTIONS
// ==============================================================================

let isZgDemoMode = true; // default demo active

function toggleBlueprintModal() {
    const box = document.getElementById("blueprintContainer");
    if (!box) return;
    box.style.display = (box.style.display === "none" || !box.style.display) ? "block" : "none";
}

function updateZgCalcPreview() {
    const totalCap = parseFloat(document.getElementById("zgTotalCapital")?.value) || 200.0;
    const numZones = parseInt(document.getElementById("zgNumZones")?.value) || 10;
    const perZone = numZones > 0 ? (totalCap / numZones).toFixed(2) : "0.00";

    const calcPerLevelEl = document.getElementById("zgCalcPerLevel");
    const calcMaxOrdersEl = document.getElementById("zgCalcMaxOrders");

    if (calcPerLevelEl) calcPerLevelEl.textContent = `$${perZone} / Level`;
    if (calcMaxOrdersEl) calcMaxOrdersEl.textContent = `${numZones} Orders Max`;
}

async function setZgDemoMode(isDemo) {
    isZgDemoMode = isDemo;
    const demoBtn = document.getElementById("zgModeDemoBtn");
    const liveBtn = document.getElementById("zgModeLiveBtn");
    const demoActions = document.getElementById("demoActionsGroup");

    if (demoBtn) demoBtn.classList.toggle("active", isDemo);
    if (liveBtn) liveBtn.classList.toggle("active", !isDemo);
    if (demoActions) demoActions.style.display = isDemo ? "flex" : "none";

    try {
        await fetch("/api/zone-grid/demo-toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled: isDemo })
        });
        fetchZgStatus();
    } catch (e) {
        console.error("Error setting demo mode:", e);
    }
}

async function resetDemoBalance() {
    try {
        const res = await fetch("/api/zone-grid/demo-reset", { method: "POST" });
        const data = await res.json();
        const dict = translations[currentLanguage] || translations.en;
        alert(dict.demo_reset_success || "Demo wallet reset to $10,000.00 USDT successfully!");
        fetchZgStatus();
    } catch (e) {
        console.error("Error resetting demo balance:", e);
    }
}

async function fetchLiveZgPrice() {
    const symbol = document.getElementById("zgSymbol")?.value.trim().toUpperCase() || "BTCUSDT";
    try {
        const previewRes = await fetch("/api/zone-grid/preview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                symbol: symbol,
                total_capital: parseFloat(document.getElementById("zgTotalCapital")?.value) || 200,
                num_zones: parseInt(document.getElementById("zgNumZones")?.value) || 10,
                zone_step_percent: parseFloat(document.getElementById("zgStepPercent")?.value) || 1.0,
                base_price: 0,
                open_range: document.getElementById("zgOpenRange")?.checked ?? true,
                demo_mode: isZgDemoMode
            })
        });
        const data = await previewRes.json();
        if (data.base_price) {
            document.getElementById("zgBasePrice").value = data.base_price;
            renderZgLevels(data.levels, false);
        }
    } catch (e) {
        console.error("Error fetching live price:", e);
    }
}

function setZgPair(symbol, btn) {
    document.querySelectorAll(".quick-pair-buttons .pair-pill").forEach(p => p.classList.remove("active"));
    if (btn) btn.classList.add("active");
    const input = document.getElementById("zgSymbol");
    if (input) input.value = symbol;
    fetchLiveZgPrice();
}

async function previewZoneGrid() {
    const symbol = document.getElementById("zgSymbol")?.value.trim().toUpperCase() || "BTCUSDT";
    const totalCap = parseFloat(document.getElementById("zgTotalCapital")?.value) || 200.0;
    const numZones = parseInt(document.getElementById("zgNumZones")?.value) || 10;
    const stepPct = parseFloat(document.getElementById("zgStepPercent")?.value) || 1.0;
    const baseP = parseFloat(document.getElementById("zgBasePrice")?.value) || 0.0;
    const openRange = document.getElementById("zgOpenRange")?.checked ?? true;

    try {
        const res = await fetch("/api/zone-grid/preview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                symbol: symbol,
                total_capital: totalCap,
                num_zones: numZones,
                zone_step_percent: stepPct,
                base_price: baseP > 0 ? baseP : null,
                open_range: openRange,
                demo_mode: isZgDemoMode
            })
        });
        const data = await res.json();
        if (data.base_price && (!baseP || baseP === 0)) {
            document.getElementById("zgBasePrice").value = data.base_price;
        }
        renderZgLevels(data.levels, false);
    } catch (e) {
        console.error("Error previewing grid:", e);
    }
}

async function fetchZgStatus() {
    try {
        const res = await fetch("/api/zone-grid/status");
        const data = await res.json();

        // Update stats
        const statTotal = document.getElementById("zgStatTotalCap");
        const statPerZone = document.getElementById("zgStatPerZoneCap");
        const statActive = document.getElementById("zgStatActiveTrades");
        const statPnl = document.getElementById("zgStatPnl");
        const statModeBal = document.getElementById("zgStatModeBalance");
        const demoBalanceText = document.getElementById("zgDemoBalanceText");

        if (statTotal) statTotal.textContent = `$${data.total_capital.toFixed(2)}`;
        if (statPerZone) statPerZone.textContent = `$${data.per_zone_capital.toFixed(2)} / Trade`;
        if (statActive) statActive.textContent = `${data.active_trades_count} / ${data.num_zones} Active`;
        if (statPnl) {
            const pnl = data.unrealized_pnl || 0.0;
            statPnl.textContent = `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`;
            statPnl.className = `stat-value ${pnl >= 0 ? 'text-emerald' : 'text-danger'}`;
        }

        // Demo vs Live Mode UI sync
        isZgDemoMode = Boolean(data.demo_mode);
        const demoBtn = document.getElementById("zgModeDemoBtn");
        const liveBtn = document.getElementById("zgModeLiveBtn");
        const demoActions = document.getElementById("demoActionsGroup");

        if (demoBtn) demoBtn.classList.toggle("active", isZgDemoMode);
        if (liveBtn) liveBtn.classList.toggle("active", !isZgDemoMode);
        if (demoActions) demoActions.style.display = isZgDemoMode ? "flex" : "none";

        if (demoBalanceText) {
            demoBalanceText.textContent = `$${(data.demo_balance || 10000.0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} USDT`;
        }

        if (statModeBal) {
            if (isZgDemoMode) {
                statModeBal.textContent = `🎮 Demo $${(data.demo_balance || 10000.0).toFixed(0)}`;
                statModeBal.className = "stat-value text-emerald";
            } else {
                statModeBal.textContent = "⚡ Live Binance";
                statModeBal.className = "stat-value text-orange";
            }
        }

        // Open Range Sync
        const openRangeEl = document.getElementById("zgOpenRange");
        if (openRangeEl && data.open_range !== undefined && !openRangeEl.dataset.userToggled) {
            openRangeEl.checked = Boolean(data.open_range);
        }

        // Update engine status badge
        const badgeEl = document.getElementById("zgEngineStatusBadge");
        const badgeText = document.getElementById("zgEngineStatusText");
        const startBtn = document.getElementById("zgStartBtn");
        const stopBtn = document.getElementById("zgStopBtn");

        if (data.is_running) {
            if (badgeEl) badgeEl.className = "status-badge badge-online";
            const modeLabel = isZgDemoMode ? "(Demo)" : "(Live)";
            if (badgeText) badgeText.textContent = (currentLanguage === "ar" ? "البوت: نشط يعمل ✅ " : "Bot: Running ✅ ") + modeLabel;
            if (startBtn) startBtn.style.display = "none";
            if (stopBtn) stopBtn.style.display = "inline-flex";
        } else {
            if (badgeEl) badgeEl.className = "status-badge badge-offline";
            if (badgeText) badgeText.textContent = currentLanguage === "ar" ? "البوت: متوقف" : "Bot: Stopped";
            if (startBtn) startBtn.style.display = "inline-flex";
            if (stopBtn) stopBtn.style.display = "none";
        }

        // Fill form fields if empty or first load
        const symInput = document.getElementById("zgSymbol");
        if (symInput && data.symbol && !symInput.dataset.userEdited) symInput.value = data.symbol;

        // Render levels table
        if (data.levels && data.levels.length > 0) {
            renderZgLevels(data.levels, data.is_running);
        }
    } catch (e) {
        console.error("Error fetching Zone Grid status:", e);
    }
}

function renderZgLevels(levels, isRunning) {
    const tbody = document.getElementById("zgLevelsTableBody");
    if (!tbody) return;

    if (!levels || levels.length === 0) {
        const dict = translations[currentLanguage] || translations.en;
        tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted">${dict.zone_no_levels}</td></tr>`;
        return;
    }

    // Sort descending: Level 10 down to Level 01 (matching financial chart order)
    const sorted = [...levels].sort((a, b) => b.index - a.index);

    let html = "";
    sorted.forEach(lvl => {
        const isHolding = lvl.is_holding;
        let statusBadge = "";

        if (isHolding) {
            if (lvl.is_partial) {
                statusBadge = `<span class="level-badge-partial"><i class="fa-solid fa-triangle-exclamation"></i> ${currentLanguage === 'ar' ? 'تنفيذ جزئي' : 'PARTIAL'}</span>`;
            } else {
                statusBadge = `<span class="level-badge-holding"><i class="fa-solid fa-cube"></i> ${currentLanguage === 'ar' ? 'مشغول بصفقة' : 'HOLDING'}</span>`;
            }
        } else {
            statusBadge = `<span class="level-badge-idle"><i class="fa-regular fa-circle"></i> ${currentLanguage === 'ar' ? 'متاح للطلب' : 'IDLE / FREE'}</span>`;
        }

        let lockBadge = "";
        if (isHolding) {
            lockBadge = `<div><span class="lock-pill-locked"><i class="fa-solid fa-lock"></i> ${currentLanguage === 'ar' ? 'مقفول (صفقة جارية)' : 'LOCKED 🔒'}</span></div>`;
            if (lvl.sell_order_id || isRunning) {
                lockBadge += `<span class="badge-order-limit"><i class="fa-solid fa-crosshairs"></i> ${currentLanguage === 'ar' ? 'أمر بيع معلق' : 'Sell Pre-placed'}</span>`;
            }
        } else {
            lockBadge = `<span class="lock-pill-unlocked"><i class="fa-solid fa-lock-open"></i> ${currentLanguage === 'ar' ? 'جاهز للشراء' : 'UNLOCKED 🔓'}</span>`;
        }

        const pnl = lvl.current_pnl || 0.0;
        const pnlPct = lvl.current_pnl_pct || 0.0;
        const pnlHtml = isHolding
            ? `<span class="${pnl >= 0 ? 'text-emerald' : 'text-danger'} font-mono font-bold">${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)} (${pnl >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%)</span>`
            : `<span class="text-muted">-</span>`;

        const qtyHtml = isHolding && lvl.bought_qty > 0
            ? `<span class="font-mono text-cyan font-bold">${lvl.bought_qty.toFixed(6)}</span>`
            : `<span class="text-muted">-</span>`;

        const entryHtml = isHolding && lvl.buy_price > 0
            ? `<span class="font-mono">$${lvl.buy_price.toFixed(4)}</span>`
            : `<span class="text-muted">-</span>`;

        const capitalVal = lvl.capital || lvl.total_cost || 20.0;

        html += `
            <tr class="${isHolding ? 'row-holding-active' : ''}">
                <td class="font-bold text-cyan">Level ${String(lvl.index).padStart(2, '0')}</td>
                <td class="font-mono font-bold">$${lvl.price.toFixed(4)}</td>
                <td class="font-mono text-emerald font-bold">$${lvl.target_price.toFixed(4)} <small class="text-muted">(+1%)</small></td>
                <td class="font-mono">$${capitalVal.toFixed(2)}</td>
                <td>${statusBadge}</td>
                <td>${qtyHtml}</td>
                <td>${entryHtml}</td>
                <td>${pnlHtml}</td>
                <td>${lockBadge}</td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

async function startZoneGrid() {
    const symbol = document.getElementById("zgSymbol")?.value.trim().toUpperCase() || "BTCUSDT";
    const totalCap = parseFloat(document.getElementById("zgTotalCapital")?.value) || 200.0;
    const numZones = parseInt(document.getElementById("zgNumZones")?.value) || 10;
    const stepPct = parseFloat(document.getElementById("zgStepPercent")?.value) || 1.0;
    const baseP = parseFloat(document.getElementById("zgBasePrice")?.value) || 0.0;
    const slType = document.getElementById("zgSlType")?.value || "TOTAL";
    const slPct = parseFloat(document.getElementById("zgSlPercent")?.value) || 10.0;
    const openRange = document.getElementById("zgOpenRange")?.checked ?? true;

    try {
        // 1. Configure with open range & demo mode
        await fetch("/api/zone-grid/configure", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                symbol: symbol,
                total_capital: totalCap,
                num_zones: numZones,
                zone_step_percent: stepPct,
                base_price: baseP > 0 ? baseP : null,
                stop_loss_type: slType,
                stop_loss_percent: slPct,
                open_range: openRange,
                demo_mode: isZgDemoMode
            })
        });

        // 2. Start
        const startRes = await fetch("/api/zone-grid/start", { method: "POST" });
        const startData = await startRes.json();

        if (startRes.ok) {
            const modeText = isZgDemoMode
                ? (currentLanguage === "ar" ? "في وضع الحساب التجريبي (ديمو 10,000$)" : "in Demo Paper Trading Mode ($10,000)")
                : (currentLanguage === "ar" ? "في وضع التداول الحقيقي (Live Binance)" : "in Live Binance Spot Mode");
            alert((currentLanguage === "ar" ? "تم تشغيل بوت الزونات بنجاح! 🚀 " : "Shark Zone Grid started successfully! 🚀 ") + modeText);
            fetchZgStatus();
        } else {
            alert(`Error: ${startData.detail || startData.message}`);
        }
    } catch (e) {
        console.error("Error starting Zone Grid:", e);
        alert("Failed to start Zone Grid: " + e.message);
    }
}

async function stopZoneGrid() {
    try {
        const res = await fetch("/api/zone-grid/stop", { method: "POST" });
        const data = await res.json();
        alert(currentLanguage === "ar" ? "تم إيقاف بوت الزونات مؤقتاً." : "Shark Zone Grid has been paused.");
        fetchZgStatus();
    } catch (e) {
        console.error("Error stopping Zone Grid:", e);
    }
}

async function emergencyCloseZoneGrid() {
    const confirmMsg = currentLanguage === "ar"
        ? "تحذير: هل أنت متأكد من تفعيل الإغلاق الطارئ؟ سيتم بيع جميع صفقات الزونات المفتوحة فوراً بطلب سوق وإيقاف البوت."
        : "CAUTION: Are you sure you want to execute Emergency Close All? This will immediately market-sell all holding positions across all zones and halt the bot.";

    if (!confirm(confirmMsg)) return;

    try {
        const res = await fetch("/api/zone-grid/emergency-close", { method: "POST" });
        const data = await res.json();
        alert(currentLanguage === "ar" ? "تم تنفيذ الإغلاق الطارئ وتسييل الصفقات بنجاح." : "Emergency liquidation completed.");
        fetchZgStatus();
        loadBalancesAndOrders();
    } catch (e) {
        console.error("Error executing emergency close:", e);
        alert("Emergency close error: " + e.message);
    }
}

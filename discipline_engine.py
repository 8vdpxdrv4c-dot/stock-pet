"""纪律引擎：定时拉大盘、判断涨跌家数、按交易时点弹纪律提醒。"""
import datetime
import logging
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

import stock_data

logger = logging.getLogger(__name__)


def _is_trade_day(dt):
    return dt.weekday() < 5


def _is_trade_time(dt):
    t = dt.time()
    return ((datetime.time(9, 25) <= t <= datetime.time(11, 35)) or
            (datetime.time(12, 55) <= t <= datetime.time(15, 5)))


class DisciplineEngine(QObject):
    notify = pyqtSignal(str, str)
    mood_change = pyqtSignal(str, bool)

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.discipline = cfg.get("discipline", {})
        self._paused = False
        self._last_reminded_time = ""
        self._last_market_warn_key = ""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30 * 1000)

    def set_paused(self, paused):
        self._paused = paused
        self.notify.emit("我先闭麦了" if paused else "我回来盯着你了", "info")

    def _tick(self):
        if self._paused:
            return
        now = datetime.datetime.now()
        if not _is_trade_day(now):
            return
        self._check_scheduled_reminder(now)
        if _is_trade_time(now):
            self._check_market(now)

    def _check_scheduled_reminder(self, now):
        hhmm = now.strftime("%H:%M")
        for rt in self.discipline.get("remind_times", []):
            if hhmm == rt and self._last_reminded_time != f"{now.date()}{rt}":
                self._last_reminded_time = f"{now.date()}{rt}"
                if rt == "09:30":
                    self.notify.emit("开盘了。先看计划：今天买什么？止损位在哪？没计划别动手。", "info")
                elif rt == "11:25":
                    self.notify.emit("上午盘快收了。冲动交易几笔？超过3笔下午收手。", "warn")
                elif rt == "14:45":
                    self.notify.emit("尾盘15分钟。拉升别追，跳水别慌割。", "warn")

    def _check_market(self, now):
        snap = stock_data.get_market_snapshot()
        if snap is None:
            return
        panic_threshold = self.discipline.get("panic_down_count_threshold", 3500)
        fomo_threshold = self.discipline.get("fomo_up_count_threshold", 4000)
        if snap.down >= panic_threshold:
            key = f"panic-{now:%Y%m%d%H}"
            if self._last_market_warn_key != key:
                self._last_market_warn_key = key
                self.notify.emit(f"⚠️ 全市场{snap.down}家下跌（跌停{snap.limit_down}家）。恐慌时刻，不许割肉也不许抄底。", "panic")
                self.mood_change.emit("panic", True)
            return
        if snap.up >= fomo_threshold:
            key = f"fomo-{now:%Y%m%d%H}"
            if self._last_market_warn_key != key:
                self._last_market_warn_key = key
                self.notify.emit(f"🔥 全市场{snap.up}家上涨（涨停{snap.limit_up}家）。人人赚钱时最危险，不许追高。", "warn")
                self.mood_change.emit("warn", True)
            return
        if self._last_market_warn_key.startswith(("panic", "fomo")):
            if not self._last_market_warn_key.endswith(f"{now:%Y%m%d%H}"):
                self._last_market_warn_key = ""
                self.mood_change.emit("normal", False)

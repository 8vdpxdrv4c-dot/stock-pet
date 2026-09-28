"""股票数据模块：多源自动降级，全部失败也不崩溃。"""
import logging
import datetime
from typing import Optional

import akshare as ak

logger = logging.getLogger(__name__)


class MarketSnapshot:
    def __init__(self, up, down, flat, limit_up, limit_down, timestamp, source=""):
        self.up = up
        self.down = down
        self.flat = flat
        self.limit_up = limit_up
        self.limit_down = limit_down
        self.timestamp = timestamp
        self.source = source

    @property
    def total(self):
        return self.up + self.down + self.flat

    def __repr__(self):
        return f"MarketSnapshot(up={self.up}, down={self.down}, flat={self.flat}, limit_up={self.limit_up}, limit_down={self.limit_down}, source={self.source}, time={self.timestamp:%H:%M})"


_last_snapshot = None


def _from_legu():
    df = ak.stock_market_activity_legu()
    data = dict(zip(df["item"].astype(str), df["value"].astype(str)))
    def _i(s):
        s = str(s).replace("家", "").replace(",", "").strip()
        try:
            return int(float(s))
        except Exception:
            return 0
    return MarketSnapshot(
        up=_i(data.get("上涨", 0)), down=_i(data.get("下跌", 0)), flat=_i(data.get("平盘", 0)),
        limit_up=_i(data.get("涨停", 0)), limit_down=_i(data.get("跌停", 0)),
        timestamp=datetime.datetime.now(), source="legu",
    )


def _from_eastmoney():
    df = ak.stock_zh_a_spot_em()
    chg = df["涨跌幅"]
    up = int((chg > 0).sum())
    down = int((chg < 0).sum())
    flat = int((chg == 0).sum())
    limit_up = int((chg >= 9.8).sum())
    limit_down = int((chg <= -9.8).sum())
    return MarketSnapshot(up=up, down=down, flat=flat, limit_up=limit_up, limit_down=limit_down, timestamp=datetime.datetime.now(), source="eastmoney")


def get_market_snapshot():
    global _last_snapshot
    for fn in (_from_legu, _from_eastmoney):
        try:
            snap = fn()
            if snap is not None and snap.total > 100:
                _last_snapshot = snap
                logger.info("大盘快照: %s", snap)
                return snap
        except Exception as e:
            logger.warning("数据源 %s 失败: %s", fn.__name__, e)
    return _last_snapshot


def get_last_snapshot():
    return _last_snapshot


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(get_market_snapshot())

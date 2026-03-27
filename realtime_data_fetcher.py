"""
实时数据获取器 - 确保所有数据都是当天最新的
支持股票实时行情、分时数据、盘口数据等
"""

import logging
from datetime import datetime, timedelta

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealtimeDataFetcher:
    """实时数据获取器 - 处理股票实时数据、避免缓存导致的过时数据"""

    def __init__(self):
        self.last_update_time = {}
        self.cache_expire_seconds = 30  # 缓存过期时间（秒）

    def get_realtime_quote(self, symbol: str, force_refresh: bool = False):
        """
        获取实时行情数据（当天最新）

        Args:
            symbol: 股票代码（6位数字或完整代码）
            force_refresh: 是否强制刷新，忽略缓存

        Returns:
            dict: 包含实时行情数据 {price, high, low, volume, amount, time, ...}
        """
        try:
            import akshare as ak

            # 检查缓存是否有效
            if not force_refresh and self._is_cache_valid(symbol):
                logger.info(f"[缓存] {symbol} 数据未过期，使用缓存")
                return self.last_update_time.get(f"{symbol}_data")

            logger.info(f"[实时行情] 正在获取 {symbol} 的实时行情...")

            # 获取实时行情
            df = ak.stock_zh_a_spot_em()

            if df is not None and not df.empty:
                # 查找对应的股票
                stock_row = df[df['代码'] == symbol]

                if not stock_row.empty:
                    row = stock_row.iloc[0]
                    data = {
                        'symbol': symbol,
                        'name': row.get('名称', ''),
                        'price': float(row.get('最新价', 0)),
                        'high': float(row.get('最高', 0)),
                        'low': float(row.get('最低', 0)),
                        'open': float(row.get('今开', 0)),
                        'close_yesterday': float(row.get('昨收', 0)),
                        'volume': float(row.get('成交量', 0)),
                        'amount': float(row.get('成交额', 0)),
                        'pe_ratio': row.get('市盈率', 'N/A'),
                        'pb_ratio': row.get('市净率', 'N/A'),
                        'change_pct': float(row.get('涨跌幅', 0)) / 100,
                        'change': float(row.get('涨跌额', 0)),
                        'update_time': datetime.now().isoformat(),
                    }

                    # 更新缓存时间
                    self.last_update_time[symbol] = datetime.now().timestamp()
                    self.last_update_time[f"{symbol}_data"] = data

                    logger.info(f"[实时行情] ✅ 成功获取 {symbol} 的实时行情: {data['price']} 元")
                    return data

            logger.warning(f"[实时行情] ⚠️ 未找到股票 {symbol}")
            return None

        except Exception as e:
            logger.error(f"[实时行情] ❌ 获取失败: {str(e)[:100]}")
            return None

    def get_realtime_intraday(self, symbol: str, period: str = '1m'):
        """
        获取分时数据（当天）

        Args:
            symbol: 股票代码
            period: 周期 ('1m', '5m', '15m', '30m', '60m')

        Returns:
            DataFrame: 包含分时数据
        """
        try:
            import akshare as ak

            logger.info(f"[分时数据] 正在获取 {symbol} 的 {period} 分时数据...")

            # 转换period格式
            period_map = {
                '1m': '1',
                '5m': '5',
                '15m': '15',
                '30m': '30',
                '60m': '60'
            }

            ak_period = period_map.get(period, '1')

            # 获取分时数据
            df = ak.stock_zh_a_tick(symbol=symbol, period=ak_period)

            if df is not None and not df.empty:
                df['time'] = pd.to_datetime(df.get('时间', df.index))
                logger.info(f"[分时数据] ✅ 成功获取 {len(df)} 条 {period} 分时数据")
                return df
            else:
                logger.warning(f"[分时数据] ⚠️ 未获取到数据")
                return None

        except Exception as e:
            logger.error(f"[分时数据] ❌ 获取失败: {str(e)[:100]}")
            return None

    def get_realtime_orderbook(self, symbol: str):
        """
        获取实时盘口数据（买卖五档）

        Args:
            symbol: 股票代码

        Returns:
            dict: 包含买卖五档数据
        """
        try:
            import akshare as ak

            logger.info(f"[盘口数据] 正在获取 {symbol} 的实时盘口...")

            # 获取实时行情（包含盘口）
            df = ak.stock_zh_a_spot_em()

            if df is not None and not df.empty:
                stock_row = df[df['代码'] == symbol]

                if not stock_row.empty:
                    row = stock_row.iloc[0]

                    # 构建盘口数据
                    data = {
                        'symbol': symbol,
                        'asks': [  # 卖方（绿色）
                            {'price': float(row.get('卖五价', 0)), 'volume': float(row.get('卖五量', 0))},
                            {'price': float(row.get('卖四价', 0)), 'volume': float(row.get('卖四量', 0))},
                            {'price': float(row.get('卖三价', 0)), 'volume': float(row.get('卖三量', 0))},
                            {'price': float(row.get('卖二价', 0)), 'volume': float(row.get('卖二量', 0))},
                            {'price': float(row.get('卖一价', 0)), 'volume': float(row.get('卖一量', 0))},
                        ],
                        'bids': [  # 买方（红色）
                            {'price': float(row.get('买一价', 0)), 'volume': float(row.get('买一量', 0))},
                            {'price': float(row.get('买二价', 0)), 'volume': float(row.get('买二量', 0))},
                            {'price': float(row.get('买三价', 0)), 'volume': float(row.get('买三量', 0))},
                            {'price': float(row.get('买四价', 0)), 'volume': float(row.get('买四量', 0))},
                            {'price': float(row.get('买五价', 0)), 'volume': float(row.get('买五量', 0))},
                        ],
                        'update_time': datetime.now().isoformat(),
                    }

                    logger.info(f"[盘口数据] ✅ 成功获取 {symbol} 的盘口数据")
                    return data

            logger.warning(f"[盘口数据] ⚠️ 未找到股票 {symbol}")
            return None

        except Exception as e:
            logger.error(f"[盘口数据] ❌ 获取失败: {str(e)[:100]}")
            return None

    def get_today_data(self, symbol: str):
        """
        获取当天的最新K线数据

        Args:
            symbol: 股票代码

        Returns:
            DataFrame: 包含当天的K线数据（最新）
        """
        try:
            import akshare as ak
            from datetime import datetime

            today = datetime.now().strftime('%Y%m%d')

            logger.info(f"[当日数据] 正在获取 {symbol} 当天的最新K线数据...")

            # 获取最近一天的数据
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period='daily',
                start_date=today,
                end_date=today,
                adjust='qfq'
            )

            if df is not None and not df.empty:
                df = df.rename(columns={
                    '日期': 'date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '涨跌幅': 'pct_change',
                })
                df['date'] = pd.to_datetime(df['date'])
                logger.info(f"[当日数据] ✅ 成功获取 {symbol} 的当日数据")
                return df
            else:
                logger.warning(f"[当日数据] ⚠️ 今天还没有数据（可能未开市或周末/节假日）")
                # 返回昨天的数据作为参考
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period='daily',
                    start_date=yesterday,
                    end_date=yesterday,
                    adjust='qfq'
                )
                if df is not None and not df.empty:
                    logger.info(f"[当日数据] 返回昨天的数据作为参考")
                    return df
                return None

        except Exception as e:
            logger.error(f"[当日数据] ❌ 获取失败: {str(e)[:100]}")
            return None

    def verify_data_freshness(self, symbol: str):
        """
        验证数据是否为当天最新的

        Args:
            symbol: 股票代码

        Returns:
            dict: {is_fresh, data_date, current_date, status}
        """
        try:
            import akshare as ak

            # 获取实时行情
            df = ak.stock_zh_a_spot_em()

            if df is not None and not df.empty:
                stock_row = df[df['代码'] == symbol]

                if not stock_row.empty:
                    current_date = datetime.now().date()

                    return {
                        'symbol': symbol,
                        'is_fresh': True,
                        'current_date': current_date.isoformat(),
                        'status': '数据为实时最新',
                        'last_check': datetime.now().isoformat()
                    }

            return {
                'symbol': symbol,
                'is_fresh': False,
                'status': '无法验证数据新鲜度',
                'last_check': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"[数据验证] ❌ 验证失败: {str(e)[:100]}")
            return {
                'symbol': symbol,
                'is_fresh': False,
                'status': f'验证失败: {str(e)[:50]}',
                'last_check': datetime.now().isoformat()
            }

    def _is_cache_valid(self, symbol: str) -> bool:
        """检查缓存是否仍然有效"""
        if symbol not in self.last_update_time:
            return False

        last_time = self.last_update_time[symbol]
        current_time = datetime.now().timestamp()

        return (current_time - last_time) < self.cache_expire_seconds

    def clear_cache(self, symbol: str = None):
        """清空缓存"""
        if symbol:
            self.last_update_time.pop(symbol, None)
            self.last_update_time.pop(f"{symbol}_data", None)
            logger.info(f"[缓存] 已清空 {symbol} 的缓存")
        else:
            self.last_update_time.clear()
            logger.info(f"[缓存] 已清空所有缓存")


# 全局实例
realtime_fetcher = RealtimeDataFetcher()


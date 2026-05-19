#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GARP量化因子选股器
基于8个核心量化指标筛选成长股
GARP = Growth at a Reasonable Price（合理价格成长股）

8个核心量化指标：
  1. 盈利预测调整 (earnings_revision)     - 机构盈利预测变化方向
  2. 盈余惊喜 (earnings_surprise)         - 实际业绩超出预期的幅度
  3. 销售额增长 (sales_growth)            - 营业收入增长率(CAGR)
  4. 营业利润率 (operating_margin)        - 核心盈利能力
  5. 自由现金流 (free_cash_flow)          - 现金流质量
  6. 盈利增长 (profit_growth)              - 净利润增长率(CAGR)
  7. 盈利动量 (earnings_momentum)         - 盈利增速变化趋势
  8. 权益报酬率 (ROE)                     - 股东回报率
"""

import io
import logging
import sys
import warnings
from typing import Dict, Optional

import numpy as np
import pandas as pd

# 设置stdout编码（仅在命令行环境）
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
    except:
        pass

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class GARPSelector:
    """GARP量化因子选股器 - 8维度量化筛选"""

    def __init__(self):
        # 8个因子的权重分配（总计100分）
        self.factor_weights = {
            'earnings_revision': 10,    # 盈利预测调整（机构信心）
            'earnings_surprise': 12,    # 盈余惊喜（超预期能力）
            'sales_growth': 13,          # 销售额增长（成长性）
            'operating_margin': 12,      # 营业利润率（盈利能力）
            'free_cash_flow': 13,       # 自由现金流（质量）
            'profit_growth': 15,         # 盈利增长（核心成长）
            'earnings_momentum': 10,     # 盈利动量（趋势）
            'roe': 15                    # 权益报酬率（股东回报）
        }

        self.raw_data = None
        self.scored_stocks = None

    def get_factor_data(self, symbol: str) -> Dict:
        """
        获取单只股票的8个因子数据

        Args:
            symbol: 股票代码

        Returns:
            包含8个因子原始数据的字典
        """
        data = {
            'symbol': symbol,
            'earnings_revision': None,     # 盈利预测调整
            'earnings_surprise': None,     # 盈余惊喜
            'sales_growth': None,          # 销售额3年CAGR
            'operating_margin': None,       # 营业利润率
            'free_cash_flow': None,        # 自由现金流/总资产
            'profit_growth': None,         # 净利润3年CAGR
            'earnings_momentum': None,     # 盈利动量
            'roe': None,                   # 净资产收益率
            'data_success': False
        }

        try:
            import akshare as ak

            print(f"  [GARP] 正在获取 {symbol} 因子数据...")

            # ---------- 获取财务报表数据 ----------
            income_df = ak.stock_financial_report_sina(stock=symbol, symbol="利润表")
            balance_df = ak.stock_financial_report_sina(stock=symbol, symbol="资产负债表")
            cashflow_df = ak.stock_financial_report_sina(stock=symbol, symbol="现金流量表")

            if income_df is not None and not income_df.empty:
                # 按报告日降序排列
                income_df = income_df.sort_values('报告日', ascending=False)
                balance_df = balance_df.sort_values('报告日', ascending=False)
                cashflow_df = cashflow_df.sort_values('报告日', ascending=False)
                print(f"  [GARP] ✓ 财务报表 {len(income_df)} 期数据")

            # ---------- 1. 销售额增长 (sales_growth) - 3年CAGR ----------
            data['sales_growth'] = self._calc_sales_cagr(income_df)
            if data['sales_growth'] is not None:
                print(f"  [GARP] ✓ 销售额增长CAGR: {data['sales_growth']:.2f}%")

            # ---------- 2. 营业利润率 (operating_margin) ----------
            data['operating_margin'] = self._calc_operating_margin(income_df)
            if data['operating_margin'] is not None:
                print(f"  [GARP] ✓ 营业利润率: {data['operating_margin']:.2f}%")

            # ---------- 3. 盈利增长 (profit_growth) - 3年CAGR ----------
            data['profit_growth'] = self._calc_profit_cagr(income_df)
            if data['profit_growth'] is not None:
                print(f"  [GARP] ✓ 净利润增长CAGR: {data['profit_growth']:.2f}%")

            # ---------- 4. 盈利动量 (earnings_momentum) ----------
            data['earnings_momentum'] = self._calc_momentum(income_df)
            if data['earnings_momentum'] is not None:
                print(f"  [GARP] ✓ 盈利动量: {data['earnings_momentum']:.2f}")

            # ---------- 5. 权益报酬率 (ROE) ----------
            data['roe'] = self._calc_roe(income_df, balance_df)
            if data['roe'] is not None:
                print(f"  [GARP] ✓ ROE: {data['roe']:.2f}%")

            # ---------- 6. 自由现金流 (free_cash_flow) ----------
            if cashflow_df is not None and not cashflow_df.empty:
                # 按报告日降序排列
                cashflow_df = cashflow_df.sort_values('报告日', ascending=False)
            data['free_cash_flow'] = self._calc_fcf_ratio(cashflow_df, balance_df)
            if data['free_cash_flow'] is not None:
                print(f"  [GARP] ✓ 自由现金流比: {data['free_cash_flow']:.2f}%")

            # ---------- 7-8. 盈利预测调整 & 盈余惊喜 ----------
            # 这两个指标需要机构研报数据，这里用季报超预期来近似
            surprise_data = self._calc_earnings_surprise(income_df)
            data['earnings_surprise'] = surprise_data
            if surprise_data is not None:
                print(f"  [GARP] ✓ 盈余惊喜: {data['earnings_surprise']:.2f}%")

            # 盈利预测调整用增长动量来近似
            if data['earnings_momentum'] is not None:
                data['earnings_revision'] = min(100, max(0, 50 + data['earnings_momentum'] * 2))
                print(f"  [GARP] ✓ 盈利预测调整(估算): {data['earnings_revision']:.1f}")

            data['data_success'] = True
            print(f"  [GARP] ✅ 8因子数据获取完成")

        except Exception as e:
            logger.warning(f"  [GARP] ❌ 因子数据获取失败: {e}")
            import traceback
            traceback.print_exc()

        return data

    def _calc_sales_cagr(self, df: pd.DataFrame) -> Optional[float]:
        """
        计算销售额3年CAGR（年复合增长率）- 只使用年报数据
        """
        if df is None or df.empty:
            return None

        try:
            from datetime import datetime
            current_year = datetime.now().year

            # 查找营收列
            cols = [c for c in df.columns if '营业总收入' in str(c)]
            if not cols:
                cols = [c for c in df.columns if '营业收入' in str(c)]
            if not cols:
                return None

            col = cols[0]

            # 只取年报数据（报告日以1231结尾，且日期<=去年）
            yearly_df = df[df['报告日'].astype(str).str.endswith('1231')].copy()
            yearly_df = yearly_df[yearly_df['报告日'].astype(str).str[:4].astype(int) < current_year - 1]
            yearly_df = yearly_df.sort_values('报告日')

            if len(yearly_df) < 4:
                return None

            # 取最近4年年报
            values = yearly_df[col].tail(4).values
            start = float(values[0])
            end = float(values[-1])
            years = len(values) - 1

            if start <= 0 or years < 1:
                return None

            cagr = ((end / start) ** (1 / years) - 1) * 100
            return round(cagr, 2)

        except Exception as e:
            logger.warning(f"  [GARP] 销售额CAGR计算失败: {e}")
            return None

    def _calc_operating_margin(self, df: pd.DataFrame) -> Optional[float]:
        """
        计算营业利润率 = 营业利润 / 营业收入
        """
        if df is None or df.empty:
            return None

        try:
            op_cols = [c for c in df.columns if '营业利润' in str(c)]
            rev_cols = [c for c in df.columns if '营业总收入' in str(c)]
            if not rev_cols:
                rev_cols = [c for c in df.columns if '营业收入' in str(c)]

            if not op_cols or not rev_cols:
                return None

            op = float(df[op_cols[0]].iloc[0])
            rev = float(df[rev_cols[0]].iloc[0])

            if rev == 0:
                return None

            margin = (op / rev) * 100
            return round(margin, 2)

        except Exception as e:
            logger.warning(f"  [GARP] 营业利润率计算失败: {e}")
            return None

    def _calc_profit_cagr(self, df: pd.DataFrame) -> Optional[float]:
        """
        计算净利润3年CAGR - 只使用年报数据
        """
        if df is None or df.empty:
            return None

        try:
            from datetime import datetime
            current_year = datetime.now().year

            # 优先使用归母净利润
            cols = [c for c in df.columns if '净利润' in str(c) and '归属' in str(c)]
            if not cols:
                cols = [c for c in df.columns if '净利润' in str(c) and '少数' not in str(c)]
            if not cols:
                return None

            col = cols[0]

            # 只取年报数据（报告日以1231结尾，且日期<=去年）
            yearly_df = df[df['报告日'].astype(str).str.endswith('1231')].copy()
            yearly_df = yearly_df[yearly_df['报告日'].astype(str).str[:4].astype(int) < current_year - 1]
            yearly_df = yearly_df.sort_values('报告日')

            if len(yearly_df) < 4:
                return None

            # 取最近4年年报
            values = yearly_df[col].tail(4).values
            start = float(values[0])
            end = float(values[-1])
            years = len(values) - 1

            if start <= 0 or years < 1:
                return None

            cagr = ((end / start) ** (1 / years) - 1) * 100
            return round(cagr, 2)

        except Exception as e:
            logger.warning(f"  [GARP] 净利润CAGR计算失败: {e}")
            return None

    def _calc_momentum(self, df: pd.DataFrame) -> Optional[float]:
        """
        计算盈利动量（近2期增速变化）

        动量 = 本季增速 - 上季增速
        - 正值：加速增长
        - 负值：减速
        - 动量越大，说明增长势头越强劲
        """
        if df is None or df.empty:
            return 0.0

        try:
            cols = [c for c in df.columns if '净利润' in str(c) and '归属' in str(c)]
            if not cols:
                cols = [c for c in df.columns if '净利润' in str(c)]
            if not cols:
                return 0.0

            col = cols[0]
            values = df[col].dropna().head(8)

            if len(values) < 4:
                return 0.0

            # 计算最近2期和之前2期的增速
            recent = [float(values.iloc[i]) for i in range(2)]
            prev = [float(values.iloc[i + 2]) for i in range(2)]

            # 避免除零
            if any(v == 0 for v in recent + prev):
                return 0.0

            # 环比增速
            growth_now = (recent[0] - recent[1]) / abs(recent[1])
            growth_prev = (prev[0] - prev[1]) / abs(prev[1])

            # 动量 = 增速变化（单位：百分比点）
            momentum = (growth_now - growth_prev) * 100

            # 限制在合理范围
            return round(max(-50, min(50, momentum)), 2)

        except Exception as e:
            logger.warning(f"  [GARP] 盈利动量计算失败: {e}")
            return 0.0

    def _calc_roe(self, income_df: pd.DataFrame, balance_df: pd.DataFrame) -> Optional[float]:
        """
        计算ROE（净资产收益率）= 净利润 / 归母净资产
        巴菲特最看重的单一指标
        """
        if income_df is None or income_df.empty or balance_df is None or balance_df.empty:
            return None

        try:
            # 优先使用归母净利润
            net_profit_cols = [c for c in income_df.columns if '净利润' in str(c) and '归属' in str(c)]
            if not net_profit_cols:
                net_profit_cols = [c for c in income_df.columns if '净利润' in str(c) and '少数' not in str(c)]

            # 查找归母股东权益（优先）或所有者权益合计
            equity_cols = [c for c in balance_df.columns if '归属于母公司股东权益' in str(c)]
            if not equity_cols:
                equity_cols = [c for c in balance_df.columns if '所有者权益(或股东权益)合计' in str(c)]
            if not equity_cols:
                equity_cols = [c for c in balance_df.columns if '所有者权益' in str(c)]

            if not net_profit_cols or not equity_cols:
                logger.warning(f"  [GARP] ROE计算失败: 找不到列 net_profit={len(net_profit_cols)}, equity={len(equity_cols)}")
                return None

            net_profit = float(income_df[net_profit_cols[0]].iloc[0])
            equity = float(balance_df[equity_cols[0]].iloc[0])

            if equity == 0 or np.isnan(equity) or np.isinf(equity):
                logger.warning(f"  [GARP] ROE计算失败: equity={equity}")
                return None

            roe = (net_profit / equity) * 100
            if np.isnan(roe) or np.isinf(roe):
                return None

            logger.info(f"  [GARP] ROE: {roe:.2f}% (净利={net_profit/1e8:.2f}亿, 权益={equity/1e8:.2f}亿)")
            return round(roe, 2)

        except Exception as e:
            logger.warning(f"  [GARP] ROE计算失败: {e}")
            return None

    def _calc_fcf_ratio(self, cashflow_df: pd.DataFrame, balance_df: pd.DataFrame) -> Optional[float]:
        """
        计算自由现金流/总资产
        """
        if cashflow_df is None or cashflow_df.empty or balance_df is None or balance_df.empty:
            return None

        try:
            # 经营现金流净额
            op_cf_cols = [c for c in cashflow_df.columns if '经营活动产生的现金流量净额' in c]
            asset_cols = [c for c in balance_df.columns if '资产总计' in c]

            if not op_cf_cols or not asset_cols:
                return None

            op_cf = float(cashflow_df[op_cf_cols[0]].iloc[0])
            assets = float(balance_df[asset_cols[0]].iloc[0])

            if assets <= 0 or np.isnan(assets) or np.isinf(assets):
                return None

            # 自由现金流/总资产
            ratio = (op_cf / assets) * 100
            if np.isnan(ratio) or np.isinf(ratio):
                return None

            logger.info(f"  [GARP] 自由现金流比: {ratio:.2f}% (经营现金流:{op_cf/1e8:.1f}亿, 总资产:{assets/1e8:.1f}亿)")
            return round(ratio, 2)

        except Exception as e:
            logger.warning(f"  [GARP] 自由现金流计算失败: {e}")
            return None

    def _calc_earnings_surprise(self, df: pd.DataFrame) -> Optional[float]:
        """
        计算盈余惊喜（简化版）

        通过季报业绩增长来估算：
        - 本季净利润 vs 上季净利润 的增速变化
        - 增速超过历史平均视为"惊喜"
        """
        if df is None or df.empty:
            return None

        try:
            cols = [c for c in df.columns if '净利润' in str(c) and '归属' in str(c)]
            if not cols:
                cols = [c for c in df.columns if '净利润' in str(c)]
            if not cols:
                return None

            col = cols[0]
            values = df[col].dropna().head(8)

            if len(values) < 4:
                return None

            # 计算近4期的平均增速
            growths = []
            for i in range(1, min(4, len(values))):
                if values.iloc[i-1] != 0:
                    g = (values.iloc[i] - values.iloc[i-1]) / abs(values.iloc[i-1]) * 100
                    growths.append(g)

            if not growths:
                return 0.0

            # 平均增速
            avg_growth = np.mean(growths)

            # 最近一期的惊喜程度（相比平均）
            latest_growth = growths[0] if growths else 0
            surprise = latest_growth - avg_growth

            return round(max(-30, min(30, surprise)), 2)

        except Exception as e:
            logger.warning(f"  [GARP] 盈余惊喜计算失败: {e}")
            return 0.0

    def score_factor(self, value: Optional[float], metric: str) -> float:
        """
        将原始指标值转换为0-100的评分

        Args:
            value: 原始指标值
            metric: 指标名称

        Returns:
            0-100的评分
        """
        if value is None:
            return 30.0  # 无数据给基准分

        # 处理NaN
        if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
            return 30.0

        # 各指标的评分阈值
        thresholds = {
            # 越高越好的指标 (excellent, good, ok, neutral)
            'earnings_revision': {'ex': 80, 'good': 60, 'ok': 40, 'neutral': 20},  # %
            'earnings_surprise': {'ex': 20, 'good': 10, 'ok': 0, 'neutral': -10},  # %
            'sales_growth': {'ex': 30, 'good': 20, 'ok': 10, 'neutral': -10},  # %
            'operating_margin': {'ex': 30, 'good': 20, 'ok': 10, 'neutral': 0},  # %
            'free_cash_flow': {'ex': 10, 'good': 5, 'ok': 0, 'neutral': -5},  # %
            'profit_growth': {'ex': 30, 'good': 20, 'ok': 10, 'neutral': -10},  # %
            'roe': {'ex': 25, 'good': 15, 'ok': 8, 'neutral': 0},  # %
        }

        t = thresholds.get(metric, {'ex': 30, 'good': 20, 'ok': 10, 'neutral': -10})

        # 盈利动量特殊处理（可正可负）
        if metric == 'earnings_momentum':
            if value >= 30:
                return 100.0
            elif value >= 15:
                return 70 + 30 * (value - 15) / 15
            elif value >= 0:
                return 40 + 30 * value / 15
            elif value >= -15:
                return 10 + 30 * (value + 15) / 15
            else:
                return max(0, 10 * (value + 30) / 15)

        # 避免除零
        if t['neutral'] == 0 or t['ok'] == t['neutral']:
            if value >= t['ex']:
                return 100.0
            elif value >= t['good']:
                return 70 + 30 * (value - t['good']) / (t['ex'] - t['good'])
            elif value >= t['ok']:
                return 40 + 30 * (value - t['ok']) / (t['good'] - t['ok'])
            else:
                return max(0, 30 * value / max(t['ok'], 0.1))

        # 越高越好的指标
        if value >= t['ex']:
            return 100.0
        elif value >= t['good']:
            score = 70 + 30 * (value - t['good']) / (t['ex'] - t['good'])
        elif value >= t['ok']:
            score = 40 + 30 * (value - t['ok']) / (t['good'] - t['ok'])
        elif value >= t['neutral']:
            score = 10 + 30 * (value - t['neutral']) / (t['ok'] - t['neutral'])
        else:
            score = max(0, 10 * value / t['neutral'])

        return round(max(0, min(100, score)), 1)

    def score_stock(self, factor_data: Dict) -> Dict:
        """
        对单只股票进行综合评分

        Args:
            factor_data: 包含8个因子原始数据的字典

        Returns:
            包含各因子得分和综合得分的字典
        """
        symbol = factor_data.get('symbol', 'Unknown')

        if not factor_data.get('data_success'):
            return {
                'symbol': symbol,
                'total_score': 0,
                'rating': '❌ 数据获取失败',
                'data_success': False
            }

        factor_scores = {}
        factor_values = {}

        print(f"\n{'='*60}")
        print(f"📈 GARP量化因子评分: {symbol}")
        print(f"{'='*60}")

        for metric in self.factor_weights.keys():
            raw_value = factor_data.get(metric)
            score = self.score_factor(raw_value, metric)
            factor_scores[metric] = score
            factor_values[metric] = raw_value

            # 打印各因子得分
            metric_names = {
                'earnings_revision': '盈利预测调整',
                'earnings_surprise': '盈余惊喜',
                'sales_growth': '销售额增长',
                'operating_margin': '营业利润率',
                'free_cash_flow': '自由现金流',
                'profit_growth': '盈利增长',
                'earnings_momentum': '盈利动量',
                'roe': '权益报酬率(ROE)'
            }
            value_str = f"{raw_value:.2f}" if isinstance(raw_value, float) else str(raw_value)
            print(f"  {metric_names.get(metric, metric)}: {value_str} → 得分 {score:.1f}")

        # 加权总分
        total_score = sum(
            factor_scores[m] * (self.factor_weights[m] / 100)
            for m in self.factor_weights
        )
        total_score = round(total_score, 1)

        # 等级评定
        if total_score >= 75:
            rating = "⭐⭐⭐ 强烈推荐"
        elif total_score >= 55:
            rating = "⭐⭐ 值得关注"
        elif total_score >= 35:
            rating = "⭐ 勉强合格"
        else:
            rating = "❌ 不符合GARP标准"

        print(f"\n  综合得分: {total_score} 分 - {rating}")

        return {
            'symbol': symbol,
            'total_score': total_score,
            'rating': rating,
            'factor_scores': factor_scores,
            'factor_values': factor_values,
            'data_success': True
        }

    def format_report(self, score_result: Dict) -> str:
        """生成可读的分析报告"""
        if not score_result.get('data_success'):
            return f"❌ {score_result.get('symbol')} 数据获取失败"

        metric_names = {
            'earnings_revision': '盈利预测调整',
            'earnings_surprise': '盈余惊喜',
            'sales_growth': '销售额增长(CAGR)',
            'operating_margin': '营业利润率',
            'free_cash_flow': '自由现金流比',
            'profit_growth': '盈利增长(CAGR)',
            'earnings_momentum': '盈利动量',
            'roe': '权益报酬率(ROE)'
        }

        lines = [
            f"\n{'='*60}",
            f"📊 GARP量化因子分析报告",
            f"{'='*60}",
            f"股票代码: {score_result.get('symbol')}",
            f"",
            f"🎯 综合评分: {score_result.get('total_score', 0)} 分",
            f"📋 评级: {score_result.get('rating', 'N/A')}",
            f"",
            f"{'─'*60}",
            f"{'因子':<20} {'原始值':>12} {'得分':>8} {'权重':>8}",
            f"{'─'*60}",
        ]

        factor_scores = score_result.get('factor_scores', {})
        factor_values = score_result.get('factor_values', {})

        for metric, weight in self.factor_weights.items():
            name = metric_names.get(metric, metric)
            value = factor_values.get(metric)
            score = factor_scores.get(metric, 0)

            if isinstance(value, float):
                value_str = f"{value:.2f}%"
            else:
                value_str = str(value) if value is not None else "N/A"

            lines.append(f"{name:<20} {value_str:>12} {score:>7.1f} {weight:>7d}%")

        lines.append(f"{'─'*60}")
        lines.append(f"{'='*60}\n")

        return "\n".join(lines)


# ============ 快速筛选入口 ============

def fast_scan_garp_stocks() -> pd.DataFrame:
    """
    快速筛选：直接通过问财语句获取符合GARP标准的股票

    Returns:
        DataFrame: 初步筛选结果
    """
    import pywencai

    print(f"\n{'='*60}")
    print(f"🔍 GARP快速初筛（问财查询）")
    print(f"{'='*60}")

    queries = [
        # 方案1: 核心GARP指标组合
        "净利润同比增长大于15%，净资产收益率大于12%，营业利润大于0，非st",
        # 方案2: 成长性优先
        "净利润同比增长大于20%，净资产收益率大于10%，非st",
        # 方案3: 盈利质量优先
        "净资产收益率大于15%，营业利润率大于15%，非st",
    ]

    for i, query in enumerate(queries, 1):
        try:
            print(f"  尝试方案{i}: {query[:50]}...")
            result = pywencai.get(query=query, loop=True, retry=2)
            if result is not None:
                if isinstance(result, pd.DataFrame) and not result.empty:
                    print(f"  ✅ 方案{i}成功，获取 {len(result)} 只股票")
                    return result
        except Exception as e:
            print(f"  ⚠️ 方案{i}失败: {e}")
            continue

    print("  ❌ 所有问财查询方案都失败")
    return pd.DataFrame()


# ============ 主测试入口 ============

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 GARP量化因子选股器测试")
    print("=" * 60)

    selector = GARPSelector()

    # 测试单只股票
    test_symbols = ["600519", "000001", "300750"]  # 贵州茅台、平安银行、宁德时代

    for symbol in test_symbols:
        print(f"\n{'#'*60}")
        print(f"# 正在分析 {symbol}...")
        print(f"{'#'*60}")

        # 获取因子数据
        factor_data = selector.get_factor_data(symbol)

        # 评分
        score_result = selector.score_stock(factor_data)

        # 打印报告
        print(selector.format_report(score_result))

        print("\n")


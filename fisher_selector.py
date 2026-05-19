#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fisher定生成年股选股器
基于《怎样选择成长股》8+3原则设计
重点实现可量化的维度

费雪15年持续增长选股框架：
  原则1: 优秀销售组织（代理指标：营收CAGR、应收账款周转）
  原则2: 创新产品与研发（代理指标：研发支出占比、无形资产）
  原则3: 令人满意的利润率（代理指标：ROIC、净利率、毛利率稳定性）
  原则4: 优秀的劳资/人事关系（代理指标：员工总数趋势、高管薪酬占比）
  原则5: 高效的管理层关系（代理指标：大股东质押比例、高管变动频率）
  原则6: 精细的成本分析与财务管控（代理指标：销售费用率、存货周转）
  原则7: 区别于竞争对手的独特商业特质（代理指标：毛利率稳定性、商誉占比）
  原则8: 管理层的诚信与坦诚（代理指标：审计意见、历史监管处罚）

扩展三原则：
  原则9: 保守的会计政策（代理指标：现金流/净利润）
  原则10: 有利的收购能力（代理指标：并购历史数据）
  原则11: 出色的投资回报率ROIC（核心量化指标）
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


class FisherSelector:
    """Fisher成长股选股器 - 11维度综合筛选"""

    def __init__(self):
        # 11个维度的权重分配（总计100分）
        self.dimension_weights = {
            # 维度一：成长性（30分）
            'revenue_cagr': 10,          # 营收3年CAGR
            'profit_cagr': 10,           # 净利润3年CAGR
            'non_recurring_adjust': 10,  # 扣非净利润质量

            # 维度二：盈利能力（25分）
            'roic': 12,                  # 投资资本回报率
            'net_margin': 8,             # 净利率
            'margin_stability': 5,       # 毛利率稳定性

            # 维度三：运营效率（20分）
            'inventory_turnover': 7,    # 存货周转
            'receivable_turnover': 6,   # 应收账款周转
            'sales_expense_ratio': 7,   # 销售费用率

            # 维度四：财务质量（15分）
            'cash_flow_quality': 10,    # 经营现金流/净利润
            'debt_ratio': 5,           # 资产负债率

            # 维度五：创新研发（10分）
            'rd_expense_ratio': 10,     # 研发支出/营收
        }

        self.raw_data = None
        self.scored_stocks = None

    def get_financial_data(self, symbol: str) -> Dict:
        """
        获取Fisher分析所需的财务数据

        Args:
            symbol: 股票代码

        Returns:
            包含财务数据的字典
        """
        data = {
            'symbol': symbol,
            'data_success': False,
            'raw_data': {}
        }

        try:
            import akshare as ak

            print(f"  [Fisher] 正在获取 {symbol} 财务数据...")

            # 获取3年（12期）财务数据
            income_df = ak.stock_financial_report_sina(stock=symbol, symbol="利润表")
            balance_df = ak.stock_financial_report_sina(stock=symbol, symbol="资产负债表")
            cashflow_df = ak.stock_financial_report_sina(stock=symbol, symbol="现金流量表")

            if income_df is not None and not income_df.empty:
                # 按报告日降序排列，最新的在前面
                income_df = income_df.sort_values('报告日', ascending=False)
                print(f"  [Fisher] ✓ 利润表 {len(income_df)} 期数据")

            if balance_df is not None and not balance_df.empty:
                # 按报告日降序排列
                balance_df = balance_df.sort_values('报告日', ascending=False)
                print(f"  [Fisher] ✓ 资产负债表 {len(balance_df)} 期数据")

            if cashflow_df is not None and not cashflow_df.empty:
                # 按报告日降序排列
                cashflow_df = cashflow_df.sort_values('报告日', ascending=False)
                print(f"  [Fisher] ✓ 现金流量表 {len(cashflow_df)} 期数据")

            data['raw_data'] = {
                'income': income_df,
                'balance': balance_df,
                'cashflow': cashflow_df
            }
            data['data_success'] = True

        except Exception as e:
            logger.warning(f"  [Fisher] ❌ 财务数据获取失败: {e}")

        return data

    def calculate_metrics(self, raw_data: Dict) -> Dict:
        """
        计算所有Fisher指标

        Args:
            raw_data: 原始财务数据

        Returns:
            计算后的各项指标字典
        """
        metrics = {}
        income_df = raw_data.get('income')
        balance_df = raw_data.get('balance')
        cashflow_df = raw_data.get('cashflow')

        if income_df is None or income_df.empty:
            return metrics

        # ---------- 维度一：成长性 ----------

        from datetime import datetime
        current_year = datetime.now().year

        # 辅助函数：提取年报数据（过滤季报和中报，排除未来日期）
        def get_yearly_data(df, col_name):
            """只保留年报数据（报告日以1231结尾，且日期<=当前年份-1）"""
            if col_name not in df.columns:
                return pd.Series(dtype=float)
            yearly_df = df[df['报告日'].astype(str).str.endswith('1231')].copy()
            # 排除未来日期（最新年报应该是去年或更早）
            # 使用更保守的过滤：只接受 < current_year - 1（即去年及更早）
            yearly_df = yearly_df[yearly_df['报告日'].astype(str).str[:4].astype(int) < current_year - 1]
            return yearly_df[col_name].sort_values().dropna()

        # 1. 营收CAGR（用近4年年报）
        rev_col = None
        for col in ['营业总收入', '营业收入']:
            if col in income_df.columns:
                rev_col = col
                break

        if rev_col:
            yearly_revs = get_yearly_data(income_df, rev_col)
            if len(yearly_revs) >= 4:
                # 取最近4年年报
                recent_revs = yearly_revs.tail(4).values
                n = len(recent_revs) - 1  # 时间跨度
                if recent_revs[0] > 0 and n >= 1:
                    cagr = ((recent_revs[-1] / recent_revs[0]) ** (1 / n) - 1) * 100
                    # 转换为亿元便于阅读
                    metrics['revenue_cagr'] = round(cagr, 2)
                    logger.info(f"  [Fisher] 营收CAGR: {metrics['revenue_cagr']:.2f}%")
                    logger.info(f"    起始: {recent_revs[0]/1e8:.2f}亿, 结束: {recent_revs[-1]/1e8:.2f}亿, {n}年")

        # 2. 净利润CAGR（用近4年年报）
        profit_col = None
        for col in income_df.columns:
            if '净利润' in str(col) and '归属' in str(col):
                profit_col = col
                break

        if profit_col:
            yearly_profits = get_yearly_data(income_df, profit_col)
            if len(yearly_profits) >= 4:
                recent_profits = yearly_profits.tail(4).values
                n = len(recent_profits) - 1
                if recent_profits[0] > 0 and n >= 1:
                    cagr = ((recent_profits[-1] / recent_profits[0]) ** (1 / n) - 1) * 100
                    metrics['profit_cagr'] = round(cagr, 2)
                    logger.info(f"  [Fisher] 净利润CAGR: {metrics['profit_cagr']:.2f}%")
                    logger.info(f"    起始: {recent_profits[0]/1e8:.2f}亿, 结束: {recent_profits[-1]/1e8:.2f}亿, {n}年")

        # 3. 扣非净利润质量（扣非/净利润 > 80% 为优质）
        gaap_cols = [c for c in income_df.columns if '净利润' in str(c) and '归属' in str(c)]
        non_recurring_cols = [c for c in income_df.columns if '非经常性损益' in str(c)]

        if gaap_cols:
            gaap = float(income_df[gaap_cols[0]].iloc[0])
            if gaap > 0:
                if non_recurring_cols:
                    non_recurring = abs(float(income_df[non_recurring_cols[0]].iloc[0])) \
                        if not pd.isna(income_df[non_recurring_cols[0]].iloc[0]) else 0
                    quality = ((gaap - non_recurring) / gaap) * 100
                else:
                    quality = 100.0  # 无非经常性损益数据，假设质量好
                metrics['non_recurring_adjust'] = round(quality, 2)
                logger.info(f"  [Fisher] 扣非净利润质量: {metrics['non_recurring_adjust']:.2f}%")

        # ---------- 维度二：盈利能力 ----------

        # 4. ROIC（投资资本回报率）= 净利润/（归母权益+有息负债）
        if balance_df is not None and not balance_df.empty:
            # 优先使用归母股东权益
            equity_cols = [c for c in balance_df.columns if '归属于母公司股东权益' in str(c)]
            if not equity_cols:
                equity_cols = [c for c in balance_df.columns if '所有者权益(或股东权益)合计' in str(c)]
            if not equity_cols:
                equity_cols = [c for c in balance_df.columns if '所有者权益' in str(c)]

            liability_cols = [c for c in balance_df.columns if '负债合计' in str(c)]

            if gaap_cols and equity_cols:
                net_profit = float(income_df[gaap_cols[0]].iloc[0])
                equity = float(balance_df[equity_cols[0]].iloc[0])
                liability = float(balance_df[liability_cols[0]].iloc[0]) if liability_cols else 0

                if np.isnan(equity) or np.isinf(equity) or equity == 0:
                    logger.warning(f"  [Fisher] ROIC计算失败: equity={equity}")
                else:
                    # 简化：有息负债按40%计
                    invested_capital = equity + liability * 0.4
                    if invested_capital > 0:
                        roic = (net_profit / invested_capital) * 100
                        if not np.isnan(roic) and not np.isinf(roic):
                            metrics['roic'] = round(roic, 2)
                            logger.info(f"  [Fisher] ROIC: {metrics['roic']:.2f}%")

        # 5. 净利率
        if rev_col and gaap_cols:
            revenue = float(income_df[rev_col].iloc[0])
            profit = float(income_df[gaap_cols[0]].iloc[0])
            if revenue > 0:
                margin = (profit / revenue) * 100
                metrics['net_margin'] = round(margin, 2)
                logger.info(f"  [Fisher] 净利率: {metrics['net_margin']:.2f}%")

        # 6. 毛利率稳定性（3年标准差，越低越稳定）
        gross_cols = [c for c in income_df.columns if '毛利' in str(c)]
        if gross_cols and rev_col:
            values = income_df[gross_cols[0]].dropna().head(12)
            revenues = income_df[rev_col].dropna().head(12)
            if len(values) >= 4 and len(revenues) == len(values):
                valid = []
                for i in range(len(values)):
                    if float(revenues.iloc[i]) > 0:
                        valid.append(float(values.iloc[i]) / float(revenues.iloc[i]) * 100)
                if len(valid) >= 4:
                    # 毛利率标准差越低越好，取一个转换
                    std = np.std(valid)
                    # 稳定性 = 100 - min(50, std*5)，std低于10%为优秀
                    stability = max(0, 100 - std * 5)
                    metrics['margin_stability'] = round(stability, 2)
                    logger.info(f"  [Fisher] 毛利率稳定性: {metrics['margin_stability']:.2f}")

        # ---------- 维度三：运营效率 ----------

        # 7. 存货周转天数（越低越好）
        if balance_df is not None and not balance_df.empty:
            inv_cols = [c for c in balance_df.columns if '存货' in str(c)]
            if inv_cols and rev_col:
                inv = float(balance_df[inv_cols[0]].iloc[0])
                revenue = float(income_df[rev_col].iloc[0]) / 4  # 单季营收
                if revenue > 0:
                    days = inv / revenue * 365 / 4
                    metrics['inventory_turnover'] = round(days, 1)
                    logger.info(f"  [Fisher] 存货周转天数: {metrics['inventory_turnover']:.1f}天")

        # 8. 应收账款周转天数（越低越好）
        ar_cols = [c for c in balance_df.columns if '应收' in str(c) and '票据' not in str(c)]
        if ar_cols and rev_col:
            ar = float(balance_df[ar_cols[0]].iloc[0])
            revenue = float(income_df[rev_col].iloc[0]) / 4
            if revenue > 0:
                days = ar / revenue * 365 / 4
                metrics['receivable_turnover'] = round(days, 1)
                logger.info(f"  [Fisher] 应收账款天数: {metrics['receivable_turnover']:.1f}天")

        # 9. 销售费用率（越低越好，说明销售效率高）
        expense_cols = [c for c in income_df.columns if '销售费用' in str(c)]
        if expense_cols and rev_col:
            expense = float(income_df[expense_cols[0]].iloc[0])
            revenue = float(income_df[rev_col].iloc[0])
            if revenue > 0:
                ratio = (expense / revenue) * 100
                metrics['sales_expense_ratio'] = round(ratio, 2)
                logger.info(f"  [Fisher] 销售费用率: {metrics['sales_expense_ratio']:.2f}%")

        # ---------- 维度四：财务质量 ----------

        # 10. 经营现金流/净利润（>100%为优质）
        if cashflow_df is not None and not cashflow_df.empty:
            op_cf_cols = [c for c in cashflow_df.columns if '经营活动产生的现金流量净额' in str(c)]
            if op_cf_cols and gaap_cols:
                op_cf = float(cashflow_df[op_cf_cols[0]].iloc[0])
                net_profit = float(income_df[gaap_cols[0]].iloc[0])
                if net_profit > 0:
                    ratio = (op_cf / net_profit) * 100
                    metrics['cash_flow_quality'] = round(ratio, 2)
                    logger.info(f"  [Fisher] 现金流质量: {metrics['cash_flow_quality']:.2f}%")

        # 11. 资产负债率（越低越好，但也要看行业）
        if balance_df is not None and not balance_df.empty:
            liability_cols = [c for c in balance_df.columns if '负债合计' in str(c)]
            asset_cols = [c for c in balance_df.columns if '资产总计' in str(c)]
            if liability_cols and asset_cols:
                liability = float(balance_df[liability_cols[0]].iloc[0])
                asset = float(balance_df[asset_cols[0]].iloc[0])
                if asset > 0:
                    ratio = (liability / asset) * 100
                    metrics['debt_ratio'] = round(ratio, 2)
                    logger.info(f"  [Fisher] 资产负债率: {metrics['debt_ratio']:.2f}%")

        # ---------- 维度五：研发创新 ----------

        # 12. 研发支出占比（科技股重要）
        rd_cols = [c for c in income_df.columns if '研发' in str(c)]
        if rd_cols and rev_col:
            rd = abs(float(income_df[rd_cols[0]].iloc[0]))
            revenue = float(income_df[rev_col].iloc[0])
            if revenue > 0:
                ratio = (rd / revenue) * 100
                metrics['rd_expense_ratio'] = round(ratio, 2)
                logger.info(f"  [Fisher] 研发支出占比: {metrics['rd_expense_ratio']:.2f}%")

        return metrics

    def score_dimension(self, value: Optional[float], dimension: str) -> float:
        """
        将指标值转换为0-100评分

        Args:
            value: 原始指标值
            dimension: 指标名称

        Returns:
            0-100的评分
        """
        if value is None:
            return 25.0  # 无数据给基准分

        # 处理NaN和Inf
        if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
            return 25.0

        # 各维度评分标准
        thresholds = {
            # 越低越好的指标
            'inventory_turnover': {'ex': 30, 'good': 60, 'ok': 120, 'neutral': 200},  # 天数
            'receivable_turnover': {'ex': 15, 'good': 30, 'ok': 60, 'neutral': 120},  # 天数
            'sales_expense_ratio': {'ex': 3, 'good': 8, 'ok': 15, 'neutral': 30},  # 越低越好
            'debt_ratio': {'ex': 20, 'good': 40, 'ok': 60, 'neutral': 80},  # 越低越好
            # 越高越好的指标
            'revenue_cagr': {'ex': 30, 'good': 20, 'ok': 10, 'neutral': 0},  # %
            'profit_cagr': {'ex': 30, 'good': 20, 'ok': 10, 'neutral': 0},  # %
            'non_recurring_adjust': {'ex': 100, 'good': 95, 'ok': 85, 'neutral': 70},  # %
            'roic': {'ex': 20, 'good': 15, 'ok': 10, 'neutral': 5},  # %
            'net_margin': {'ex': 25, 'good': 15, 'ok': 8, 'neutral': 0},  # %
            'margin_stability': {'ex': 95, 'good': 85, 'ok': 70, 'neutral': 50},  # 稳定性得分
            'cash_flow_quality': {'ex': 120, 'good': 100, 'ok': 80, 'neutral': 50},  # %
            'rd_expense_ratio': {'ex': 15, 'good': 8, 'ok': 3, 'neutral': 0},  # %
        }

        t = thresholds.get(dimension, {'ex': 20, 'good': 10, 'ok': 5, 'neutral': 0})

        # 判断是否为"越低越好"的指标
        lower_is_better = dimension in [
            'inventory_turnover', 'receivable_turnover',
            'sales_expense_ratio', 'debt_ratio'
        ]

        if lower_is_better:
            # 越低越好
            if value <= t['ex']:
                return 100.0
            elif value <= t['good']:
                score = 70 + 30 * (t['good'] - value) / (t['good'] - t['ex'])
            elif value <= t['ok']:
                score = 40 + 30 * (t['ok'] - value) / (t['ok'] - t['good'])
            elif value <= t['neutral']:
                score = 10 + 30 * (t['neutral'] - value) / (t['neutral'] - t['ok'])
            else:
                score = max(0, 10 * t['neutral'] / value)
        else:
            # 越高越好
            if value >= t['ex']:
                return 100.0
            elif value >= t['good']:
                score = 70 + 30 * (value - t['good']) / (t['ex'] - t['good'])
            elif value >= t['ok']:
                score = 40 + 30 * (value - t['ok']) / (t['good'] - t['ok'])
            elif value >= t['neutral']:
                score = 10 + 30 * (value - t['neutral']) / (t['ok'] - t['neutral'])
            else:
                score = max(0, 10 * value / max(t['neutral'], 0.1))

        return round(max(0, min(100, score)), 1)

    def score_stock(self, symbol: str) -> Dict:
        """
        对单只股票进行Fisher综合评分

        Args:
            symbol: 股票代码

        Returns:
            包含评分结果的字典
        """
        print(f"\n{'='*60}")
        print(f"🐟 Fisher定生成年股分析: {symbol}")
        print(f"{'='*60}")

        # 1. 获取数据
        raw = self.get_financial_data(symbol)

        if not raw.get('data_success'):
            return {
                'symbol': symbol,
                'total_score': 0,
                'rating': '❌ 数据获取失败',
                'data_success': False
            }

        # 2. 计算指标
        metrics = self.calculate_metrics(raw['raw_data'])
        print(f"  [Fisher] 计算了 {len(metrics)} 个指标")

        # 3. 各维度评分
        dim_scores = {}
        for dim in self.dimension_weights.keys():
            dim_scores[dim] = self.score_dimension(metrics.get(dim), dim)

        # 4. 加权总分
        total_score = sum(
            dim_scores[d] * (self.dimension_weights[d] / 100)
            for d in self.dimension_weights
        )
        total_score = round(total_score, 1)

        # 5. 等级
        if total_score >= 75:
            rating = "⭐⭐⭐ 强烈推荐"
        elif total_score >= 55:
            rating = "⭐⭐ 值得关注"
        elif total_score >= 35:
            rating = "⭐ 勉强合格"
        else:
            rating = "❌ 不符合Fisher标准"

        print(f"  [Fisher] 综合评分: {total_score} 分 - {rating}")

        return {
            'symbol': symbol,
            'total_score': total_score,
            'rating': rating,
            'dim_scores': dim_scores,
            'metrics': metrics,
            'data_success': True
        }

    def format_report(self, score_result: Dict) -> str:
        """
        生成Fisher分析报告

        Args:
            score_result: 评分结果

        Returns:
            格式化的报告文本
        """
        if not score_result.get('data_success'):
            return f"❌ {score_result.get('symbol')} 数据获取失败"

        dim_names = {
            # 成长性
            'revenue_cagr': '营收3年CAGR',
            'profit_cagr': '净利润3年CAGR',
            'non_recurring_adjust': '扣非净利润质量',
            # 盈利能力
            'roic': 'ROIC(投资回报率)',
            'net_margin': '净利率',
            'margin_stability': '毛利率稳定性',
            # 运营效率
            'inventory_turnover': '存货周转天数',
            'receivable_turnover': '应收账款天数',
            'sales_expense_ratio': '销售费用率',
            # 财务质量
            'cash_flow_quality': '经营现金流/净利润',
            'debt_ratio': '资产负债率',
            # 研发创新
            'rd_expense_ratio': '研发支出占比',
        }

        lines = [
            f"\n{'='*60}",
            f"🐟 Fisher定生成年股分析报告",
            f"{'='*60}",
            f"股票代码: {score_result.get('symbol')}",
            f"",
            f"🎯 综合评分: {score_result.get('total_score', 0)} 分",
            f"📋 评级: {score_result.get('rating', 'N/A')}",
            f"",
            f"{'─'*60}",
            f"{'指标':<22} {'原始值':>12} {'得分':>8} {'权重':>8}",
            f"{'─'*60}",
        ]

        for dim, weight in self.dimension_weights.items():
            name = dim_names.get(dim, dim)
            value = score_result.get('metrics', {}).get(dim)
            score = score_result.get('dim_scores', {}).get(dim, 0)

            if isinstance(value, float):
                # 判断指标类型添加单位
                if dim in ['inventory_turnover', 'receivable_turnover']:
                    value_str = f"{value:.1f}天"
                elif dim in ['revenue_cagr', 'profit_cagr', 'net_margin', 'cash_flow_quality',
                            'sales_expense_ratio', 'rd_expense_ratio', 'roic']:
                    value_str = f"{value:.2f}%"
                elif dim == 'margin_stability':
                    value_str = f"{value:.1f}"
                elif dim == 'debt_ratio':
                    value_str = f"{value:.2f}%"
                else:
                    value_str = f"{value:.2f}"
            else:
                value_str = str(value) if value is not None else "N/A"

            lines.append(f"{name:<22} {value_str:>12} {score:>7.1f} {weight:>7d}%")

        lines.append(f"{'─'*60}")

        # 添加维度汇总
        dim_categories = {
            '成长性': ['revenue_cagr', 'profit_cagr', 'non_recurring_adjust'],
            '盈利能力': ['roic', 'net_margin', 'margin_stability'],
            '运营效率': ['inventory_turnover', 'receivable_turnover', 'sales_expense_ratio'],
            '财务质量': ['cash_flow_quality', 'debt_ratio'],
            '研发创新': ['rd_expense_ratio'],
        }

        lines.append(f"\n📊 各维度得分汇总:")
        for category, dims in dim_categories.items():
            cat_weight = sum(self.dimension_weights[d] for d in dims)
            cat_score = sum(
                score_result.get('dim_scores', {}).get(d, 0) * (self.dimension_weights[d] / 100)
                for d in dims
            ) / (cat_weight / 100) * (cat_weight / 100) if cat_weight > 0 else 0
            # 简化计算
            total_dim_score = sum(score_result.get('dim_scores', {}).get(d, 0) for d in dims)
            cat_avg = total_dim_score / len(dims) if dims else 0
            lines.append(f"  {category}: {cat_avg:.1f}分 (权重{cat_weight}%)")

        lines.append(f"{'='*60}\n")

        return "\n".join(lines)


# ============ 快速筛选入口 ============

def fast_fisher_scan() -> pd.DataFrame:
    """
    快速筛选：直接通过问财语句初筛符合Fisher部分标准的股票

    Returns:
        DataFrame: 初步筛选结果
    """
    import pywencai

    print(f"\n{'='*60}")
    print(f"🔍 Fisher快速初筛（问财查询）")
    print(f"{'='*60}")

    # Fisher核心：持续成长 + 优质盈利
    queries = [
        # 方案1: 高ROE + 持续增长
        "净资产收益率大于15%，净利润同比增长大于10%，非st，非科创板",
        # 方案2: 优质现金流 + 高净利率
        "销售净利率大于15%，非st，净资产收益率大于12%",
        # 方案3: 成长性筛选
        "净利润同比增长大于20%，非st，净资产收益率大于10%",
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
    print("🧪 Fisher定生成年股选股器测试")
    print("=" * 60)

    selector = FisherSelector()

    # 测试单只股票
    test_symbols = ["600519", "000001", "300750"]  # 贵州茅台、平安银行、宁德时代

    for symbol in test_symbols:
        result = selector.score_stock(symbol)
        print(selector.format_report(result))


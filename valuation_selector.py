#!/usr/bin/env python3
"""
估值模块 - 基于巴菲特"合理价格"理念 + PEG指标
改进版：
1. 添加PEG指标（PE/Growth）- 成长股核心估值工具
2. 行业分类估值 - 不同行业使用不同合理PE区间
3. 更准确的数据清洗
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# 行业分类与合理估值区间
INDUSTRY_VALUATION = {
    # 行业: (合理PE下限, 合理PE上限, 合理PB上限, 行业名称)
    'tech': (25, 55, 8, '科技/成长'),
    'consumer': (20, 40, 6, '消费'),
    'finance': (8, 15, 1.5, '金融'),
    'healthcare': (25, 50, 6, '医疗健康'),
    'manufacturing': (12, 30, 3, '制造'),
    'energy': (10, 25, 2, '能源'),
    'realestate': (8, 15, 1.2, '房地产'),
    'utility': (10, 18, 1.5, '公用事业'),
    'default': (15, 45, 4, '综合'),
}


class ValuationSelector:
    """增强版估值选股器 - 支持PEG和行业分类"""

    def __init__(self):
        self.weights = {'pe_score': 20, 'peg_score': 25, 'pb_score': 15, 'hist_score': 20, 'industry_adj': 20}

    def _detect_industry(self, symbol: str) -> str:
        """根据股票代码前缀判断行业（简化版）"""
        code = str(symbol)

        # 创业板/科创板 → 科技成长
        if code.startswith('300') or code.startswith('688'):
            return 'tech'
        # 主板部分代码
        elif code.startswith('600') or code.startswith('000'):
            # 金融类
            if code in ['600036', '601398', '601939', '000001', '601166', '601288']:
                return 'finance'
            # 消费类
            elif code in ['600519', '000858', '000568', '600887']:
                return 'consumer'
            # 医疗
            elif code in ['600276', '300760', '300122']:
                return 'healthcare'
            else:
                return 'default'
        else:
            return 'default'

    def _get_yearly_profit_growth(self, symbol: str) -> Optional[float]:
        """计算近3年净利润复合增长率（用于PEG计算）"""
        try:
            import akshare as ak
            from datetime import datetime

            income_df = ak.stock_financial_report_sina(stock=symbol, symbol='利润表')
            if income_df is None or income_df.empty:
                return None

            income_df = income_df.sort_values('报告日', ascending=False)

            # 找到归母净利润列
            profit_cols = [c for c in income_df.columns
                          if '净利润' in str(c) and ('归属' in str(c) or '母公司' in str(c))]

            if not profit_cols:
                return None

            # 筛选年报数据（报告日以1231结尾）
            yearly_data = []
            for _, row in income_df.iterrows():
                report_date = str(row.get('报告日', ''))
                if report_date.endswith('1231'):
                    try:
                        year = int(report_date[:4])
                        current_year = datetime.now().year
                        # 只用已完成的年度数据
                        if year < current_year:
                            profit = row[profit_cols[0]]
                            if profit is not None and isinstance(profit, (int, float)) and profit > 0:
                                yearly_data.append((year, float(profit)))
                    except (ValueError, TypeError):
                        continue

            # 按年份排序，取最近3年
            yearly_data.sort(key=lambda x: x[0], reverse=True)

            if len(yearly_data) >= 3:
                profit_recent = yearly_data[0][1]  # 最新年度
                profit_oldest = yearly_data[-1][1]  # 3年前

                years = yearly_data[0][0] - yearly_data[-1][0]
                if years > 0 and profit_oldest > 0:
                    cagr = (profit_recent / profit_oldest) ** (1 / years) - 1
                    return round(cagr * 100, 2)

            return None

        except Exception as e:
            logger.debug(f"计算利润增长率失败: {e}")
            return None

    def get_valuation_data(self, symbol: str) -> Dict:
        """获取估值数据 - 增强版"""
        data = {
            'symbol': symbol,
            'price': None,
            'market_cap': None,
            'pe': None,
            'pb': None,
            'ps': None,
            'peg': None,           # 新增：PEG指标
            'profit_growth': None, # 新增：利润增长率
            'pe_percentile': None,
            'is_undervalued': False,
            'valuation_score': 0,
            'data_success': False,
            'industry': 'default', # 新增：行业分类
            'industry_name': '综合',
        }

        try:
            import akshare as ak

            print(f"  [Valuation] 正在获取 {symbol} 估值数据...")

            # 1. 检测行业
            industry = self._detect_industry(symbol)
            data['industry'] = industry
            data['industry_name'] = INDUSTRY_VALUATION[industry][3]
            print(f"  [Valuation] ✓ 行业分类: {data['industry_name']}")

            # 2. 获取基本信息
            stock_info = ak.stock_individual_info_em(symbol=symbol)
            if stock_info is not None and not stock_info.empty:
                info_dict = dict(zip(stock_info['item'], stock_info['value']))

                price = info_dict.get('最新')
                if price is not None:
                    data['price'] = float(price)

                cap = info_dict.get('总市值')
                if cap is not None:
                    data['market_cap'] = float(cap) / 1e8
                    print(f"  [Valuation] ✓ 价格={data['price']}, 市值={data['market_cap']:.0f}亿")

            # 3. 获取财务报表计算 PE/PB
            income_df = ak.stock_financial_report_sina(stock=symbol, symbol='利润表')
            balance_df = ak.stock_financial_report_sina(stock=symbol, symbol='资产负债表')

            if income_df is not None and balance_df is not None:
                income_df = income_df.sort_values('报告日', ascending=False)
                balance_df = balance_df.sort_values('报告日', ascending=False)

                net_profit_cols = [c for c in income_df.columns
                                  if '净利润' in str(c) and '归属' in str(c)]

                if net_profit_cols and data['market_cap']:
                    net_profit = float(income_df[net_profit_cols[0]].iloc[0])
                    if net_profit > 0:
                        data['pe'] = (data['market_cap'] * 1e8) / net_profit

                    equity_cols = [c for c in balance_df.columns
                                  if '归属于母公司股东权益' in str(c)]
                    if equity_cols:
                        equity = float(balance_df[equity_cols[0]].iloc[0])
                        if equity > 0:
                            data['pb'] = (data['market_cap'] * 1e8) / equity

                    print(f"  [Valuation] ✓ 计算PE={data.get('pe', 0):.2f}, PB={data.get('pb', 0):.2f}")

            # 4. 计算利润增长率和 PEG
            profit_growth = self._get_yearly_profit_growth(symbol)
            data['profit_growth'] = profit_growth

            if data.get('pe') and data['pe'] > 0 and profit_growth is not None and profit_growth > 0:
                data['peg'] = data['pe'] / abs(profit_growth)
                print(f"  [Valuation] ✓ 利润增长率={profit_growth:.1f}%, PEG={data['peg']:.2f}")
            else:
                # 如果无法计算真实增长率，尝试从GARP模块获取
                data['peg'] = None
                if profit_growth is not None:
                    print(f"  [Valuation] ⚠ 利润增长率={profit_growth:.1f}%（可能为负或PE无效）")

            # 5. 计算行业调整后的PE分位
            if data['pe'] and data['pe'] > 0:
                # 使用行业特定的估值区间
                pe_low, pe_high, pb_high, _ = INDUSTRY_VALUATION.get(industry, INDUSTRY_VALUATION['default'])

                if data['pe'] <= pe_low:
                    data['pe_percentile'] = 20  # 明显低估
                elif data['pe'] >= pe_high:
                    data['pe_percentile'] = 80  # 明显高估
                else:
                    # 线性插值
                    data['pe_percentile'] = round(20 + (data['pe'] - pe_low) / (pe_high - pe_low) * 60)

                # 综合判断是否低估（考虑PEG、PB）
                undervalue_score = 0

                # PE分位因子
                if data['pe_percentile'] <= 30:
                    undervalue_score += 40
                elif data['pe_percentile'] <= 50:
                    undervalue_score += 25
                elif data['pe_percentile'] <= 65:
                    undervalue_score += 10

                # PEG因子（非常重要！）
                peg = data.get('peg')
                if peg is not None:
                    if peg <= 0.8:
                        undervalue_score += 35  # PEG<1，非常低估
                    elif peg <= 1.0:
                        undervalue_score += 25  # PEG<1，低估
                    elif peg <= 1.5:
                        undervalue_score += 10  # PEG<1.5，合理
                    # PEG>1.5 不加分

                # PB因子
                pb = data.get('pb')
                if pb is not None and pb > 0:
                    if pb <= pb_high * 0.5:
                        undervalue_score += 25  # PB很低
                    elif pb <= pb_high * 0.8:
                        undervalue_score += 15  # PB偏低
                    elif pb <= pb_high:
                        undervalue_score += 5   # PB合理

                # 综合判断：得分>=50才算低估
                data['is_undervalued'] = undervalue_score >= 50

                print(f"  [Valuation] ✓ PE分位={data['pe_percentile']}%, "
                      f"PEG={data.get('peg', 'N/A')}, "
                      f"低估={data['is_undervalued']}")

            # 6. 计算估值评分
            data['valuation_score'] = self._calculate_valuation_score(data)
            if data['valuation_score'] > 0:
                print(f"  [Valuation] ✅ 估值评分: {data['valuation_score']:.1f}/100")
            data['data_success'] = True

        except Exception as e:
            logger.warning(f"  [Valuation] 获取估值数据失败: {e}")
        return data

    def _calculate_valuation_score(self, data: Dict) -> float:
        """计算估值评分 - 增强版（包含PEG）"""
        score = 0.0

        # 1. PE分位评分 (20分满分)
        pe_pct = data.get('pe_percentile')
        if pe_pct is not None:
            if pe_pct <= 25:
                score += 20
            elif pe_pct <= 40:
                score += 16
            elif pe_pct <= 55:
                score += 12
            elif pe_pct <= 70:
                score += 7
            else:
                score += 3

        # 2. PEG评分 (25分满分) - 成长股核心指标！
        peg = data.get('peg')
        if peg is not None:
            if peg <= 0.5:
                score += 25  # 极度低估
            elif peg <= 0.8:
                score += 22  # 非常低估
            elif peg <= 1.0:
                score += 18  # 低估（彼得·林奇标准）
            elif peg <= 1.3:
                score += 12  # 合理
            elif peg <= 1.8:
                score += 6   # 略高
            elif peg <= 2.5:
                score += 2   # 偏高
            # PEG>2.5 不加分
        else:
            # 无法计算PEG时，给一个基础分
            score += 5

        # 3. PE绝对值评分 (15分满分)
        pe = data.get('pe')
        if pe is not None and pe > 0:
            if pe <= 15:
                score += 15
            elif pe <= 25:
                score += 13
            elif pe <= 35:
                score += 10
            elif pe <= 50:
                score += 6
            elif pe <= 70:
                score += 3
            else:
                score += 1

        # 4. PB评分 (15分满分)
        pb = data.get('pb')
        industry = data.get('industry', 'default')
        _, _, pb_high, _ = INDUSTRY_VALUATION.get(industry, INDUSTRY_VALUATION['default'])

        if pb is not None and pb > 0:
            # 根据行业调整PB评分标准
            pb_ratio = pb / pb_high if pb_high > 0 else pb
            if pb_ratio <= 0.5:
                score += 15
            elif pb_ratio <= 0.8:
                score += 12
            elif pb_ratio <= 1.0:
                score += 8
            elif pb_ratio <= 1.5:
                score += 4
            else:
                score += 1

        # 5. 低估加分 + 行业调整 (25分满分)
        if data.get('is_undervalued'):
            score += 15

        # 利润增长率加分（成长性验证）
        growth = data.get('profit_growth')
        if growth is not None:
            if growth > 30:
                score += 10  # 高成长
            elif growth > 20:
                score += 7   # 中高成长
            elif growth > 10:
                score += 4   # 稳定成长
            # 增长率低于10%不额外加分

        return min(100, score)

    def score_factor(self, data: Dict) -> float:
        if not data.get('data_success'):
            return 0.0
        return data.get('valuation_score', 0)

    def get_recommendation(self, data: Dict) -> str:
        score = data.get('valuation_score', 0)
        peg = data.get('peg')

        # 结合PEG给出更精准的建议
        if peg is not None and peg <= 1.0:
            peg_hint = " (PEG<1)"
        elif peg is not None and peg <= 1.5:
            peg_hint = " (PEG合理)"
        else:
            peg_hint = ""

        if score >= 75:
            return f"强烈推荐{peg_hint} - 严重低估"
        elif score >= 60:
            return f"推荐{peg_hint} - 被低估"
        elif score >= 45:
            return "中性 - 合理估值"
        elif score >= 30:
            return "谨慎 - 估值偏高"
        return "不推荐 - 估值过高"

    def get_detailed_analysis(self, data: Dict) -> str:
        """生成详细的估值分析文本"""
        lines = []
        lines.append(f"### 📊 估值分析详情")
        lines.append(f"- **行业**: {data.get('industry_name', '未知')}")
        lines.append(f"- **市盈率(PE)**: {data.get('pe', 'N/A')}")
        lines.append(f"- **市净率(PB)**: {data.get('pb', 'N/A')}")
        lines.append(f"- **PEG指标**: {data.get('peg', 'N/A')}")
        lines.append(f"- **利润增长率**: {data.get('profit_growth', 'N/A')}%")
        lines.append(f"- **PE历史分位**: {data.get('pe_percentile', 'N/A')}%")
        lines.append(f"- **是否低估**: {'✅ 是' if data.get('is_undervalued') else '❌ 否'}")
        lines.append(f"- **估值评分**: {data.get('valuation_score', 0)}/100")

        # PEG解读
        peg = data.get('peg')
        if peg is not None:
            if peg <= 0.8:
                lines.append(f"- **PEG解读**: 🟢 PEG={peg:.2f}<1，股价被显著低估，具有很高的安全边际")
            elif peg <= 1.0:
                lines.append(f"- **PEG解读**: 🟢 PEG={peg:.2f}≈1，估值合理，符合彼得·林奇选股标准")
            elif peg <= 1.5:
                lines.append(f"- **PEG解读**: 🟡 PEG={peg:.2f}>1，估值略偏高但可接受")
            elif peg <= 2.0:
                lines.append(f"- **PEG解读**: 🔴 PEG={peg:.2f}>1.5，估值偏高，需谨慎")
            else:
                lines.append(f"- **PEG解读**: 🔴 PEG={peg:.2f}>2，明显高估，建议回避")

        return "\n".join(lines)


if __name__ == '__main__':
    v = ValuationSelector()

    # 测试多只股票
    test_codes = ['300750', '600519', '000858', '300122']
    for code in test_codes:
        d = v.get_valuation_data(code)
        print(f"\n{'='*50}")
        print(f"{code}:")
        print(f"  PE={d.get('pe', 'N/A')}, PB={d.get('pb', 'N/A')}, PEG={d.get('peg', 'N/A')}")
        print(f"  行业={d.get('industry_name')}, 低估={d.get('is_undervalued')}")
        print(f"  评分={d.get('valuation_score')}")
        print(v.get_recommendation(d))


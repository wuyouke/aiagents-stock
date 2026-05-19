#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长股选股主引擎（四引擎版）
Fisher定性 + GARP量化 + 估值分析 + AI智能解读

理论框架：
  - Fisher（费雪）: 《怎样选择成长股》- 定性成长股选股
  - GARP: Growth at a Reasonable Price - 量化因子选股
  - PEG估值: 彼得·林奇核心工具
  - Ollama AI: 本地大模型智能分析

Fisher 11维度:
  成长性(30分): 营收CAGR, 净利润CAGR, 扣非净利润质量
  盈利能力(25分): ROIC, 净利率, 毛利率稳定性
  运营效率(20分): 存货周转, 应收周转, 销售费用率
  财务质量(15分): 现金流质量, 资产负债率
  研发创新(10分): 研发支出占比

GARP 8因子:
  盈利预测调整, 盈余惊喜, 销售额增长, 营业利润率,
  自由现金流, 盈利增长, 盈利动量, ROE
"""

import io
import logging
import sys
import warnings
from datetime import datetime
from typing import Dict, List, Callable

import pandas as pd

from fisher_selector import FisherSelector
from garp_selector import GARPSelector
from valuation_selector import ValuationSelector

# 设置stdout编码（仅在命令行环境）
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
    except:
        pass

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class GrowthStockEngine:
    """
    成长股选股双引擎（增强版）

    整合Fisher定生成年股选股器、GARP量化因子选股器和估值模块，
    提供统一的选股、评分、排名功能。

    新增特性：
    - 动态权重调整：根据股票类型自动调整各引擎权重
    - 行业适配：不同行业使用不同的估值标准
    - PEG集成：将PEG指标纳入综合评估
    - AI分析：集成Ollama本地大模型智能解读
    """

    # Ollama 配置
    OLLAMA_ENABLED = True  # 是否启用AI分析
    OLLAMA_BASE_URL = "http://localhost:11434"
    OLLAMA_MODEL = "gpt-oss:20b"  # 默认模型

    # 默认权重配置
    DEFAULT_WEIGHTS = {
        'fisher': 0.40,   # 费雪定性分析
        'garp': 0.35,     # GARP量化因子
        'valuation': 0.25  # 估值分析（含PEG）
    }

    # 不同股票类型的权重配置
    STOCK_TYPE_WEIGHTS = {
        'growth': {       # 高成长股（创业板/科创板）
            'fisher': 0.30,
            'garp': 0.45,  # 更重视动量指标
            'valuation': 0.25
        },
        'value': {        # 价值股（低PE/PB）
            'fisher': 0.45,  # 更重视质量
            'garp': 0.25,
            'valuation': 0.30  # 更重视安全边际
        },
        'balanced': {     # 均衡型
            'fisher': 0.40,
            'garp': 0.35,
            'valuation': 0.25
        }
    }

    def __init__(self, enable_ai: bool = True):
        self.fisher = FisherSelector()
        self.garp = GARPSelector()
        self.valuation = ValuationSelector()

        # 初始化 AI 分析器（可选）
        self.ai_analyst = None
        if enable_ai and self.OLLAMA_ENABLED:
            try:
                from ollama_analyst import OllamaAnalyst
                self.ai_analyst = OllamaAnalyst(
                    base_url=self.OLLAMA_BASE_URL,
                    model=self.OLLAMA_MODEL
                )
                # 检查服务是否可用
                if not self.ai_analyst.check_ollama_available():
                    print("  ⚠️ Ollama 服务不可用，AI分析功能已禁用")
                    self.ai_analyst = None
                else:
                    print(f"  ✅ AI分析模块已启用 (模型: {self.OLLAMA_MODEL})")
            except ImportError:
                print("  ⚠️ ollama_analyst 模块未找到")
            except Exception as e:
                print(f"  ⚠️ AI分析初始化失败: {e}")

    def _detect_stock_type(self, symbol: str, valuation_data: Dict) -> str:
        """
        检测股票类型（成长型/价值型/均衡型）

        基于以下因素判断：
        1. 股票代码前缀（创业板/科创板→成长型）
        2. PE水平（低PE→价值型）
        3. 利润增长率（高增长→成长型）
        """
        code = str(symbol)

        # 基础判断：代码前缀
        if code.startswith('300') or code.startswith('688'):
            base_type = 'growth'
        elif code.startswith('600'):
            base_type = 'balanced'
        else:
            base_type = 'balanced'

        # 根据估值数据调整
        pe = valuation_data.get('pe')
        growth = valuation_data.get('profit_growth')

        if pe is not None and growth is not None:
            # 高成长 + 合理PE → 成长型
            if growth > 20 and pe > 25:
                return 'growth'
            # 低PE + 低增长 → 价值型
            elif pe < 20 and growth < 10:
                return 'value'

        return base_type

    def _get_dynamic_weights(self, symbol: str, valuation_data: Dict) -> Dict[str, float]:
        """获取动态调整后的权重"""
        stock_type = self._detect_stock_type(symbol, valuation_data)
        weights = self.STOCK_TYPE_WEIGHTS.get(stock_type, self.DEFAULT_WEIGHTS).copy()

        print(f"  [Engine] 📊 检测到股票类型: {stock_type}")
        print(f"  [Engine] ⚖️ 动态权重: Fisher={weights['fisher']:.0%}, "
              f"GARP={weights['garp']:.0%}, Valuation={weights['valuation']:.0%}")

        return weights

    def get_stock_name(self, symbol: str) -> str:
        """获取股票名称"""
        try:
            import akshare as ak
            info = ak.stock_individual_info_em(symbol=symbol)
            if info is not None and not info.empty:
                name_row = info[info['item'] == '股票简称']
                if not name_row.empty:
                    return name_row.iloc[0]['value']
            return '未知'
        except Exception as e:
            logger.warning(f"  获取股票名称失败 {symbol}: {e}")
            return '未知'

    def analyze_stock(self, symbol: str, name: str = None) -> Dict:
        """
        对单只股票进行双引擎分析

        Args:
            symbol: 股票代码
            name: 股票名称（可选，自动获取）

        Returns:
            {
                'symbol': str,
                'name': str,
                'fisher': {score, rating, report, dim_scores, metrics, data_success},
                'garp': {score, rating, report, factor_scores, factor_values, data_success},
                'combined_score': float,
                'final_recommendation': str
            }
        """
        print(f"\n{'#'*70}")
        print(f"## 🚀 成长股双引擎分析: {symbol}")
        print(f"{'#'*70}")

        # 自动获取股票名称
        if name is None:
            name = self.get_stock_name(symbol)
            print(f"  股票名称: {name}")

        # ---------- 并行运行两个引擎 ----------

        # 1. Fisher 定性分析
        print(f"\n{'='*70}")
        print(f"🐟 引擎一: Fisher 定性成长股分析")
        print(f"{'='*70}")
        fisher_result = self.fisher.score_stock(symbol)

        # 2. GARP 量化分析
        print(f"\n{'='*70}")
        print(f"📈 引擎二: GARP 量化因子分析")
        print(f"{'='*70}")
        factor_data = self.garp.get_factor_data(symbol)
        garp_result = self.garp.score_stock(factor_data)

        # 3. 估值分析（安全边际）
        print(f"\n{'='*70}")
        print(f"💰 引擎三: 估值与安全边际分析")
        print(f"{'='*70}")
        valuation_data = self.valuation.get_valuation_data(symbol)
        valuation_score = self.valuation.score_factor(valuation_data)

        # ---------- 综合评分（动态权重） ----------
        fisher_score = fisher_result.get('total_score', 0) if fisher_result.get('data_success') else 0
        garp_score = garp_result.get('total_score', 0) if garp_result.get('data_success') else 0

        # 获取动态权重
        dynamic_weights = self._get_dynamic_weights(symbol, valuation_data)

        # 安全处理估值数据为None的情况（估值获取失败时使用默认值）
        pe_percentile = valuation_data.get('pe_percentile')
        if pe_percentile is None:
            pe_percentile = 50  # 默认中间值，不触发惩罚

        # 安全边际筛选：根据PE分位调整
        safety_penalty = 0
        if pe_percentile > 75:
            safety_penalty = 8   # PE分位>75%扣8分
        elif pe_percentile > 60:
            safety_penalty = 4   # PE分位>60%扣4分

        # PEG调整：PEG过高时额外扣分
        peg = valuation_data.get('peg')
        peg_penalty = 0
        if peg is not None:
            if peg > 2.5:
                peg_penalty = 6   # PEG>2.5明显高估
            elif peg > 2.0:
                peg_penalty = 3   # PEG>2偏高

        # 使用动态权重计算综合评分
        combined_score = round(
            fisher_score * dynamic_weights['fisher'] +
            garp_score * dynamic_weights['garp'] +
            valuation_score * dynamic_weights['valuation'],
            1
        )

        # 扣除安全边际和PEG惩罚
        combined_score = max(0, combined_score - safety_penalty - peg_penalty)

        # ---------- 最终推荐（改进版：更合理的推荐逻辑）----------
        is_undervalued = valuation_data.get('is_undervalued', False)
        pe = valuation_data.get('pe', None)
        valuation_score_result = valuation_data.get('valuation_score', 0)

        # 安全处理pe为None的情况
        pe_valid = pe is not None and isinstance(pe, (int, float)) and pe > 0

        # 综合评分 + 估值状态 → 推荐等级
        if combined_score >= 70 and is_undervalued:
            recommendation = "⭐⭐⭐ 强烈推荐买入"
            action = "✅ 质量优秀且估值偏低，建议建仓"
        elif combined_score >= 65 and (is_undervalued or (pe_valid and pe < 35)):
            recommendation = "⭐⭐⭐ 推荐"
            action = "👍 质量良好且估值合理，可以关注"
        elif combined_score >= 55:
            recommendation = "⭐⭐ 值得关注"
            action = "📋 基本面尚可，建议等待更好买点"
        elif combined_score >= 40:
            recommendation = "⭐ 观望"
            action = "⚠️ 部分指标达标，需进一步观察"
        else:
            recommendation = "❌ 暂不推荐"
            action = "❌ 综合评分较低，建议寻找其他标的"

        # ---------- 生成综合报告 ----------
        fisher_report = self.fisher.format_report(fisher_result)
        garp_report = self.garp.format_report(garp_result)

        # ---------- AI 智能分析（引擎四）- 独立分析原始财报 ----------
        ai_analysis = None
        if self.ai_analyst is not None:
            print(f"\n{'='*70}")
            print(f"🤖 引擎四: Ollama AI 智能分析（独立财报解读）")
            print(f"{'='*70}")
            print(f"  📌 AI 将直接获取并分析原始财务报表数据")
            print(f"  📌 不依赖三引擎的计算结果，给出独立第四方观点")

            try:
                # 直接传股票代码和名称，AI自行获取原始财报数据进行分析
                ai_result = self.ai_analyst.analyze_stock(symbol=symbol, name=name)
                ai_analysis = ai_result
                if ai_analysis.get('success'):
                    print(f"  ✅ AI 分析完成 (模型: {ai_analysis.get('model', 'N/A')})")
                    data_source = ai_analysis.get('data_source', 'unknown')
                    raw_summary = ai_analysis.get('raw_data_summary', {})
                    print(f"  📊 数据来源: {data_source}")
                    print(f"  📊 财报数据: 利润表{raw_summary.get('income_periods',0)}期, "
                          f"资产负债表{raw_summary.get('balance_periods',0)}期, "
                          f"现金流量表{raw_summary.get('cashflow_periods',0)}期")
                else:
                    print(f"  ⚠️ AI 分析失败，使用备用分析")
            except Exception as e:
                print(f"  ❌ AI 分析异常: {e}")
                ai_analysis = None

        # ---------- 构建结果 ----------
        result = {
            'symbol': symbol,
            'name': name,
            'fisher': {
                'score': fisher_score,
                'rating': fisher_result.get('rating', 'N/A'),
                'report': fisher_report,
                'dim_scores': fisher_result.get('dim_scores', {}),
                'metrics': fisher_result.get('metrics', {}),
                'data_success': fisher_result.get('data_success', False)
            },
            'garp': {
                'score': garp_score,
                'rating': garp_result.get('rating', 'N/A'),
                'report': garp_report,
                'factor_scores': garp_result.get('factor_scores', {}),
                'factor_values': garp_result.get('factor_values', {}),
                'data_success': garp_result.get('data_success', False)
            },
            'valuation': {
                'score': valuation_score,
                'pe': valuation_data.get('pe'),
                'pb': valuation_data.get('pb'),
                'peg': valuation_data.get('peg'),           # 新增：PEG
                'profit_growth': valuation_data.get('profit_growth'),  # 新增：利润增长率
                'pe_percentile': valuation_data.get('pe_percentile'),
                'is_undervalued': valuation_data.get('is_undervalued'),
                'industry': valuation_data.get('industry'),  # 新增：行业
                'industry_name': valuation_data.get('industry_name'),
                'recommendation': self.valuation.get_recommendation(valuation_data),
                'data_success': valuation_data.get('data_success', False),
                'detailed_analysis': self.valuation.get_detailed_analysis(valuation_data)  # 新增：详细分析
            },
            'stock_type': self._detect_stock_type(symbol, valuation_data),  # 新增：股票类型
            'weights_used': dynamic_weights,  # 新增：使用的权重
            'ai_analysis': ai_analysis,  # 新增：AI分析结果
            'combined_score': combined_score,
            'recommendation': recommendation,
            'action': action,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 打印综合摘要
        print(f"\n{'='*70}")
        print(f"📊 双引擎综合分析报告")
        print(f"{'='*70}")
        print(f"  股票代码: {symbol}")
        print(f"  股票名称: {name}")
        print(f"")
        print(f"  🐟 Fisher评分: {fisher_score} 分 ({fisher_result.get('rating', 'N/A')})")
        print(f"  📈 GARP评分:   {garp_score} 分 ({garp_result.get('rating', 'N/A')})")
        print(f"")
        print(f"  🎯 综合评分:   {combined_score} 分")
        print(f"  📋 最终推荐:   {recommendation}")
        print(f"  💡 操作建议:   {action}")
        print(f"{'='*70}")

        return result

    def batch_analyze(self, symbols: List[str],
                      progress_callback: Callable[[int, int, str], None] = None) -> pd.DataFrame:
        """
        批量分析多只股票

        Args:
            symbols: 股票代码列表
            progress_callback: 进度回调函数 (current, total, message)

        Returns:
            排序后的评分结果DataFrame
        """
        print(f"\n{'#'*70}")
        print(f"## 📊 批量成长股分析")
        print(f"{'#'*70}")
        print(f"  待分析股票数量: {len(symbols)}")
        print(f"{'='*70}")

        results = []
        total = len(symbols)

        for i, symbol in enumerate(symbols):
            msg = f"分析 {symbol} ({i+1}/{total})"
            print(f"\n  [{i+1}/{total}] {msg}")
            if progress_callback:
                progress_callback(i + 1, total, msg)

            try:
                # 完整分析
                analysis = self.analyze_stock(symbol)

                results.append({
                    'symbol': symbol,
                    'name': analysis['name'],
                    'fisher_score': analysis['fisher']['score'],
                    'garp_score': analysis['garp']['score'],
                    'combined_score': analysis['combined_score'],
                    'recommendation': analysis['recommendation'],
                    'fisher_success': analysis['fisher']['data_success'],
                    'garp_success': analysis['garp']['data_success'],
                    # 各维度得分
                    'revenue_cagr': analysis['fisher']['metrics'].get('revenue_cagr'),
                    'profit_cagr': analysis['fisher']['metrics'].get('profit_cagr'),
                    'roic': analysis['fisher']['metrics'].get('roic'),
                    'net_margin': analysis['fisher']['metrics'].get('net_margin'),
                    'cash_flow_quality': analysis['fisher']['metrics'].get('cash_flow_quality'),
                    'roe': analysis['garp']['factor_values'].get('roe'),
                    'profit_growth': analysis['garp']['factor_values'].get('profit_growth'),
                    'earnings_momentum': analysis['garp']['factor_values'].get('earnings_momentum'),
                })

            except Exception as e:
                logger.warning(f"  ❌ {symbol} 分析失败: {e}")
                results.append({
                    'symbol': symbol,
                    'name': '未知',
                    'fisher_score': 0,
                    'garp_score': 0,
                    'combined_score': 0,
                    'recommendation': '❌ 分析失败',
                    'fisher_success': False,
                    'garp_success': False,
                    'revenue_cagr': None,
                    'profit_cagr': None,
                    'roic': None,
                    'net_margin': None,
                    'cash_flow_quality': None,
                    'roe': None,
                    'profit_growth': None,
                    'earnings_momentum': None,
                })

        # 转换为DataFrame并排序
        df = pd.DataFrame(results)
        if not df.empty:
            df = df.sort_values('combined_score', ascending=False).reset_index(drop=True)
            # 添加排名
            df.insert(0, 'rank', range(1, len(df) + 1))

        print(f"\n{'='*70}")
        print(f"📊 批量分析完成，共 {len(df)} 只股票")
        print(f"{'='*70}")

        # 打印排名摘要
        if not df.empty:
            print(f"\n{'排名':<5} {'代码':<8} {'名称':<10} {'Fisher':>8} {'GARP':>8} {'综合':>8} {'推荐'}")
            print(f"{'─'*70}")
            for _, row in df.head(10).iterrows():
                print(f"{row['rank']:<5} {row['symbol']:<8} {row['name']:<10} "
                      f"{row['fisher_score']:>8.1f} {row['garp_score']:>8.1f} "
                      f"{row['combined_score']:>8.1f} {row['recommendation'][:10]}")

        return df

    def quick_scan(self, top_n: int = 20) -> pd.DataFrame:
        """
        快速扫描：通过问财初筛后深度分析

        Args:
            top_n: 返回前N只股票

        Returns:
            深度分析后的排名DataFrame
        """
        print(f"\n{'#'*70}")
        print(f"## 🔍 成长股快速扫描")
        print(f"{'#'*70}")

        # 尝试从问财获取初筛结果
        raw_results = []

        # 方法1: Fisher快速筛选
        try:
            from fisher_selector import fast_fisher_scan
            fisher_scan = fast_fisher_scan()
            if fisher_scan is not None and not fisher_scan.empty:
                for _, row in fisher_scan.iterrows():
                    code = row.get('股票代码', row.get('代码', ''))
                    if isinstance(code, str) and '.' in code:
                        code = code.split('.')[0]
                    name = row.get('股票简称', row.get('名称', '未知'))
                    raw_results.append({'code': str(code), 'name': name, 'source': 'fisher'})
                print(f"  ✅ Fisher初筛获取 {len(fisher_scan)} 只股票")
        except Exception as e:
            print(f"  ⚠️ Fisher初筛失败: {e}")

        # 方法2: GARP快速筛选
        try:
            from garp_selector import fast_scan_garp_stocks
            garp_scan = fast_scan_garp_stocks()
            if garp_scan is not None and not garp_scan.empty:
                for _, row in garp_scan.iterrows():
                    code = row.get('股票代码', row.get('代码', ''))
                    if isinstance(code, str) and '.' in code:
                        code = code.split('.')[0]
                    name = row.get('股票简称', row.get('名称', '未知'))
                    # 避免重复
                    if not any(r['code'] == code for r in raw_results):
                        raw_results.append({'code': str(code), 'name': name, 'source': 'garp'})
                print(f"  ✅ GARP初筛获取 {len(garp_scan)} 只股票")
        except Exception as e:
            print(f"  ⚠️ GARP初筛失败: {e}")

        # 去重并限制数量
        seen = set()
        unique_results = []
        for r in raw_results:
            if r['code'] not in seen:
                seen.add(r['code'])
                unique_results.append(r)

        unique_results = unique_results[:top_n * 2]  # 预留一些被过滤的

        print(f"  📊 初筛合并去重后: {len(unique_results)} 只股票")
        print(f"  🔬 即将进行深度分析...")

        if not unique_results:
            print("  ❌ 无法获取初筛结果，请检查网络和问财接口")
            return pd.DataFrame()

        # 深度分析
        symbols = [r['code'] for r in unique_results]
        return self.batch_analyze(symbols)

    def compare_stocks(self, symbols: List[str]) -> pd.DataFrame:
        """
        对比分析多只股票

        Args:
            symbols: 股票代码列表

        Returns:
            对比分析DataFrame
        """
        print(f"\n{'#'*70}")
        print(f"## ⚖️ 股票对比分析")
        print(f"{'#'*70}")
        print(f"  对比股票数量: {len(symbols)}")
        print(f"{'='*70}")

        # 批量分析
        df = self.batch_analyze(symbols)

        # 添加对比视图
        if not df.empty:
            print(f"\n{'='*70}")
            print(f"📊 关键指标对比")
            print(f"{'='*70}")

            compare_cols = ['revenue_cagr', 'profit_cagr', 'roic', 'net_margin',
                          'cash_flow_quality', 'roe', 'profit_growth', 'earnings_momentum']

            print(f"\n{'指标':<20}", end='')
            for _, row in df.iterrows():
                print(f"{row['symbol'][:6]:>10}", end='')
            print()
            print(f"{'─'*70}")

            col_names = {
                'revenue_cagr': '营收CAGR%',
                'profit_cagr': '净利CAGR%',
                'roic': 'ROIC%',
                'net_margin': '净利率%',
                'cash_flow_quality': '现金流%',
                'roe': 'ROE%',
                'profit_growth': '盈利增长%',
                'earnings_momentum': '盈利动量'
            }

            for col in compare_cols:
                print(f"{col_names.get(col, col):<20}", end='')
                for _, row in df.iterrows():
                    val = row.get(col)
                    if val is not None and isinstance(val, (int, float)):
                        print(f"{val:>10.1f}", end='')
                    else:
                        print(f"{'N/A':>10}", end='')
                print()

        return df

    def format_full_report(self, result: Dict) -> str:
        """
        生成完整的分析报告（用于PDF导出等）

        Args:
            result: analyze_stock() 返回的结果

        Returns:
            完整报告文本
        """
        lines = [
            f"{'#'*70}",
            f"# 成长股双引擎分析报告",
            f"# 生成时间: {result.get('timestamp', 'N/A')}",
            f"{'#'*70}",
            f"",
            f"## 基本信息",
            f"- 股票代码: {result.get('symbol')}",
            f"- 股票名称: {result.get('name')}",
            f"",
            f"## 综合评分",
            f"- Fisher评分: {result['fisher']['score']} 分 ({result['fisher']['rating']})",
            f"- GARP评分:   {result['garp']['score']} 分 ({result['garp']['rating']})",
            f"- 综合评分:   {result.get('combined_score')} 分",
            f"- 最终推荐:   {result.get('recommendation')}",
            f"- 操作建议:   {result.get('action')}",
            f"",
        ]

        # Fisher详细报告
        lines.append(f"{'='*70}")
        lines.append(f"# Fisher定生成年股分析报告")
        lines.append(f"{'='*70}")
        lines.append(result['fisher']['report'])

        # GARP详细报告
        lines.append(f"{'='*70}")
        lines.append(f"# GARP量化因子分析报告")
        lines.append(f"{'='*70}")
        lines.append(result['garp']['report'])

        lines.append(f"\n{'='*70}")
        lines.append(f"# 报告结束")
        lines.append(f"{'='*70}")

        return "\n".join(lines)


# ============ 主测试入口 ============

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 成长股双引擎选股系统测试")
    print("=" * 70)

    engine = GrowthStockEngine()

    # 选项1: 测试单只股票
    # result = engine.analyze_stock("600519")  # 贵州茅台

    # 选项2: 批量分析指定股票
    test_symbols = ["600519", "000001", "300750", "002594", "000858"]
    print(f"\n批量分析: {test_symbols}")
    df = engine.batch_analyze(test_symbols)

    # 选项3: 快速扫描（需要问财）
    # print("\n尝试快速扫描...")
    # df = engine.quick_scan(top_n=10)

    print("\n✅ 测试完成")


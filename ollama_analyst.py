#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama 本地大模型分析模块（改进版）
功能：
1. 直接获取公司原始财务数据
2. 按照费雪15原则 + GARP 8因子 + 估值策略进行独立分析
3. 不依赖引擎计算的指标，AI自行解读原始数据
4. 给出独立的投资建议和风险评估
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List

import requests

logger = logging.getLogger(__name__)


class OllamaAnalyst:
    """
    Ollama 本地AI分析师 - 直接分析原始财报数据

    核心改进：
    - AI 直接读取利润表、资产负债表、现金流量表原始数据
    - AI 自行计算和判断，不依赖预计算的指标
    - 给出独立于三引擎的第四方观点
    """

    def __init__(self,
                 base_url: str = "http://localhost:11434",
                 model: str = "gpt-oss:20b",
                 timeout: int = 120):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout

        # 系统提示词 - 专业金融分析师角色
        self.system_prompt = """你是一位拥有20年经验的资深证券分析师，精通以下投资分析框架：

## 你的核心分析框架

### 一、费雪（Philip Fisher）成长股选股 15条原则（定性）
1. **产品/服务市场潜力** - 是否有巨大的市场空间？
2. **研发投入** - 公司是否持续创新？
3. **销售组织** - 销售效率如何？
4. **利润率** - 是否有持续的高利润率？
5. **诚信管理** - 管理层是否值得信任？
6. **财务稳健** - 财务状况是否健康？
7. **防御特性** - 是否有护城河？
8. **劳资关系** - 员工关系是否良好？
9. **高管执行** - 管理层执行力如何？
10. **成本控制** - 成本控制能力？
11. **行业前景** - 所处行业是否有前景？
12. **现金流** - 现金流是否充裕？
13. **资本配置** - 资本使用是否高效？
14. ** insider交易** - 内部人买卖情况？
15. **长期展望** - 未来3-5年发展预期？

### 二、GARP量化因子分析（8个核心指标）
1. **盈利预测调整** - 分析师是否上调盈利预测？
2. **盈余惊喜** - 是否经常超预期？
3. **销售额增长** - 收入增长趋势
4. **营业利润率** - 盈利能力
5. **自由现金流** - FCF/Revenue 或 FCF/EV
6. **盈利增长** - 净利润增长率
7. **盈利动量** - 盈利加速度
8. **ROE (权益报酬率)** - 股东回报率

### 三、估值分析（彼得·林奇标准）
- **PEG**: PE/Growth < 1 为理想买入点
- **PE**: 与历史水平和同业比较
- **PB**: 净资产溢价合理性
- **PS**: 对于高成长公司的适用性

## 分析要求

请根据提供的**原始财务数据**，进行以下分析：

1. **数据解读**：直接从报表中提取关键数字，说明其含义
2. **趋势分析**：对比近3-5年数据，判断趋势
3. **横向比较**：与行业平均水平对比（根据你的知识）
4. **风险识别**：明确指出主要风险因素
5. **投资建议**：给出明确的操作建议（强烈买入/买入/持有/观望/卖出）

## 输出格式要求
- 使用中文
- 使用 Markdown 格式
- 数据要具体，不要笼统
- 观点要有依据
- 风险提示要明确"""

    def check_ollama_available(self) -> bool:
        """检查 Ollama 服务是否可用"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                logger.info(f"✅ Ollama 可用，已安装模型: {model_names}")

                if any(self.model in name for name in model_names):
                    return True
                else:
                    logger.warning(f"⚠️ 模型 {self.model} 未找到")
                    if model_names:
                        self.model = model_names[0]
                        return True
                    return False
            return False
        except Exception as e:
            logger.warning(f"❌ Ollama 服务不可用: {e}")
            return False

    def _call_ollama(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """调用 Ollama API"""
        try:
            url = f"{self.base_url}/api/generate"

            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt or self.system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 4096,  # 更长的输出
                }
            }

            logger.info(f"🤖 正在调用 Ollama 模型: {self.model}")
            response = requests.post(url, json=payload, timeout=self.timeout)

            if response.status_code == 200:
                result = response.json()
                text = result.get('response', '')
                text = text.strip()
                if text:
                    logger.info(f"✅ AI 分析完成，生成 {len(text)} 字符")
                    return text
                else:
                    logger.warning("⚠️ 模型返回空内容")
                    return None
            else:
                logger.error(f"❌ API 请求失败: HTTP {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"❌ 请求超时 ({self.timeout}秒)")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("❌ 无法连接到 Ollama 服务")
            return None
        except Exception as e:
            logger.error(f"❌ 调用 Ollama 失败: {e}")
            return None

    def _fetch_raw_financial_data(self, symbol: str) -> Dict:
        """
        获取原始财务数据（不经过任何预处理）

        Returns:
            包含原始财务数据的字典
        """
        data = {
            'symbol': symbol,
            'success': False,
            'income_statement': None,   # 利润表原始数据
            'balance_sheet': None,      # 资产负债表原始数据
            'cash_flow': None,          # 现金流量表原始数据
            'stock_info': None,         # 股票基本信息
            'error': None
        }

        try:
            import akshare as ak

            print(f"  [AI] 正在获取 {symbol} 原始财务数据...")

            # 1. 股票基本信息
            stock_info = ak.stock_individual_info_em(symbol=symbol)
            if stock_info is not None and not stock_info.empty:
                info_dict = dict(zip(stock_info['item'], stock_info['value']))
                data['stock_info'] = info_dict
                print(f"  [AI] ✓ 获取到股票基本信息")

            # 2. 利润表（最近10期）
            income_df = ak.stock_financial_report_sina(stock=symbol, symbol='利润表')
            if income_df is not None and not income_df.empty:
                income_df = income_df.sort_values('报告日', ascending=False).head(12)
                # 转换为可读格式
                data['income_statement'] = income_df.to_dict(orient='records')
                print(f"  [AI] ✓ 利润表 {len(income_df)} 期数据")

                # 打印关键列名供参考
                cols = list(income_df.columns)
                print(f"  [AI]   利润表列: {cols[:8]}...")

            # 3. 资产负债表
            balance_df = ak.stock_financial_report_sina(stock=symbol, symbol='资产负债表')
            if balance_df is not None and not balance_df.empty:
                balance_df = balance_df.sort_values('报告日', ascending=False).head(12)
                data['balance_sheet'] = balance_df.to_dict(orient='records')
                print(f"  [AI] ✓ 资产负债表 {len(balance_df)} 期数据")

            # 4. 现金流量表
            cashflow_df = ak.stock_financial_report_sina(stock=symbol, symbol='现金流量表')
            if cashflow_df is not None and not cashflow_df.empty:
                cashflow_df = cashflow_df.sort_values('报告日', ascending=False).head(12)
                data['cash_flow'] = cashflow_df.to_dict(orient='records')
                print(f"  [AI] ✓ 现金流量表 {len(cashflow_df)} 期数据")

            data['success'] = True

        except Exception as e:
            data['error'] = str(e)
            print(f"  [AI] ❌ 获取财务数据失败: {e}")

        return data

    def _build_analysis_prompt(self, symbol: str, name: str, raw_data: Dict) -> str:
        """
        构建分析提示词 - 让AI直接分析原始财报数据
        """

        # 基本信息
        stock_info = raw_data.get('stock_info', {})
        price = stock_info.get('最新', 'N/A')
        market_cap = stock_info.get('总市值', 'N/A')
        if market_cap and market_cap != 'N/A':
            try:
                market_cap_yi = float(market_cap) / 1e8
                market_cap_str = f"{market_cap_yi:.0f}亿"
            except:
                market_cap_str = market_cap
        else:
            market_cap_str = 'N/A'

        prompt = f"""请对以下公司进行专业的投资分析：

## 📌 公司基本信息
- **股票代码**: {symbol}
- **股票名称**: {name}
- **当前股价**: {price}
- **总市值**: {market_cap_str}

---

## 📊 原始财务报表数据

### 利润表（最近几期）
"""

        # 添加利润表数据
        income_data = raw_data.get('income_statement')
        if income_data:
            # 只取前6期数据避免过长
            for i, record in enumerate(income_data[:6]):
                report_date = record.get('报告日', 'N/A')
                prompt += f"\n**第{i+1}期 (报告日: {report_date})**:\n"

                # 提取关键财务指标
                key_fields = [
                    ('营业收入', '营业总收入'),
                    ('营业成本', '营业成本'),
                    ('营业利润', '营业利润'),
                    ('利润总额', '利润总额'),
                    ('净利润', '净利润'),
                    ('归母净利润', '归属于母公司股东的净利润'),
                    ('扣非净利润', '扣除非经常性损益后的净利润'),
                    ('研发费用', '研发费用'),
                    ('销售费用', '销售费用'),
                    ('管理费用', '管理费用'),
                ]

                for cn_name, alt_name in key_fields:
                    value = record.get(cn_name) or record.get(alt_name)
                    if value is not None:
                        try:
                            val_float = float(value)
                            if abs(val_float) > 100000000:  # 大于1亿
                                prompt += f"- {cn_name}: {val_float/1e8:.2f}亿元\n"
                            elif abs(val_float) > 10000:  # 大于1万
                                prompt += f"- {cn_name}: {val_float/10000:.2f}万元\n"
                            else:
                                prompt += f"- {cn_name}: {val_float:.2f}\n"
                        except (ValueError, TypeError):
                            prompt += f"- {cn_name}: {value}\n"

        prompt += "\n### 资产负债表（最新一期）\n"

        # 添加资产负债表数据（只取最新一期）
        balance_data = raw_data.get('balance_sheet')
        if balance_data and len(balance_data) > 0:
            record = balance_data[0]
            report_date = record.get('报告日', 'N/A')
            prompt += f"(报告日: {report_date})\n"

            key_fields = [
                ('资产总计', '资产合计'),
                ('负债总计', '负债合计'),
                ('归母股东权益', '归属于母公司股东权益合计'),
                ('流动资产', '流动资产合计'),
                ('流动负债', '流动负债合计'),
                ('货币资金', '货币资金'),
                ('应收账款', '应收账款'),
                ('存货', '存货'),
                ('固定资产', '固定资产净额'),
            ]

            for cn_name, alt_name in key_fields:
                value = record.get(cn_name) or record.get(alt_name)
                if value is not None:
                    try:
                        val_float = float(value)
                        if abs(val_float) > 100000000:
                            prompt += f"- {cn_name}: {val_float/1e8:.2f}亿元\n"
                        else:
                            prompt += f"- {cn_name}: {val_float:.2f}\n"
                    except (ValueError, TypeError):
                        prompt += f"- {cn_name}: {value}\n"

        prompt += "\n### 现金流量表（最新一期）\n"

        # 添加现金流量表数据
        cashflow_data = raw_data.get('cash_flow')
        if cashflow_data and len(cashflow_data) > 0:
            record = cashflow_data[0]
            report_date = record.get('报告日', 'N/A')
            prompt += f"(报告日: {report_date})\n"

            key_fields = [
                ('经营现金流净额', '经营活动产生的现金流量净额'),
                ('投资现金流净额', '投资活动产生的现金流量净额'),
                ('筹资现金流净额', '筹资活动产生的现金流量净额'),
                ('期末现金余额', '期末现金及现金等价物余额'),
            ]

            for cn_name, alt_name in key_fields:
                value = record.get(cn_name) or record.get(alt_name)
                if value is not None:
                    try:
                        val_float = float(value)
                        if abs(val_float) > 100000000:
                            prompt += f"- {cn_name}: {val_float/1e8:.2f}亿元\n"
                        else:
                            prompt += f"- {cn_name}: {val_float:.2f}\n"
                    except (ValueError, TypeError):
                        prompt += f"- {cn_name}: {value}\n"

        prompt += """

---

## 请你完成以下分析任务：

### 任务一：财务健康度评估
基于以上原始数据，评估该公司的：
1. 盈利能力（毛利率、净利率、ROE估算）
2. 成长性（营收和利润的同比变化趋势）
3. 财务安全性（资产负债率、流动比率估算）
4. 现金流质量（经营现金流与净利润的匹配度）

### 任务二：费雪原则评分
按照费雪《怎样选择成长股》的核心原则，对该公司打分（0-100分）：
- 产品/市场潜力
- 管理层质量（从费用控制、研发投入推断）
- 财务稳健性
- 成长持续性

### 任务三：GARP因子评估
评估以下8个因子的表现：
1. 盈利预测趋势（从利润变化推断）
2. 盈余惊喜可能性
3. 销售额增长动力
4. 营业利润率水平
5. 自由现金流充裕度
6. 盈利增长速度
7. 盈利动量（加速/减速）
8. ROE水平

### 任务四：估值判断
基于当前市值和最新财报数据：
1. 计算或估算 PE、PB、PS
2. 判断估值是否合理
3. 给出估值评级（低估/合理/高估）

### 任务五：综合投资建议
1. **总体评价**：一句话总结该公司
2. **投资评级**：⭐⭐⭐ 强烈推荐 / ⭐⭐ 推荐 / ⭐ 关注 / 观望 / 不推荐
3. **目标价位**：（如能估算）
4. **核心逻辑**：3个要点支撑你的判断
5. **风险提示**：至少3个主要风险
6. **适合投资者类型**：价值型/成长型/激进型/保守型

请确保你的分析有数据支撑，不要泛泛而谈。"""

        return prompt

    def analyze_stock(self, symbol: str, name: str = None) -> Dict:
        """
        对股票进行AI分析 - 直接分析原始财报数据

        Args:
            symbol: 股票代码
            name: 股票名称（可选）

        Returns:
            包含AI分析结果的字典
        """
        # 获取股票名称
        if name is None:
            try:
                import akshare as ak
                info = ak.stock_individual_info_em(symbol=symbol)
                if info is not None and not info.empty:
                    name_row = info[info['item'] == '股票简称']
                    if not name_row.empty:
                        name = name_row.iloc[0]['value']
            except:
                pass
        if name is None:
            name = symbol

        # 获取原始财务数据
        raw_data = self._fetch_raw_financial_data(symbol)

        # 构建提示词
        prompt = self._build_analysis_prompt(symbol, name, raw_data)

        # 调用AI模型
        ai_response = self._call_ollama(prompt)

        # 构建返回结果
        result = {
            'success': ai_response is not None,
            'model': self.model,
            'analysis': ai_response or self._get_fallback_analysis(symbol, name, raw_data),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_source': 'original_financial_statements',  # 标记数据来源
            'raw_data_summary': {
                'income_periods': len(raw_data.get('income_statement') or []),
                'balance_periods': len(raw_data.get('balance_sheet') or []),
                'cashflow_periods': len(raw_data.get('cash_flow') or []),
                'data_success': raw_data.get('success', False),
            }
        }

        return result

    def _get_fallback_analysis(self, symbol: str, name: str, raw_data: Dict) -> str:
        """当AI不可用时返回的备用分析"""
        success = raw_data.get('success', False)
        error = raw_data.get('error')

        analysis = f"""# 🤖 {name}({symbol}) 财报分析报告

> ⚠️ **注意**: 当前 Ollama AI 服务不可用，以下为基于原始数据的简要摘要。

## 数据获取状态
- **数据获取**: {'✅ 成功' if success else '❌ 失败'}
- **错误信息**: {error or '无'}

"""

        if success:
            # 尝试提取一些关键数据展示
            income_data = raw_data.get('income_statement')
            if income_data and len(income_data) > 0:
                latest = income_data[0]
                analysis += "## 最新一期利润表关键数据\n\n"

                key_items = [
                    ('营业总收入', '营业收入'),
                    ('净利润', '净利润'),
                    ('归母净利润', '归属净利润'),
                    ('研发费用', '研发费用'),
                ]

                for cn, alt in key_items:
                    val = latest.get(cn) or latest.get(alt)
                    if val is not None:
                        try:
                            v = float(val)
                            if abs(v) > 1e8:
                                analysis += f"- **{cn}**: {v/1e8:.2f} 亿元\n"
                            else:
                                analysis += f"- **{cn}**: {v:.2f}\n"
                        except:
                            analysis += f"- **{cn}**: {val}\n"

        analysis += """
---

## 建议

启动 Ollama AI 服务后可获得更深入的专业分析：

```bash
# 安装并启动 Ollama
ollama serve &

# 拉取推荐模型
ollama pull qwen2.5:7b

# 刷新本页面即可看到AI分析结果
```

*AI分析可提供：费雪15原则评分、GARP因子评估、估值判断、投资建议*
"""
        return analysis

    def compare_stocks_ai(self, symbols: List[str]) -> Optional[str]:
        """AI对比分析多只股票"""
        comparisons = []

        for symbol in symbols:
            try:
                raw_data = self._fetch_raw_financial_data(symbol)
                if raw_data.get('success'):
                    income = raw_data.get('income_statement', [])
                    if income:
                        latest = income[0]
                        revenue = latest.get('营业总收入') or latest.get('营业收入')
                        profit = latest.get('净利润') or latest.get('归母净利润')
                        comparisons.append({
                            'symbol': symbol,
                            'revenue': revenue,
                            'profit': profit
                        })
            except:
                continue

        if not comparisons:
            return None

        prompt = "以下是多家公司的最新财务数据对比：\n\n"
        prompt += "| 公司 | 营业收入 | 净利润 |\n|------|----------|--------|\n"
        for c in comparisons:
            rev = f"{float(c['revenue'])/1e8:.1f}亿" if c['revenue'] else 'N/A'
            prof = f"{float(c['profit'])/1e8:.1f}亿" if c['profit'] else 'N/A'
            prompt += f"| {c['symbol']} | {rev} | {prof} |\n"

        prompt += "\n请对比以上公司，给出投资排序建议。"

        return self._call_ollama(prompt)

    def list_available_models(self) -> List[str]:
        """列出可用模型"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                return [m.get('name', '') for m in response.json().get('models', [])]
        except:
            pass
        return []


if __name__ == '__main__':
    print("=" * 60)
    print("🧪 Ollama AI 分析模块测试（直接分析财报版）")
    print("=" * 60)

    analyst = OllamaAnalyst()

    print("\n[1] 检查 Ollama 服务...")
    if analyst.check_ollama_available():
        print(f"✅ Ollama 可用，模型: {analyst.model}")

        print("\n[2] 测试完整分析流程...")
        result = analyst.analyze_stock('300750', '宁德时代')

        print(f"\n[3] 结果:")
        print(f"  成功: {result.get('success')}")
        print(f"  模型: {result.get('model')}")
        print(f"  数据来源: {result.get('data_source')}")
        print(f"  分析长度: {len(result.get('analysis', ''))} 字符")

        if result.get('analysis'):
            print(f"\n{'='*60}")
            print("AI 分析报告预览（前500字）:")
            print(f"{'='*60}")
            print(result['analysis'][:500])
            print("...")
    else:
        print("❌ Ollama 服务不可用")
        print("💡 请运行: ollama serve && ollama pull qwen2.5:7b")


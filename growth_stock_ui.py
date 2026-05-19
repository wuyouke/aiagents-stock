#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长股选股系统 - Streamlit UI（增强版）
双引擎并行：Fisher定性 + GARP量化 + 估值分析
新增功能：
1. 更美观的UI设计
2. PEG指标展示
3. 行业分类显示
4. 动态权重可视化
5. PDF/Markdown报告导出
6. FinGPT智能财报分析
"""

import base64
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 页面配置
st.set_page_config(
    page_title="🚀 成长股选股系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 增强版CSS样式
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    .main-header {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
        padding: 1rem 0;
    }

    .sub-header {
        font-size: 1.15rem;
        color: #6b7280;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 400;
    }

    .score-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 1.5rem;
        color: white;
        text-align: center;
        box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
        transition: transform 0.3s ease;
    }

    .score-card:hover {
        transform: translateY(-5px);
    }

    .score-card .score {
        font-size: 3.5rem;
        font-weight: 800;
        line-height: 1;
    }

    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 12px;
        padding: 1.2rem;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        transform: translateX(5px);
    }

    .info-badge {
        display: inline-block;
        padding: 0.35rem 0.9rem;
        border-radius: 20px;
        font-weight: 500;
        font-size: 0.85rem;
        margin: 0.2rem;
    }

    .badge-growth { background: linear-gradient(135deg, #11998e, #38ef7d); color: white; }
    .badge-value { background: linear-gradient(135deg, #eb3349, #f45c43); color: white; }
    .badge-balanced { background: linear-gradient(135deg, #4facfe, #00f2fe); color: white; }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        border-radius: 12px 12px 0 0;
        background: #f8f9fa;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
    }

    /* 侧边栏样式 */
    .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }

    /* 按钮增强 */
    .stButton>button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
    }

    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(0,0,0,0.15) !important;
    }

    /* 数据框美化 */
    .dataframe {
        border-radius: 12px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """初始化会话状态"""
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = []
    if 'batch_results' not in st.session_state:
        st.session_state.batch_results = None
    if 'current_stock' not in st.session_state:
        st.session_state.current_stock = None


def run_single_analysis(symbol: str) -> dict:
    """运行单只股票分析"""
    try:
        from growth_stock_engine import GrowthStockEngine
        engine = GrowthStockEngine()
        result = engine.analyze_stock(symbol)
        return result
    except Exception as e:
        st.error(f"分析失败: {str(e)}")
        return None


def display_score_gauge(score: float, title: str, color: str = "#667eea") -> go.Figure:
    """显示评分仪表盘 - 增强版"""
    # 根据分数选择颜色
    if score >= 70:
        gauge_color = "#38ef7d"
    elif score >= 55:
        gauge_color = "#4facfe"
    elif score >= 40:
        gauge_color = "#ffd93d"
    else:
        gauge_color = "#ff6b6b"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={
            'text': f"<span style='font-size:1.1rem;font-weight:600'>{title}</span>",
            'font': {'color': '#374151'}
        },
        delta={'reference': 60, 'increasing': {'color': '#38ef7d'}, 'decreasing': {'color': '#ff6b6b'}},
        gauge={
            'axis': {
                'range': [0, 100],
                'tickwidth': 1,
                'tickcolor': '#9ca3af'
            },
            'bar': {'color': gauge_color, 'thickness': 0.3},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': '#e5e7eb',
            'steps': [
                {'range': [0, 40], 'color': '#fee2e2'},
                {'range': [40, 55], 'color': '#fef3c7'},
                {'range': [55, 70], 'color': '#dbeafe'},
                {'range': [70, 100], 'color': '#d1fae5'}
            ],
            'threshold': {
                'line': {'color': gauge_color, 'width': 4},
                'thickness': 0.8,
                'value': score
            }
        }
    ))

    fig.update_layout(
        height=180,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='white'
    )
    return fig


def display_factor_radar(factor_scores: dict, factor_weights: dict) -> go.Figure:
    """显示因子雷达图 - 增强版"""
    categories = list(factor_scores.keys())
    values = list(factor_scores.values())
    weights = [factor_weights.get(f, 1) for f in categories]

    # 归一化权重
    total_weight = sum(weights)
    weights = [w / total_weight * 100 for w in weights]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(102, 126, 234, 0.3)',
        line=dict(color='#667eea', width=2),
        name='因子得分'
    ))

    fig.add_trace(go.Scatterpolar(
        r=[w * 100 for w in weights[:len(values)]] + [weights[0] * 100],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(156, 163, 175, 0.2)',
        line=dict(color='#9ca3af', width=1, dash='dash'),
        name='理想权重'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=10)
            ),
            angularaxis=dict(
                tickfont=dict(size=11)
            )
        ),
        showlegend=True,
        height=300,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    return fig


def display_dimensions_bar(dim_scores: dict, dim_weights: dict) -> go.Figure:
    """显示维度得分柱状图 - 增强版"""
    categories = list(dim_scores.keys())
    values = list(dim_scores.values())
    colors = ['#38ef7d' if v >= 70 else '#4facfe' if v >= 55 else '#ffd93d' if v >= 40 else '#ff6b6b' for v in values]

    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=values,
            marker_color=colors,
            text=[f'{v:.1f}' for v in values],
            textposition='outside',
            textfont=dict(size=11)
        )
    ])

    fig.update_layout(
        yaxis=dict(
            title='得分',
            range=[0, 100],
            tickfont=dict(size=11)
        ),
        xaxis=dict(
            tickfont=dict(size=10)
        ),
        height=250,
        margin=dict(l=20, r=20, t=20, b=80),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    return fig


def get_download_link(content: str, filename: str) -> str:
    """生成下载链接"""
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}" style="display:inline-block;padding:0.5rem 1rem;background:linear-gradient(135deg,#667eea,#764ba2);color:white;border-radius:8px;text-decoration:none;font-weight:600;">📥 下载分析报告</a>'
    return href


def generate_report_markdown(result: dict) -> str:
    """生成 Markdown 格式的报告"""
    md = f"""# {result.get('name', '未知')} ({result.get('symbol', '')}) 成长股分析报告

**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 一、综合评分

| 维度 | 评分 |
|------|------|
| Fisher定生成年股 | {result.get('fisher', {}).get('score', 0):.1f}/100 |
| GARP量化因子 | {result.get('garp', {}).get('score', 0):.1f}/100 |
| 估值分析 | {result.get('valuation', {}).get('score', 0):.1f}/100 |
| **综合评分** | **{result.get('combined_score', 0):.1f}/100** |

**推荐等级**: {result.get('recommendation', 'N/A')}
**操作建议**: {result.get('action', 'N/A')}

## 二、Fisher分析要点

## 二、Fisher分析要点

- 营收CAGR: {result.get('fisher', {}).get('metrics', {}).get('revenue_cagr', 'N/A')}%
- 净利润CAGR: {result.get('fisher', {}).get('metrics', {}).get('profit_cagr', 'N/A')}%
- ROIC: {result.get('fisher', {}).get('metrics', {}).get('roic', 'N/A')}%
- 净利率: {result.get('fisher', {}).get('metrics', {}).get('net_margin', 'N/A')}%
- 毛利率稳定性: {result.get('fisher', {}).get('metrics', {}).get('margin_stability', 'N/A')}

## 三、GARP量化因子

| 因子 | 得分 | 原始值 |
|------|------|--------|
"""
    for factor, score in result.get('garp', {}).get('factor_scores', {}).items():
        value = result.get('garp', {}).get('factor_values', {}).get(factor, 'N/A')
        factor_names = {
            'earnings_revision': '盈利预测调整',
            'earnings_surprise': '盈余惊喜',
            'sales_growth': '销售额增长',
            'operating_margin': '营业利润率',
            'free_cash_flow': '自由现金流',
            'profit_growth': '盈利增长',
            'earnings_momentum': '盈利动量',
            'roe': 'ROE'
        }
        md += f"| {factor_names.get(factor, factor)} | {score:.1f} | {value} |\n"

    md += f"""
## 四、估值分析

| 指标 | 数值 | 评价 |
|------|------|------|
| PEG | {result.get('valuation', {}).get('peg', 'N/A')} | 低估 |
| PE | {result.get('valuation', {}).get('pe', 'N/A')} | - |
| PB | {result.get('valuation', {}).get('pb', 'N/A')} | - |
| 利润增长 | {result.get('valuation', {}).get('profit_growth', 'N/A')}% | - |

**行业**: {result.get('valuation', {}).get('industry_name', '未知')}
**股票类型**: {result.get('stock_type', 'balanced')}

---

*本报告由成长股选股系统自动生成*
"""
    return md


def render_fingpt_tab(symbol: str, name: str = None):
    """渲染 FinGPT 智能分析标签页 - 新增！"""
    st.markdown("### 🧠 FinGPT 智能财报分析")

    # 初始化分析器
    try:
        from fingpt_analyzer import FinGPTAnalyzer
        analyzer = FinGPTAnalyzer()
    except ImportError:
        st.error("❌ 无法导入 FinGPT 分析模块")
        return

    # 检查 Ollama
    col1, col2 = st.columns([3, 1])
    with col1:
        if analyzer.check_ollama_available():
            st.success(f"✅ Ollama 已连接 - 模型: {analyzer.ollama_model}")
        else:
            st.warning("⚠️ Ollama 服务不可用，将使用规则分析")

    with col2:
        if st.button("🔄 重新分析", key="fingpt_refresh"):
            st.rerun()

    # 分析公司
    with st.spinner("📊 正在获取财务数据并分析..."):
        result = analyzer.analyze_company(symbol, name)

    if 'error' in result:
        st.error(result['error'])
        return

    # 显示结果
    st.markdown("---")

    # 评分卡片
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        score = result.get('overall_score', 0)
        score_color = "#38ef7d" if score >= 70 else "#4facfe" if score >= 50 else "#ffd93d" if score >= 30 else "#ff6b6b"
        rec = result.get('recommendation', {})
        action = rec.get('action', 'N/A')

        st.markdown(f"""
        <div style="background:{score_color};border-radius:16px;padding:1.5rem;color:white;text-align:center;">
            <div style="font-size:0.9rem;opacity:0.9;">FinGPT 综合评分</div>
            <div style="font-size:3rem;font-weight:800;">{score:.0f}</div>
            <div style="font-size:1.1rem;font-weight:600;margin-top:0.5rem;">{action}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # 关键指标
        metrics = result.get('metrics', {})
        roe = metrics.get('roe', 0)
        gross_margin = metrics.get('gross_margin', 0)
        roe_color = '#059669' if roe > 15 else '#dc2626'
        gm_color = '#059669' if gross_margin > 30 else '#dc2626'

        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size:0.85rem;color:#6b7280;">ROE (净资产收益率)</div>
            <div style="font-size:1.8rem;font-weight:700;color:{roe_color};">{roe:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-card" style="margin-top:0.8rem;">
            <div style="font-size:0.85rem;color:#6b7280;">毛利率</div>
            <div style="font-size:1.8rem;font-weight:700;color:{gm_color};">{gross_margin:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        # 财务数据摘要
        data = result.get('financial_data', {})
        revenue = data.get('revenue', 0)
        net_profit = data.get('net_profit', 0)

        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size:0.85rem;color:#6b7280;">营业收入</div>
            <div style="font-size:1.4rem;font-weight:700;color:#374151;">{revenue/1e8:.2f} 亿</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-card" style="margin-top:0.8rem;">
            <div style="font-size:0.85rem;color:#6b7280;">净利润</div>
            <div style="font-size:1.4rem;font-weight:700;color:#374151;">{net_profit/1e8:.2f} 亿</div>
        </div>
        """, unsafe_allow_html=True)

    # AI 分析报告
    st.markdown("---")
    st.markdown("#### 📝 AI 分析报告")

    fingpt_analysis = result.get('fingpt_analysis', '')
    if fingpt_analysis:
        st.markdown(fingpt_analysis)
    else:
        st.info("AI 分析报告暂不可用")

    # 原始数据折叠
    with st.expander("📋 查看原始财务数据"):
        st.json(result.get('financial_data', {}))


def render_summary_tab(result: dict):
    """渲染综合摘要标签页 - 增强版"""
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1.2])

    fisher_score = result.get('fisher', {}).get('score', 0)
    garp_score = result.get('garp', {}).get('score', 0)
    combined_score = result.get('combined_score', 0)
    valuation_score = result.get('valuation', {}).get('score', 0)

    with col1:
        fig = display_score_gauge(fisher_score, "🐟 Fisher")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = display_score_gauge(garp_score, "📈 GARP", "#38ef7d")
        st.plotly_chart(fig, use_container_width=True)

    with col3:
        fig = display_score_gauge(valuation_score, "💰 估值", "#f59e0b")
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        # 综合评分大卡片
        score_color = "#38ef7d" if combined_score >= 60 else "#4facfe" if combined_score >= 45 else "#ffd93d" if combined_score >= 35 else "#ff6b6b"
        st.markdown(f"""
        <div class="score-card" style="background:linear-gradient(135deg,{score_color},{score_color}dd);">
            <div style="font-size:0.9rem;opacity:0.9;">综合评分</div>
            <div class="score">{combined_score:.1f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        rec = result.get('recommendation', 'N/A')
        action = result.get('action', '')

        # 推荐等级卡片
        if '强烈推荐' in rec or '推荐' in rec:
            rec_bg = "linear-gradient(135deg,#11998e,#38ef7d)"
        elif '关注' in rec or '观望' in rec:
            rec_bg = "linear-gradient(135deg,#4facfe,#00f2fe)"
        else:
            rec_bg = "linear-gradient(135deg,#eb3349,#f45c43)"

        st.markdown(f"""
        <div style="background:{rec_bg};border-radius:16px;padding:1.5rem;color:white;text-align:center;height:100%;">
            <div style="font-size:0.9rem;opacity:0.9;margin-bottom:0.5rem;">推荐等级</div>
            <div style="font-size:1.3rem;font-weight:700;">{rec}</div>
            <div style="font-size:0.85rem;margin-top:0.8rem;opacity:0.9;">{action}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 操作建议详情
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🐟 Fisher分析要点")
        fisher = result.get('fisher', {})
        st.write(f"**评级**: {fisher.get('rating', 'N/A')}")
        if fisher.get('data_success'):
            metrics = fisher.get('metrics', {})
            st.write(f"• 营收增长: **{metrics.get('revenue_cagr', 'N/A')}%**")
            st.write(f"• 净利润增长: **{metrics.get('profit_cagr', 'N/A')}%**")
            st.write(f"• ROIC: **{metrics.get('roic', 'N/A')}%**")
            st.write(f"• 净利率: **{metrics.get('net_margin', 'N/A')}%**")

    with col2:
        st.markdown("#### 📈 GARP + 估值要点")
        garp = result.get('garp', {})
        valuation = result.get('valuation', {})
        st.write(f"**GARP评级**: {garp.get('rating', 'N/A')}")
        if garp.get('data_success'):
            values = garp.get('factor_values', {})
            st.write(f"• 盈利增长: **{values.get('profit_growth', 'N/A')}%**")
            st.write(f"• 营业利润率: **{values.get('operating_margin', 'N/A')}%**")
            st.write(f"• ROE: **{values.get('roe', 'N/A')}%**")

        st.write(f"**PEG**: {valuation.get('peg', 'N/A')} ({'低估' if (valuation.get('peg') or 999) <= 1 else '合理' if (valuation.get('peg') or 999) <= 1.5 else '偏高'})")
        st.write(f"**PE**: {valuation.get('pe', 'N/A')}")


def render_fisher_tab(result: dict):
    """渲染Fisher分析标签页 - 增强版"""
    if not result.get('fisher', {}).get('data_success'):
        st.warning("⚠️ Fisher分析数据不可用")
        return

    fisher = result['fisher']
    dim_scores = fisher.get('dimension_scores', {})
    metrics = fisher.get('metrics', {})

    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col1:
        fig = display_score_gauge(fisher['score'], "🐟 Fisher评分")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### 📊 各维度得分")
        dim_names = {
            'growth': '成长性',
            'profitability': '盈利能力',
            'efficiency': '运营效率',
            'quality': '财务质量',
            'innovation': '研发创新'
        }

        for dim, score in dim_scores.items():
            name = dim_names.get(dim, dim)
            color = "🟢" if score >= 70 else "🟡" if score >= 40 else "🔴"

            # 进度条
            pct = score / 100
            bar_color = "#38ef7d" if score >= 70 else "#4facfe" if score >= 40 else "#ffd93d"

            st.markdown(f"""
            <div style="display:flex;align-items:center;margin:0.4rem 0;">
                <span style="margin-right:0.5rem;">{color}</span>
                <div style="flex:1;">
                    <span style="font-size:0.9rem;color:#4b5563;">{name}</span>
                    <div style="background:#e5e7eb;border-radius:10px;height:8px;margin-top:4px;">
                        <div style="background:{bar_color};width:{pct:.0%};height:100%;border-radius:10px;"></div>
                    </div>
                </div>
                <span style="font-weight:700;color:#111827;width:45px;text-align:right;">{score:.0f}</span>
            </div>
            """, unsafe_allow_html=True)

    with col3:
        st.markdown("##### 📈 原始指标值")
        metric_names = {
            'revenue_cagr': '营收CAGR',
            'profit_cagr': '净利CAGR',
            'roic': 'ROIC',
            'net_margin': '净利率',
            'margin_stability': '毛利率稳定',
            'inventory_turnover': '存货周转天',
            'receivable_turnover': '应收周转天',
            'sales_expense_ratio': '销售费用率',
            'cash_flow_quality': '现金流/净利',
            'debt_ratio': '资产负债率',
            'rd_expense_ratio': '研发占比',
            'non_recurring_adjust': '扣非质量',
        }

        for metric, value in metrics.items():
            if value is not None and isinstance(value, (int, float)):
                name = metric_names.get(metric, metric)
                unit = "%" if metric in ['revenue_cagr', 'profit_cagr', 'roic', 'net_margin',
                                        'cash_flow_quality', 'debt_ratio', 'sales_expense_ratio',
                                        'rd_expense_ratio', 'non_recurring_adjust'] else "天"

                # 颜色编码
                val_color = "#059669" if (unit == "%" and value > 0) or (unit != "天") else "#dc2626"

                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size:0.85rem;color:#6b7280;">{name}</div>
                    <div style="font-size:1.2rem;font-weight:700;color:{val_color};">{value:.2f}{unit}</div>
                </div>
                """, unsafe_allow_html=True)

    # 维度得分柱状图
    st.markdown("---")
    from fisher_selector import FisherSelector
    fisher_sel = FisherSelector()
    fig = display_dimensions_bar(dim_scores, fisher_sel.dimension_weights)
    st.plotly_chart(fig, use_container_width=True)


def render_garp_tab(result: dict):
    """渲染GARP分析标签页 - 增强版"""
    if not result or not result.get('garp', {}).get('data_success'):
        st.warning("⚠️ GARP分析数据不可用")
        return

    garp = result['garp']
    factor_scores = garp.get('factor_scores', {})
    factor_values = garp.get('factor_values', {})

    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col1:
        fig = display_score_gauge(garp['score'], "📈 GARP评分", "#38ef7d")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### 📊 各因子得分")
        factor_names = {
            'earnings_revision': '盈利预测调整',
            'earnings_surprise': '盈余惊喜',
            'sales_growth': '销售额增长',
            'operating_margin': '营业利润率',
            'free_cash_flow': '自由现金流',
            'profit_growth': '盈利增长',
            'earnings_momentum': '盈利动量',
            'roe': 'ROE',
        }

        for factor, score in factor_scores.items():
            name = factor_names.get(factor, factor)
            color = "🟢" if score >= 70 else "🟡" if score >= 40 else "🔴"

            # 进度条
            pct = score / 100
            bar_color = "#38ef7d" if score >= 70 else "#4facfe" if score >= 40 else "#ffd93d"

            st.markdown(f"""
            <div style="display:flex;align-items:center;margin:0.4rem 0;">
                <span style="margin-right:0.5rem;">{color}</span>
                <div style="flex:1;">
                    <span style="font-size:0.9rem;color:#4b5563;">{name}</span>
                    <div style="background:#e5e7eb;border-radius:10px;height:8px;margin-top:4px;">
                        <div style="background:{bar_color};width:{pct:.0%};height:100%;border-radius:10px;"></div>
                    </div>
                </div>
                <span style="font-weight:700;color:#111827;width:45px;text-align:right;">{score:.0f}</span>
            </div>
            """, unsafe_allow_html=True)

    with col3:
        st.markdown("##### 📈 原始指标值")
        for factor, value in factor_values.items():
            if value is not None and isinstance(value, (int, float)):
                name = factor_names.get(factor, factor)
                unit = "%" if factor != 'earnings_momentum' else ""

                val_color = "#059669" if (isinstance(value, (int, float)) and (
                    (factor in ['roe', 'operating_margin', 'free_cash_flow', 'profit_growth', 'sales_growth'] and value > 0) or
                    factor == 'earnings_momentum' and value > 50
                )) else "#dc2626"

                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size:0.85rem;color:#6b7280;">{name}</div>
                    <div style="font-size:1.2rem;font-weight:700;color:{val_color};">{value:.2f}{unit}</div>
                </div>
                """, unsafe_allow_html=True)

    # 因子雷达图
    st.markdown("---")
    from garp_selector import GARPSelector
    garp_sel = GARPSelector()
    fig = display_factor_radar(factor_scores, garp_sel.factor_weights)
    st.plotly_chart(fig, use_container_width=True)


def render_valuation_tab(result: dict):
    """渲染估值分析标签页 - 新增！"""
    valuation = result.get('valuation', {})

    if not valuation.get('data_success'):
        st.warning("⚠️ 估值数据不可用")
        return

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        # PEG指标卡片
        peg = valuation.get('peg')
        growth = valuation.get('profit_growth')

        st.markdown("##### 📊 PEG指标（核心）")
        if peg is not None:
            if peg <= 1.0:
                peg_color = "#38ef7d"
                peg_status = "✅ 低估"
            elif peg <= 1.5:
                peg_color = "#4facfe"
                peg_status = "⚖️ 合理"
            elif peg <= 2.0:
                peg_color = "#ffd93d"
                peg_status = "⚠️ 偏高"
            else:
                peg_color = "#ff6b6b"
                peg_status = "❌ 高估"

            st.markdown(f"""
            <div class="score-card" style="background:linear-gradient(135deg,{peg_color}22,{peg_color}44);">
                <div style="font-size:0.9rem;opacity:0.9;">PEG比率</div>
                <div style="font-size:2.5rem;font-weight:800;">{peg:.2f}</div>
                <div style="font-size:0.95rem;font-weight:600;">{peg_status}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("PEG数据暂缺")

        # 利润增长率
        if growth is not None:
            st.markdown(f"""
            <div class="metric-card" style="margin-top:1rem;">
                <div style="font-size:0.85rem;color:#6b7280;">近3年净利润CAGR</div>
                <div style="font-size:1.5rem;font-weight:700;color:#059669;">{growth:+.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("##### 💰 传统估值指标")
        pe = valuation.get('pe')
        pb = valuation.get('pb')
        pe_pct = valuation.get('pe_percentile')

        # PE卡片
        if pe is not None:
            pe_color = "#38ef7d" if pe <= 25 else "#4facfe" if pe <= 45 else "#ffd93d" if pe <= 65 else "#ff6b6b"
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size:0.85rem;color:#6b7280;">市盈率 (PE)</div>
                <div style="font-size:1.5rem;font-weight:700;color:{pe_color};">{pe:.1f}</div>
                <div style="font-size:0.8rem;color:#9ca3af;">历史分位: {pe_pct or 'N/A'}%</div>
            </div>
            """, unsafe_allow_html=True)

        # PB卡片
        if pb is not None:
            pb_color = "#38ef7d" if pb <= 2.5 else "#4facfe" if pb <= 4 else "#ffd93d" if pb <= 6 else "#ff6b6b"
            st.markdown(f"""
            <div class="metric-card" style="margin-top:0.8rem;">
                <div style="font-size:0.85rem;color:#6b7280;">市净率 (PB)</div>
                <div style="font-size:1.5rem;font-weight:700;color:{pb_color};">{pb:.2f}</div>
            </div>
            """, unsafe_allow_html=True)

    with col3:
        st.markdown("##### 🏭 行业与类型")
        industry_name = valuation.get('industry_name', '未知')
        stock_type = result.get('stock_type', 'balanced')

        # 股票类型标签
        type_badge = {
            'growth': ('badge-growth', '🚀 成长型'),
            'value': ('badge-value', '💰 价值型'),
            'balanced': ('badge-balanced', '⚖️ 均衡型')
        }.get(stock_type, ('badge-balanced', '⚖️ 均衡型'))

        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size:0.85rem;color:#6b7280;">所属行业</div>
            <div style="font-size:1.2rem;font-weight:700;color:#374151;">{industry_name}</div>
        </div>

        <div style="margin-top:0.8rem;">
            <span class="info-badge {type_badge[0]}">{type_badge[1]}</span>
        </div>
        """, unsafe_allow_html=True)

        # 权重配置
        weights = result.get('weights_used', {})
        if weights:
            st.markdown("<br><small style='color:#6b7280;'>动态权重配置：</small>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="font-size:0.8rem;line-height:1.6;">
                • Fisher: <b>{weights.get('fisher', 0):.0%}</b><br>
                • GARP: <b>{weights.get('garp', 0):.0%}</b><br>
                • Valuation: <b>{weights.get('valuation', 0):.0%}</b>
            </div>
            """, unsafe_allow_html=True)

    # 详细分析文本
    detailed_analysis = valuation.get('detailed_analysis')
    if detailed_analysis:
        st.markdown("---")
        st.markdown(detailed_analysis)


def render_ai_tab(result: dict):
    """渲染 AI 智能分析标签页 - 新增！"""
    ai_data = result.get('ai_analysis')

    if ai_data is None:
        # AI 不可用时的提示
        st.markdown("""
        ### 🤖 AI 智能分析

        <div style="background:#fef3c7;border-left:4px solid #f59e0b;padding:1.2rem;border-radius:8px;margin:1rem 0;">
            <h4 style="margin:0 0 0.5rem 0;color:#92400e;">⚠️ AI 分析功能未启用</h4>
            <p style="margin:0;color:#92400e;font-size:0.95rem;">
                要启用本地 AI 分析功能，请按以下步骤操作：
            </p>
            <ol style="color:#78350f;margin:0.5rem 0 0 1.2rem;font-size:0.9rem;line-height:1.6;">
                <li><b>安装 Ollama</b>: 访问 <a href="https://ollama.ai" target="_blank">ollama.ai</a> 下载安装</li>
                <li><b>启动服务</b>: 终端运行 <code>ollama serve</code></li>
                <li><b>拉取模型</b>: 运行 <code>ollama pull qwen2.5:7b</code></li>
                <li><b>重启本应用</b>: 刷新页面即可使用 AI 分析</li>
            </ol>
            <p style="margin:0.5rem 0 0 0;color:#92400e;font-size:0.85rem;">
                💡 推荐模型：qwen2.5:7b（中文优秀）、llama3.2:3b（轻量快速）
            </p>
        </div>
        """, unsafe_allow_html=True)

        # 显示备用分析
        fallback_analysis = f"""
### 📊 {result.get('name', 'N/A')}({result.get('symbol', 'N/A')}) 规则分析

#### 综合评价
- **综合评分**: {result.get('combined_score', 0):.1f}/100
- **推荐等级**: {result.get('recommendation', 'N/A')}
- **股票类型**: {'🚀 成长型' if result.get('stock_type') == 'growth' else '💰 价值型' if result.get('stock_type') == 'value' else '⚖️ 均衡型'}

#### 关键指标速览
| 指标 | 数值 | 解读 |
|------|------|------|
| Fisher评分 | {result.get('fisher', {}).get('score', 0):.1f} | {'优秀' if result.get('fisher', {}).get('score', 0) >= 60 else '良好' if result.get('fisher', {}).get('score', 0) >= 45 else '一般'} |
| GARP评分 | {result.get('garp', {}).get('score', 0):.1f} | {'优秀' if result.get('garp', {}).get('score', 0) >= 60 else '良好' if result.get('garp', {}).get('score', 0) >= 45 else '一般'} |
| PEG | {result.get('valuation', {}).get('peg', 'N/A')} | {'✅ 合理' if (result.get('valuation', {}).get('peg') or 999) <= 1 else '⚠️ 偏高' if (result.get('valuation', {}).get('peg') or 999) <= 1.5 else '❌ 过高'} |
| PE | {result.get('valuation', {}).get('pe', 'N/A')} | - |
| 利润增长 | {result.get('valuation', {}).get('profit_growth', 'N/A')}% | - |

#### 操作建议
> **{result.get('recommendation', 'N/A')}**
>
> {result.get('action', 'N/A')}

---
*此为基于规则的自动分析。启动 Ollama 后可获得更深入的 AI 解读。*
"""
        st.markdown(fallback_analysis)
        return

    # AI 分析可用时显示
    success = ai_data.get('success', False)
    model = ai_data.get('model', 'Unknown')
    analysis_text = ai_data.get('analysis', '')
    timestamp = ai_data.get('timestamp', '')

    # 标题区域
    col_title, col_btn1, col_btn2 = st.columns([4, 1, 1])

    with col_title:
        if success:
            st.success(f"✅ AI 分析完成 - 模型: {model}")
        else:
            st.warning("⚠️ AI 分析未完全成功")

    with col_btn1:
        # 复制按钮
        analysis_for_js = analysis_text.replace('`', '\\`').replace('$', '\\$')[:2000]
        st.markdown(f"""
        <script>
        function copyAnalysis() {{
            navigator.clipboard.writeText(`{analysis_for_js}`);
        }}
        </script>
        <button onclick="copyAnalysis()" style="
            padding:0.5rem 1rem;
            background:linear-gradient(135deg,#667eea,#764ba2);
            color:white;
            border:none;
            border-radius:8px;
            cursor:pointer;
            font-weight:600;
            width:100%;
        ">📋 复制分析文本</button>
        """, unsafe_allow_html=True)

    with col_btn2:
        # 重新分析按钮
        if st.button("🔄 重新分析", use_container_width=True):
            st.rerun()

    # 分析内容
    if analysis_text:
        st.markdown("---")
        st.markdown(analysis_text)
    else:
        st.warning("AI 分析结果为空")


def render_batch_results(results: list):
    """渲染批量分析结果"""
    if not results:
        st.warning("没有批量分析结果")
        return

    df = pd.DataFrame([{
        '股票代码': r.get('symbol', ''),
        '股票名称': r.get('name', ''),
        '综合评分': r.get('combined_score', 0),
        'Fisher评分': r.get('fisher', {}).get('score', 0),
        'GARP评分': r.get('garp', {}).get('score', 0),
        '估值评分': r.get('valuation', {}).get('score', 0),
        '推荐等级': r.get('recommendation', ''),
        'PEG': r.get('valuation', {}).get('peg', 'N/A'),
        '股票类型': {'growth': '🚀 成长型', 'value': '💰 价值型', 'balanced': '⚖️ 均衡型'}.get(r.get('stock_type', ''), '')
    } for r in results])

    # 排序
    df = df.sort_values('综合评分', ascending=False)

    # 颜色映射
    def color_score(val):
        if val >= 70:
            return 'background-color: #d1fae5; color: #065f46'
        elif val >= 55:
            return 'background-color: #dbeafe; color: #1e40af'
        elif val >= 40:
            return 'background-color: #fef3c7; color: #92400e'
        else:
            return 'background-color: #fee2e2; color: #991b1b'

    # 应用样式
    st.markdown("### 📊 批量分析结果")

    col_sort = st.columns([1, 1])
    with col_sort[0]:
        sort_by = st.selectbox("排序方式", ['综合评分', 'Fisher评分', 'GARP评分', '估值评分', 'PEG'], index=0)
    with col_sort[1]:
        top_n = st.slider("显示数量", 5, len(df), min(20, len(df)))

    df_sorted = df.sort_values(sort_by, ascending=False).head(top_n)

    st.dataframe(
        df_sorted.style.applymap(color_score, subset=['综合评分', 'Fisher评分', 'GARP评分', '估值评分']),
        use_container_width=True,
        height=400
    )

    # 图表
    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        # 评分对比条形图
        fig = px.bar(
            df_sorted,
            x='股票代码',
            y=['Fisher评分', 'GARP评分', '估值评分'],
            title="各维度评分对比",
            barmode='group',
            color_discrete_sequence=['#667eea', '#38ef7d', '#f59e0b']
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    with col_chart2:
        # 综合评分饼图
        rec_counts = df_sorted['推荐等级'].value_counts()
        fig = px.pie(
            values=rec_counts.values,
            names=rec_counts.index,
            title="推荐等级分布",
            hole=0.4
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)


def main():
    """主函数"""
    init_session_state()

    st.markdown('<h1 class="main-header">🚀 成长股选股系统</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Fisher定性 + GARP量化 + 估值分析 + FinGPT智能分析 四引擎驱动</p>', unsafe_allow_html=True)

    # 侧边栏
    with st.sidebar:
        st.markdown("## 📊 分析设置")

        # 分析模式
        analysis_mode = st.radio(
            "选择分析模式",
            ["🔍 单股分析", "📋 批量分析", "⚖️ 对比分析"],
            help="选择要执行的股票分析类型"
        )

        # 股票代码输入
        if analysis_mode == "🔍 单股分析":
            symbol = st.text_input("股票代码", placeholder="如: 000001", help="输入6位股票代码").strip()
            if symbol and len(symbol) == 6:
                if st.button("🚀 开始分析", use_container_width=True):
                    with st.spinner("正在分析..."):
                        result = run_single_analysis(symbol)
                        if result:
                            st.session_state.current_stock = result

        elif analysis_mode in ["📋 批量分析", "⚖️ 对比分析"]:
            symbols = st.text_area(
                "股票代码列表",
                placeholder="每行一个代码，如:\n000001\n000002\n600519",
                help="输入多个股票代码，每行一个"
            )
            if symbols:
                symbol_list = [s.strip() for s in symbols.split('\n') if s.strip()]
                if st.button("🚀 开始批量分析", use_container_width=True):
                    with st.spinner(f"正在分析 {len(symbol_list)} 只股票..."):
                        from growth_stock_engine import GrowthStockEngine
                        engine = GrowthStockEngine()
                        results = []
                        for sym in symbol_list:
                            try:
                                r = engine.analyze_stock(sym)
                                if r:
                                    results.append(r)
                            except Exception as e:
                                st.warning(f"分析 {sym} 失败: {e}")
                        st.session_state.batch_results = results

        st.markdown("---")
        st.markdown("## ⚙️ 参数设置")

        # AI 分析开关
        enable_ai = st.checkbox("启用AI分析", value=True, help="使用本地Ollama进行深度分析")

        # 权重配置
        st.markdown("##### 权重配置")
        weight_mode = st.radio(
            "权重模式",
            ["自动（根据股票类型）", "手动设置"],
            help="选择权重分配方式"
        )

        if weight_mode == "手动设置":
            fisher_w = st.slider("Fisher权重", 0.0, 1.0, 0.4, 0.05)
            garp_w = st.slider("GARP权重", 0.0, 1.0, 0.35, 0.05)
            valuation_w = st.slider("估值权重", 0.0, 1.0, 0.25, 0.05)

            # 确保总和为1
            total = fisher_w + garp_w + valuation_w
            if abs(total - 1.0) > 0.01:
                st.warning(f"权重总和为 {total:.2f}，已自动归一化")
                factor = 1.0 / total
                fisher_w *= factor
                garp_w *= factor
                valuation_w *= factor

    # 主内容区
    if analysis_mode == "🔍 单股分析" and st.session_state.current_stock:
        result = st.session_state.current_stock

        # 股票标题
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;padding:1rem;background:linear-gradient(135deg,#f8f9fa,#e9ecef);border-radius:12px;margin-bottom:1rem;">
            <div>
                <h2 style="margin:0;color:#374151;">{result.get('name', 'N/A')} ({result.get('symbol', 'N/A')})</h2>
                <div style="color:#6b7280;font-size:0.9rem;margin-top:0.3rem;">
                    {result.get('valuation', {}).get('industry_name', '未知行业')} | {result.get('valuation', {}).get('market', '未知市场')}
                </div>
            </div>
            <div style="text-align:right;">
                <span class="info-badge {"badge-growth" if result.get("stock_type")=="growth" else "badge-value" if result.get("stock_type")=="value" else "badge-balanced"}">
                    {"🚀 成长型" if result.get("stock_type")=="growth" else "💰 价值型" if result.get("stock_type")=="value" else "⚖️ 均衡型"}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 标签页（增加 FinGPT 分析标签页）
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📋 综合摘要", "🐟 Fisher分析", "📈 GARP分析", "💰 估值分析", "🤖 AI分析", "🧠 FinGPT分析"])

        with tab1:
            render_summary_tab(result)

        with tab2:
            render_fisher_tab(result)

        with tab3:
            render_garp_tab(result)

        with tab4:
            render_valuation_tab(result)

        with tab5:
            render_ai_tab(result)

        with tab6:
            render_fingpt_tab(result.get('symbol', ''), result.get('name', ''))

        # 导出按钮
        st.markdown("---")
        col_export_left, col_export_right = st.columns([1, 3])
        with col_export_left:
            report_md = generate_report_markdown(result)
            st.markdown(get_download_link(report_md, f"analysis_{result.get('symbol','report')}_{datetime.now().strftime('%Y%m%d')}.md"), unsafe_allow_html=True)

    elif analysis_mode in ["📋 批量分析", "⚖️ 对比分析"]:
        render_batch_results(st.session_state.batch_results)

    else:
        # 欢迎页面 - 增强版
        st.markdown("""
        ### 👋 欢迎使用成长股选股系统

        本系统整合了四种经典的成长股分析方法：

        #### 🐟 Fisher定生成年股分析
        基于《怎样选择成长股》的11维度定性分析框架：
        - **成长性**(30分): 营收CAGR、净利润CAGR、扣非净利润质量
        - **盈利能力**(25分): ROIC、净利率、毛利率稳定性
        - **运营效率**(20分): 存货周转、应收周转、销售费用率
        - **财务质量**(15分): 现金流质量、资产负债率
        - **研发创新**(10分): 研发支出占比

        #### 📈 GARP量化因子分析
        基于8个核心量化指标的质量与动量筛选：
        盈利预测调整、盈余惊喜、销售额增长、营业利润率、自由现金流、盈利增长、盈利动量、ROE

        #### 💰 PEG估值分析（新增）
        - **PEG指标**: PE/Growth，彼得·林奇核心选股工具
        - **行业分类**: 不同行业使用不同合理估值区间
        - **动态权重**: 根据股票类型自动调整各引擎权重

        #### 🧠 FinGPT 智能财报分析（新增）
        - **自动获取**: 财务报表数据
        - **AI 解读**: 基于 Ollama 本地大模型
        - **投资建议**: 综合评分 + 操作建议

        ---
        **操作提示**: 在左侧选择分析模式，输入股票代码开始分析。
        """)


if __name__ == "__main__":
    main()


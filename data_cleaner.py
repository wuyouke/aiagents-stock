#!/usr/bin/env python3
"""
数据清洗模块 - 统一处理财务数据的常见问题
功能：
1. 过滤未来日期和无效数据
2. 区分年报/季报/月报
3. 处理 NaN、Inf、异常值
4. 数据排序和标准化
"""
import logging
from datetime import datetime
from typing import List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FinancialDataCleaner:
    """财务数据清洗器"""

    def __init__(self):
        self.current_year = datetime.now().year

    def clean_financial_df(self, df: pd.DataFrame,
                           date_col: str = '报告日',
                           sort_ascending: bool = False) -> pd.DataFrame:
        """
        清洗财务报表DataFrame

        Args:
            df: 原始财务数据
            date_col: 日期列名
            sort_ascending: 是否升序排列

        Returns:
            清洗后的DataFrame
        """
        if df is None or df.empty:
            return df

        try:
            # 1. 复制避免修改原数据
            cleaned = df.copy()

            # 2. 确保日期列存在
            if date_col not in cleaned.columns:
                logger.warning(f"日期列 {date_col} 不存在")
                return cleaned

            # 3. 转换日期列为字符串格式（便于过滤）
            cleaned[date_col] = cleaned[date_col].astype(str)

            # 4. 过滤无效日期
            cleaned = self._filter_invalid_dates(cleaned, date_col)

            # 5. 排序
            cleaned = cleaned.sort_values(date_col, ascending=sort_ascending).reset_index(drop=True)

            # 6. 清洗数值列中的异常值
            cleaned = self._clean_numeric_columns(cleaned, date_col)

            return cleaned

        except Exception as e:
            logger.warning(f"数据清洗失败: {e}")
            return df

    def _filter_invalid_dates(self, df: pd.DataFrame, date_col: str) -> pd.DataFrame:
        """过滤无效或未来的日期"""
        mask = True

        for idx, row in df.iterrows():
            date_str = str(row[date_col])

            # 检查长度是否合理（8位数字，如20231231）
            if len(date_str) != 8 or not date_str.isdigit():
                mask &= (df.index != idx)
                continue

            try:
                year = int(date_str[:4])

                # 排除未来年份的数据
                if year > self.current_year:
                    mask &= (df.index != idx)
                    continue

                # 排除过早的数据（2000年以前）
                if year < 2000:
                    mask &= (df.index != idx)
                    continue

            except (ValueError, IndexError):
                mask &= (df.index != idx)

        filtered = df[mask]
        if len(filtered) < len(df):
            logger.debug(f"过滤了 {len(df) - len(filtered)} 条无效日期记录")

        return filtered

    def _clean_numeric_columns(self, df: pd.DataFrame, exclude_cols: List[str] = None) -> pd.DataFrame:
        """清洗数值列中的 NaN 和 Inf"""
        if exclude_cols is None:
            exclude_cols = ['报告日', '股票代码', '日期']

        numeric_cols = [col for col in df.columns
                       if col not in exclude_cols
                       and pd.api.types.is_numeric_dtype(df[col])]

        for col in numeric_cols:
            # 将 Inf 替换为 NaN
            df[col] = df[col].replace([np.inf, -np.inf], np.nan)

            # 可选：用前向填充NaN（根据业务需求决定是否启用）
            # df[col] = df[col].fillna(method='ffill')

        return df

    def get_yearly_data(self, df: pd.DataFrame,
                        date_col: str = '报告日',
                        max_years: int = 5,
                        require_complete: bool = False) -> pd.DataFrame:
        """
        获取年报数据（排除季度累计数据）

        Args:
            df: 已清洗的财务数据
            date_col: 日期列名
            max_years: 最大获取年数
            require_complete: 是否要求有完整年度数据

        Returns:
            只包含年报的DataFrame
        """
        if df is None or df.empty:
            return pd.DataFrame()

        try:
            # 筛选年报（报告日以1231结尾）
            yearly_mask = df[date_col].astype(str).str.endswith('1231')
            yearly_df = df[yearly_mask].copy()

            # 排除当前年份及以后（可能是不完整数据）
            valid_mask = yearly_df[date_col].apply(
                lambda x: int(str(x)[:4]) < self.current_year if len(str(x)) >= 4 else False
            )
            yearly_df = yearly_df[valid_mask]

            # 按日期降序排列（最新的在前）
            yearly_df = yearly_df.sort_values(date_col, ascending=False)

            # 限制年数
            if len(yearly_df) > max_years:
                yearly_df = yearly_df.head(max_years)

            return yearly_df.reset_index(drop=True)

        except Exception as e:
            logger.warning(f"获取年报数据失败: {e}")
            return pd.DataFrame()

    def calculate_cagr(self, values: List[float], years: int) -> Optional[float]:
        """
        计算复合年增长率(CAGR)

        Args:
            values: 数值列表（从最新到最旧）
            years: 年数

        Returns:
            CAGR百分比，如果计算失败返回None
        """
        if not values or len(values) < 2 or years <= 0:
            return None

        try:
            latest = values[0]
            oldest = values[-1]

            # 检查有效性
            if latest is None or oldest is None:
                return None
            if isinstance(latest, (int, float)) and isinstance(oldest, (int, float)):
                if oldest <= 0 or latest <= 0:
                    return None

                cagr = (latest / oldest) ** (1 / years) - 1
                cagr_pct = round(cagr * 100, 2)

                # 合理性检查：CAGR绝对值不超过200%
                if abs(cagr_pct) > 200:
                    logger.warning(f"CAGR异常高: {cagr_pct}%")

                return cagr_pct
            else:
                return None

        except (ValueError, TypeError, ZeroDivisionError) as e:
            logger.debug(f"CAGR计算错误: {e}")
            return None

    def safe_divide(self, numerator, denominator, default=None):
        """安全除法，处理各种异常情况"""
        try:
            if numerator is None or denominator is None:
                return default
            num = float(numerator)
            den = float(denominator)
            if den == 0:
                return default
            result = num / den
            # 检查结果有效性
            if np.isinf(result) or np.isnan(result):
                return default
            return round(result, 4)
        except (ValueError, TypeError):
            return default

    def find_column(self, df: pd.DataFrame, keywords: List[str],
                   exclude_keywords: List[str] = None) -> Optional[str]:
        """
        在DataFrame中查找包含关键字的列名

        Args:
            df: 数据框
            keywords: 必须包含的关键字列表
            exclude_keywords: 不能包含的关键字列表

        Returns:
            匹配的列名，未找到返回None
        """
        if df is None or df.empty:
            return None

        for col in df.columns:
            col_str = str(col)

            # 检查必须包含的关键字
            if all(kw in col_str for kw in keywords):
                # 检查排除关键字
                if exclude_keywords:
                    if any(ex_kw in col_str for ex_kw in exclude_keywords):
                        continue
                return col

        return None


# 全局实例
_cleaner_instance = None

def get_cleaner() -> FinancialDataCleaner:
    """获取全局数据清洗器实例"""
    global _cleaner_instance
    if _cleaner_instance is None:
        _cleaner_instance = FinancialDataCleaner()
    return _cleaner_instance


if __name__ == '__main__':
    # 测试数据清洗器
    cleaner = FinancialDataCleaner()

    print("=== 数据清洗模块测试 ===")
    print(f"当前年份: {cleaner.current_year}")

    # 测试CAGR计算
    test_values = [100, 80, 60]  # 假设3年数据
    cagr = cleaner.calculate_cagr(test_values, 2)
    print(f"\nCAGR测试: {test_values} → {cagr}%")

    # 测试安全除法
    print(f"\n安全除法测试:")
    print(f"  100/50 = {cleaner.safe_divide(100, 50)}")
    print(f"  100/0 = {cleaner.safe_divide(100, 0)}")
    print(f"  100/None = {cleaner.safe_divide(100, None)}")


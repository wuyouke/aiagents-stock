#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
低价擒牛选股模块
使用pywencai获取低价高成长股票
"""

import time
from typing import Tuple, Optional

import pandas as pd
import pywencai


class LowPriceBullSelector:
    """低价擒牛选股类"""
    
    def __init__(self):
        self.raw_data = None
        self.selected_stocks = None
    
    def get_low_price_stocks(self, top_n: int = 5) -> Tuple[bool, Optional[pd.DataFrame], str]:
        """
        获取低价高成长股票
        
        选股策略：
        - 股价<10元
        - 净利润增长率≥100%
        - 非ST
        - 非科创板
        - 非创业板
        - 沪深A股
        - 成交额由小至大排名
        
        Args:
            top_n: 返回前N只股票
            
        Returns:
            (success, dataframe, message)
        """
        try:
            print(f"\n{'='*60}")
            print(f"🐂 低价擒牛选股 - 数据获取中")
            print(f"{'='*60}")
            print(f"策略: 股价<10元 + 净利润增长率≥100% + 沪深A股")
            print(f"目标: 筛选前{top_n}只股票")
            
            # 构建查询语句 - 使用多个备选方案，因为复杂查询容易失败
            queries = [
                # 方案1: 完整查询
                (
                    "股价<10元，"
                    "净利润增长率(净利润同比增长率)≥100%，"
                    "非st，"
                    "非科创板，"
                    "非创业板，"
                    "沪深A股，"
                    "成交额由小至大排名"
                ),
                # 方案2: 去掉排序
                (
                    "股价<10元，"
                    "净利润增长率(净利润同比增长率)≥100%，"
                    "非st，"
                    "非科创板，"
                    "非创业板，"
                    "沪深A股"
                ),
                # 方案3: 简化条件
                (
                    "股价<10元，"
                    "净利润增长率≥100%，"
                    "非st，非科创板，非创业板"
                ),
            ]
            
            result = None
            df_result = None
            
            for i, query in enumerate(queries, 1):
                print(f"\n尝试方案 {i}/{len(queries)}...")
                print(f"查询语句: {query[:80]}..." if len(query) > 80 else f"查询语句: {query}")
                print(f"正在调用问财接口...")
            
                try:
                    # 调用pywencai
                    result = pywencai.get(query=query, loop=True, retry=2, sleep=1, log=False)
            
                    if result is None:
                        print(f"  ⚠️ 方案{i}返回None，尝试下一个方案")
                        time.sleep(2)
                        continue
            
                    # 转换为DataFrame
                    df_result = self._convert_to_dataframe(result)

                    if df_result is None or df_result.empty:
                        print(f"  ⚠️ 方案{i}数据为空，尝试下一个方案")
                        time.sleep(2)
                        continue

                    print(f"  ✅ 方案{i}成功！获取到 {len(df_result)} 只股票")
                    break

                except AttributeError as e:
                    print(f"  ⚠️ 方案{i}API响应错误: {str(e)[:50]}")
                    time.sleep(2)
                    continue
                except Exception as e:
                    print(f"  ❌ 方案{i}失败: {str(e)[:80]}")
                    time.sleep(2)
                    continue

            if df_result is None or df_result.empty:
                return False, None, "所有查询方案都失败了，问财接口可能不可用"
            
            print(f"✅ 成功获取 {len(df_result)} 只股票")
            
            # 显示获取到的列名
            print(f"\n获取到的数据字段:")
            for col in df_result.columns[:15]:
                print(f"  - {col}")
            if len(df_result.columns) > 15:
                print(f"  ... 还有 {len(df_result.columns) - 15} 个字段")
            
            # 保存原始数据
            self.raw_data = df_result
            
            # 取前N只
            if len(df_result) > top_n:
                selected = df_result.head(top_n)
                print(f"\n从 {len(df_result)} 只股票中选出前 {top_n} 只")
            else:
                selected = df_result
                print(f"\n共 {len(df_result)} 只符合条件的股票")
            
            self.selected_stocks = selected
            
            # 显示选中的股票
            print(f"\n✅ 选中的股票:")
            for idx, row in selected.iterrows():
                code = row.get('股票代码', 'N/A')
                name = row.get('股票简称', 'N/A')
                price = row.get('股价', row.get('最新价', 'N/A'))
                growth = row.get('净利润增长率', row.get('净利润同比增长率', 'N/A'))
                turnover = row.get('成交额', 'N/A')
                print(f"  {idx+1}. {code} {name} - 股价:{price} 净利增长:{growth}% 成交额:{turnover}")
            
            print(f"{'='*60}\n")
            
            return True, selected, f"成功筛选出{len(selected)}只低价高成长股票"
            
        except Exception as e:
            error_msg = f"获取数据失败: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, None, error_msg
    
    def _convert_to_dataframe(self, result) -> Optional[pd.DataFrame]:
        """将pywencai返回结果转换为DataFrame"""
        try:
            if isinstance(result, pd.DataFrame):
                return result
            elif isinstance(result, dict):
                if 'data' in result:
                    return pd.DataFrame(result['data'])
                elif 'result' in result:
                    return pd.DataFrame(result['result'])
                else:
                    return pd.DataFrame(result)
            elif isinstance(result, list):
                return pd.DataFrame(result)
            else:
                print(f"⚠️ 未知的数据格式: {type(result)}")
                return None
        except Exception as e:
            print(f"转换DataFrame失败: {e}")
            return None
    
    def get_stock_codes(self) -> list:
        """
        获取选中股票的代码列表（去掉市场后缀）
        
        Returns:
            股票代码列表
        """
        if self.selected_stocks is None or self.selected_stocks.empty:
            return []
        
        codes = []
        for code in self.selected_stocks['股票代码'].tolist():
            if isinstance(code, str):
                # 去掉 .SZ 等后缀
                clean_code = code.split('.')[0] if '.' in code else code
                codes.append(clean_code)
            else:
                codes.append(str(code))
        
        return codes

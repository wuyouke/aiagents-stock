#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 pywencai 修复是否有效
"""

import os
os.environ['NODE_NO_WARNINGS'] = '1'

from main_force_selector import MainForceStockSelector

print("\n" + "="*60)
print("测试 pywencai 修复")
print("="*60 + "\n")

try:
    selector = MainForceStockSelector()

    # 测试获取主力资金净流入股票
    print("正在测试主力选股功能...")
    success, df, message = selector.get_main_force_stocks(
        days_ago=7,
        min_market_cap=50.0,
        max_market_cap=5000.0
    )

    if success:
        print(f"\n✅ 成功！{message}")
        print(f"返回的股票数: {len(df)}")
        print(f"列名: {list(df.columns)[:10]}")
        print("\n✅ pywencai 修复验证成功！")
    else:
        print(f"\n❌ 失败：{message}")
        print("⚠️ 可能是网络问题或问财 API 不可用")

except Exception as e:
    print(f"\n❌ 错误: {str(e)}")
    import traceback
    traceback.print_exc()


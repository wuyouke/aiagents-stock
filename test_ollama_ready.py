#!/usr/bin/env python3
"""
测试 Ollama 是否准备好
"""

import sys

import requests

print("=" * 60)
print("🔍 Ollama 就绪检查")
print("=" * 60)

# 1. 检查 Ollama 服务
print("\n1️⃣ 检查 Ollama 服务...")
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=2)
    if response.status_code == 200:
        print("   ✅ Ollama 服务运行中")
        data = response.json()
        models = data.get("models", [])
        if models:
            print(f"   ✅ 已安装模型: {len(models)} 个")
            for model in models:
                name = model.get("name", "unknown")
                size = model.get("size", 0) / 1e9  # 转换为 GB
                print(f"      • {name} ({size:.1f}GB)")
        else:
            print("   ⚠️ 没有安装任何模型")
            print("   请运行: ollama pull llama2")
            sys.exit(1)
    else:
        print(f"   ❌ Ollama 返回错误: {response.status_code}")
        sys.exit(1)
except requests.exceptions.ConnectionError:
    print("   ❌ Ollama 服务未运行")
    print("   请运行: ollama serve")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ 错误: {e}")
    sys.exit(1)

# 2. 测试 API 调用
print("\n2️⃣ 测试 API 调用...")
try:
    import openai
    client = openai.OpenAI(
        api_key="not-needed",
        base_url="http://localhost:11434/v1"
    )

    response = client.chat.completions.create(
        model="llama2",
        messages=[{"role": "user", "content": "你好"}],
        max_tokens=50
    )

    print("   ✅ API 调用成功")
    print(f"   响应: {response.choices[0].message.content[:50]}...")

except Exception as e:
    print(f"   ❌ API 调用失败: {e}")
    sys.exit(1)

# 3. 检查 .env 配置
print("\n3️⃣ 检查 .env 配置...")
try:
    import os
    from dotenv import load_dotenv
    load_dotenv()

    llm_provider = os.getenv("LLM_PROVIDER", "").strip()
    if llm_provider == "ollama":
        print(f"   ✅ LLM_PROVIDER = ollama")
    else:
        print(f"   ⚠️ LLM_PROVIDER = {llm_provider} （应该是 ollama）")
        print("   请在 .env 中修改: LLM_PROVIDER=ollama")

except Exception as e:
    print(f"   ⚠️ 无法检查 .env: {e}")

# 4. 总结
print("\n" + "=" * 60)
print("✅ 一切就绪！")
print("=" * 60)
print("\n现在可以运行应用了：")
print("  streamlit run app.py")
print("\n或使用自动启动脚本：")
print("  bash start_ollama_app.sh")
print("\n" + "=" * 60)


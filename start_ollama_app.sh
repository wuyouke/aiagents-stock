#!/bin/bash

# 启动 Ollama 和应用的一键脚本

echo "=========================================="
echo "🚀 启动 Ollama + AI 股票分析系统"
echo "=========================================="
echo ""

# 1. 启动 Ollama 服务
echo "1️⃣ 启动 Ollama 服务..."
ollama serve > /tmp/ollama.log 2>&1 &
OLLAMA_PID=$!
echo "   ✅ Ollama 进程 ID: $OLLAMA_PID"
echo "   （日志: /tmp/ollama.log）"
echo ""

# 等待 Ollama 启动
echo "2️⃣ 等待 Ollama 启动..."
sleep 3

# 检查 Ollama 是否运行
for i in {1..10}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "   ✅ Ollama 已启动"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "   ❌ Ollama 启动超时"
        exit 1
    fi
    echo "   ⏳ 等待中... ($i/10)"
    sleep 1
done

echo ""
echo "3️⃣ 启动应用..."
echo "   运行: streamlit run app.py"
echo ""
echo "=========================================="
echo "✅ 一切就绪！"
echo "=========================================="
echo ""
echo "📌 应用将在 http://localhost:8501 打开"
echo "📌 Ollama 在后台运行"
echo "📌 要停止，按 Ctrl+C"
echo ""

# 启动应用
streamlit run app.py

# 清理
echo ""
echo "清理中..."
kill $OLLAMA_PID 2>/dev/null
echo "✅ Ollama 已关闭"


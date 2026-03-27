#!/bin/bash

# Ollama 快速配置脚本（macOS）

echo "=========================================="
echo "🚀 Ollama 快速配置脚本"
echo "=========================================="

# 检查是否安装了 Ollama
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama 未安装"
    echo ""
    echo "📥 正在安装 Ollama..."

    # 尝试使用 brew 安装
    if command -v brew &> /dev/null; then
        echo "使用 Homebrew 安装 Ollama..."
        brew install ollama
    else
        echo "❌ 未找到 Homebrew"
        echo ""
        echo "请手动下载安装："
        echo "访问 https://ollama.ai 下载 macOS 版本"
        exit 1
    fi
else
    echo "✅ Ollama 已安装"
fi

echo ""
echo "=========================================="
echo "📦 下载模型"
echo "=========================================="

# 检查是否已安装模型
echo ""
echo "拉取 llama2 模型（~4GB，首次需要几分钟）..."
echo "如果已安装，此步骤会很快完成"

ollama pull llama2

echo ""
echo "✅ 模型下载完成"

echo ""
echo "=========================================="
echo "⚙️ 配置 .env 文件"
echo "=========================================="

# 创建 .env 文件备份
if [ -f ".env" ]; then
    cp .env .env.backup
    echo "✅ 已备份当前 .env 文件为 .env.backup"
fi

# 更新 .env 文件
echo ""
echo "修改 LLM_PROVIDER 配置..."

# 使用 sed 命令更新配置（支持 macOS）
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' 's/^LLM_PROVIDER=.*/LLM_PROVIDER=ollama/' .env
    sed -i '' 's/^OLLAMA_BASE_URL=.*/OLLAMA_BASE_URL=http:\/\/localhost:11434\/v1/' .env
    sed -i '' 's/^OLLAMA_MODEL=.*/OLLAMA_MODEL=llama2/' .env
else
    # Linux
    sed -i 's/^LLM_PROVIDER=.*/LLM_PROVIDER=ollama/' .env
    sed -i 's/^OLLAMA_BASE_URL=.*/OLLAMA_BASE_URL=http:\/\/localhost:11434\/v1/' .env
    sed -i 's/^OLLAMA_MODEL=.*/OLLAMA_MODEL=llama2/' .env
fi

echo "✅ .env 文件已更新"

echo ""
echo "=========================================="
echo "🎉 配置完成！"
echo "=========================================="

echo ""
echo "📝 后续步骤："
echo ""
echo "1️⃣ 启动 Ollama 服务（在新终端中）"
echo "   $ ollama serve"
echo ""
echo "2️⃣ 启动应用程序"
echo "   $ streamlit run app.py"
echo ""
echo "3️⃣ 打开浏览器访问应用"
echo "   http://localhost:8501"
echo ""
echo "✅ 现在就可以使用 AI 分析师功能了！"
echo ""


import os

from dotenv import load_dotenv

# 加载环境变量（override=True 强制覆盖已存在的环境变量）
load_dotenv(override=True)

# ========== LLM API 配置 ==========
# 优先级：LLM_PROVIDER > DEEPSEEK_API_KEY
# 支持的提供商：deepseek, ollama, openai, qwen, claude, custom

# LLM 提供商选择
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")

# DeepSeek API配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# Ollama 本地模型配置（需要本地运行 Ollama）
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")

# OpenAI API配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# 阿里云 Qwen API配置
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")

# 自定义 API 配置（通用 OpenAI 兼容 API）
CUSTOM_API_KEY = os.getenv("CUSTOM_API_KEY", "")
CUSTOM_BASE_URL = os.getenv("CUSTOM_BASE_URL", "")
CUSTOM_MODEL = os.getenv("CUSTOM_MODEL", "")

# 默认AI模型名称
DEFAULT_MODEL_NAME = os.getenv("DEFAULT_MODEL_NAME", "deepseek-chat")

# 其他配置
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")

# 股票数据源配置
DEFAULT_PERIOD = "1y"  # 默认获取1年数据
DEFAULT_INTERVAL = "1d"  # 默认日线数据

# MiniQMT量化交易配置
MINIQMT_CONFIG = {
    'enabled': os.getenv("MINIQMT_ENABLED", "false").lower() == "true",
    'account_id': os.getenv("MINIQMT_ACCOUNT_ID", ""),
    'host': os.getenv("MINIQMT_HOST", "127.0.0.1"),
    'port': int(os.getenv("MINIQMT_PORT", "58610")),
}

# TDX股票数据API配置项目地址github.com/oficcejo/tdx-api
TDX_CONFIG = {
    'enabled': os.getenv("TDX_ENABLED", "false").lower() == "true",
    'base_url': os.getenv("TDX_BASE_URL", "http://192.168.1.222:8181"),
}
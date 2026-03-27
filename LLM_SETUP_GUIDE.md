# LLM API 配置指南

本项目支持多个 LLM 提供商。根据你的需求选择合适的配置方案。

## 🚀 快速开始

### 方案 1: 使用本地 Ollama（推荐 - 完全免费）

**优点**：完全免费，无需 API Key，离线运行

**步骤**：

1. **安装 Ollama**
   ```bash
   # macOS
   brew install ollama

   # 或访问 https://ollama.ai 下载
   ```

2. **启动 Ollama 服务**
   ```bash
   ollama serve
   ```

3. **拉取模型**（另外一个终端）
   ```bash
   # 选择一个模型（任选其一）
   ollama pull llama2        # ~4GB
   ollama pull mistral       # ~5GB
   ollama pull neural-chat   # ~4GB
   ```

4. **修改 `.env` 文件**
   ```
   LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434/v1
   OLLAMA_MODEL=llama2
   ```

5. **重启应用**
   ```bash
   streamlit run app.py
   ```

---

### 方案 2: 使用阿里云 Qwen（便宜 - 按量付费）

**优点**：成本低，响应快，支持中文

**步骤**：

1. **注册阿里云账户**
   - 访问 https://dashscope.aliyun.com/
   - 注册并登录

2. **获取 API Key**
   - 复制你的 API Key

3. **修改 `.env` 文件**
   ```
   LLM_PROVIDER=qwen
   QWEN_API_KEY=your_api_key
   QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
   QWEN_MODEL=qwen-plus
   ```

4. **重启应用**

---

### 方案 3: 使用 DeepSeek（已配置）

如果你有 DeepSeek 账户余额，直接使用默认配置即可：

```
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_key
```

---

### 方案 4: 使用 OpenAI（高质量但昂贵）

**步骤**：

1. **获取 OpenAI API Key**
   - 访问 https://platform.openai.com/api-keys
   - 创建新 API Key

2. **修改 `.env` 文件**
   ```
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your_api_key
   OPENAI_MODEL=gpt-3.5-turbo
   ```

3. **重启应用**

---

### 方案 5: 自定义 API（其他兼容服务）

如果你有其他 OpenAI 兼容的 API 服务：

```
LLM_PROVIDER=custom
CUSTOM_API_KEY=your_api_key
CUSTOM_BASE_URL=https://your-api-endpoint.com/v1
CUSTOM_MODEL=your-model-name
```

---

## 📊 对比表

| 方案 | 成本 | 速度 | 质量 | 离线 | 推荐度 |
|------|------|------|------|------|--------|
| Ollama | ✅ 免费 | 慢 | 一般 | ✅ 是 | ⭐⭐⭐⭐⭐ |
| Qwen | 💰 便宜 | 快 | 好 | ❌ 否 | ⭐⭐⭐⭐ |
| DeepSeek | 💰 便宜 | 快 | 很好 | ❌ 否 | ⭐⭐⭐⭐ |
| OpenAI | 💸 贵 | 快 | 最好 | ❌ 否 | ⭐⭐⭐ |

---

## 🔧 故障排除

### Ollama 连接失败

```bash
# 1. 确认 Ollama 正在运行
curl http://localhost:11434/api/tags

# 2. 如果返回 404，需要启动 Ollama
ollama serve

# 3. 检查防火墙设置
```

### API Key 无效

- 复制 API Key 时注意不要包含空格
- 检查 API Key 是否过期
- 尝试生成新的 API Key

### 模型不存在

```bash
# 查看已安装的模型
ollama list

# 拉取新模型
ollama pull <model_name>
```

---

## 💡 建议

1. **个人使用**：推荐使用 Ollama（免费，离线）
2. **生产环境**：推荐使用 Qwen 或 DeepSeek（成本低，稳定）
3. **高质量需求**：使用 OpenAI（但成本较高）

---

## 🆘 需要帮助？

- 查看控制台输出了解详细错误信息
- 确认网络连接正常
- 检查 API Key 是否正确
- 检查 `.env` 文件格式是否正确

---

**最后更新**: 2026-03-27


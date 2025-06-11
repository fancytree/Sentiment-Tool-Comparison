# Render.com 部署说明

## 内存优化措施

为了在 render.com 的 512MB 内存限制下成功部署，我们进行了以下优化：

### 1. 模型优化
- 使用轻量级的 `distilbert-base-uncased-finetuned-sst-2-english` 模型替代重型的 RoBERTa 模型
- 实现延迟加载，只在需要时才加载模型
- 添加基于规则的后备情感分析方案

### 2. 依赖优化
- 移除了 `torch` 和 `scikit-learn` 等重型依赖
- 使用兼容的 `httpx==0.24.1` 版本
- 简化了 transformers 的使用

### 3. 应用优化
- 减少工作进程数量到 1 个
- 移除复杂的方面分析功能
- 使用 Gunicorn 配置优化内存使用

## 部署步骤

1. **环境变量设置**
   在 render.com 控制台中设置以下环境变量：
   ```
   OPENAI_API_KEY=your-openai-api-key
   ENV=production
   FRONTEND_URL=https://your-frontend-domain.onrender.com
   ```

2. **启动命令**
   在 render.com 的 Build & Deploy 设置中使用：
   ```
   Start Command: ./start.sh
   ```
   或者直接使用：
   ```
   Start Command: gunicorn -c gunicorn.conf.py main:app
   ```

3. **构建命令**
   ```
   Build Command: pip install -r requirements.txt
   ```

## 内存监控

如果仍然遇到内存问题，可以考虑：

1. **进一步简化模型**
   - 完全使用基于规则的情感分析
   - 移除 transformers 依赖

2. **升级 render.com 计划**
   - 升级到更高内存的计划（1GB 或更多）

## 故障排除

如果部署失败：
1. 检查日志中的具体错误信息
2. 确认所有环境变量已正确设置
3. 验证 requirements.txt 中的依赖版本
4. 考虑进一步减少功能以降低内存使用 
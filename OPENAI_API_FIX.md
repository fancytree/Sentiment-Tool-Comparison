# 🔧 OpenAI API 密钥修复指南

## ✅ 测试结果

您的 OpenAI API 密钥已通过本地测试：
- **密钥格式**: ✅ 正确 (sk-proj-...mIUA)
- **密钥长度**: ✅ 164 字符
- **API 调用**: ✅ 成功响应

## 🎯 问题定位

API 密钥在本地工作正常，问题出现在 render.com 部署环境中。

## 🔧 修复步骤

### 步骤 1: 在 render.com 设置环境变量

1. **登录 render.com**
   - 访问 https://render.com
   - 登录您的账户

2. **进入后端服务**
   - 找到您的后端服务（例如：`sentiment-tool-comparison-1`）
   - 点击进入服务详情页面

3. **设置环境变量**
   - 点击左侧菜单的 **"Environment"** 标签
   - 点击 **"Add Environment Variable"** 按钮
   - 添加以下环境变量：

   ```
   Key: OPENAI_API_KEY
   Value: your-openai-api-key-here
   ```

   **⚠️ 重要提示**：
   - 确保 Key 名称完全正确：`OPENAI_API_KEY`
   - 确保 Value 完整复制，没有多余的空格或换行
   - 不要在密钥前后添加引号

4. **保存并重新部署**
   - 点击 **"Save Changes"** 按钮
   - render.com 会自动触发重新部署

### 步骤 2: 验证环境变量设置

重新部署完成后，测试 API：

```bash
# 测试 LLM 情感分析 API
curl -X POST https://your-backend-url.onrender.com/api/llm-sentiment/ \
  -H "Content-Type: application/json" \
  -d '{"text":"This is an amazing product!"}'
```

**预期响应**：
```json
{
  "sentiment": "positive",
  "score": 4.5,
  "polarity": 0.9,
  "brief_analysis": "Positive review expressing satisfaction with product quality",
  "aspects": []
}
```

### 步骤 3: 检查部署日志

如果仍有问题，检查 render.com 的部署日志：

1. 在服务详情页面，点击 **"Logs"** 标签
2. 查看最新的部署日志
3. 寻找以下信息：
   - `OPENAI_API_KEY environment variable is not set` - 表示环境变量未设置
   - `401` 或 `invalid_api_key` - 表示密钥问题
   - 其他错误信息

## 🔍 故障排除

### 问题 1: 环境变量未生效

**症状**: 仍然显示 "OPENAI_API_KEY environment variable is not set"

**解决方案**:
1. 确认环境变量名称拼写正确：`OPENAI_API_KEY`
2. 确认已点击 "Save Changes"
3. 等待重新部署完成（通常需要 3-5 分钟）
4. 检查服务状态是否为 "Live"

### 问题 2: API 密钥仍然无效

**症状**: 仍然显示 401 错误

**解决方案**:
1. 重新复制 API 密钥，确保没有遗漏字符
2. 检查 OpenAI 账户余额是否充足
3. 确认 API 密钥权限设置正确

### 问题 3: 部署失败

**症状**: 服务无法启动

**解决方案**:
1. 检查 render.com 日志中的具体错误信息
2. 确认所有依赖都已正确安装
3. 检查内存使用是否超出限制

## 📋 完整的环境变量配置

在 render.com 后端服务中设置以下环境变量：

```
OPENAI_API_KEY=your-openai-api-key-here
ENV=production
FRONTEND_URL=https://your-frontend-domain.onrender.com
```

## 🎉 验证成功

配置完成后，您应该能够：
- ✅ 使用 LLM 情感分析功能
- ✅ 上传文件进行批量分析
- ✅ 使用聊天功能
- ✅ 获得详细的情感分析结果

## 📞 需要帮助？

如果按照以上步骤仍有问题，请提供：
1. render.com 的部署日志截图
2. API 测试的具体错误信息
3. 环境变量设置的截图

我会帮您进一步诊断和解决问题！ 
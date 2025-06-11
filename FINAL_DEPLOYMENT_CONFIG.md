# 🎯 最终部署配置

## 你的服务 URL

- **前端**: https://sentiment-tool-comparison.onrender.com/
- **后端**: https://sentiment-tool-comparison-1.onrender.com

## ✅ 后端状态检查

- **根端点**: ✅ 正常 - 返回 `{"message":"Welcome to the API"}`
- **健康检查**: ✅ 正常 - 返回 `{"status":"healthy"}`
- **API 测试**: ✅ 正常 - Transformer API 返回情感分析结果

## 🔧 需要配置的环境变量

### 前端服务环境变量

在 render.com 前端服务设置中添加：

```
VITE_API_URL=https://sentiment-tool-comparison-1.onrender.com
```

**配置步骤**：
1. 登录 render.com
2. 进入前端服务 `sentiment-tool-comparison`
3. 点击 "Environment" 标签
4. 添加环境变量：
   - Key: `VITE_API_URL`
   - Value: `https://sentiment-tool-comparison-1.onrender.com`
5. 点击 "Save Changes"
6. 服务会自动重新部署

### 后端服务环境变量

在 render.com 后端服务设置中添加：

```
FRONTEND_URL=https://sentiment-tool-comparison.onrender.com
```

**配置步骤**：
1. 进入后端服务 `sentiment-tool-comparison-1`
2. 点击 "Environment" 标签
3. 添加环境变量：
   - Key: `FRONTEND_URL`
   - Value: `https://sentiment-tool-comparison.onrender.com`
4. 确保已有其他必要环境变量：
   - `ENV=production`
   - `OPENAI_API_KEY=your-openai-api-key`
5. 点击 "Save Changes"
6. 服务会自动重新部署

## 🔍 验证连接

配置完成后，请验证以下功能：

### 1. 前端访问
访问：https://sentiment-tool-comparison.onrender.com/
- [ ] 页面正常加载
- [ ] 没有 CORS 错误（检查浏览器控制台）
- [ ] 页面样式正常显示

### 2. API 连接测试
在前端页面测试：
- [ ] **Transformer 情感分析**：输入文本 "This is amazing!" 并点击分析
- [ ] **LLM 情感分析**：输入文本进行分析（需要 OpenAI API Key）
- [ ] **通用分析**：测试文本分析功能

### 3. 文件上传测试
- [ ] 上传 CSV 文件进行批量分析
- [ ] 下载分析结果文件

### 4. 聊天功能测试
- [ ] 在 LLM 页面测试聊天功能

## 🐛 故障排除

### 如果前端无法连接后端：

1. **检查环境变量**：
   - 确认 `VITE_API_URL` 设置正确
   - 重新部署前端服务

2. **检查 CORS 设置**：
   - 确认后端 `FRONTEND_URL` 设置正确
   - 重新部署后端服务

3. **检查网络请求**：
   - 打开浏览器开发者工具
   - 查看 Network 标签页的请求状态
   - 查看 Console 标签页的错误信息

### 常见错误及解决方案：

#### CORS 错误
```
Access to fetch at 'https://sentiment-tool-comparison-1.onrender.com/api/...' 
from origin 'https://sentiment-tool-comparison.onrender.com' has been blocked by CORS policy
```
**解决**：确认后端 `FRONTEND_URL` 环境变量正确设置

#### API 调用失败
```
Failed to fetch
```
**解决**：确认前端 `VITE_API_URL` 环境变量正确设置

## 📱 测试用例

### 快速测试脚本

你可以在浏览器控制台运行以下代码来测试 API 连接：

```javascript
// 测试 Transformer API
fetch('/api/transformer-sentiment/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: 'This is a wonderful day!' })
})
.then(res => res.json())
.then(data => console.log('Transformer API:', data))
.catch(err => console.error('Error:', err));

// 测试健康检查
fetch('/health')
.then(res => res.json())
.then(data => console.log('Health check:', data))
.catch(err => console.error('Error:', err));
```

## 🎉 配置完成检查清单

- [ ] 前端环境变量 `VITE_API_URL` 已设置
- [ ] 后端环境变量 `FRONTEND_URL` 已设置
- [ ] 后端环境变量 `ENV=production` 已设置
- [ ] 后端环境变量 `OPENAI_API_KEY` 已设置（如需 LLM 功能）
- [ ] 两个服务都已重新部署
- [ ] 前端页面可以正常访问
- [ ] API 调用正常工作
- [ ] 文件上传功能正常
- [ ] 没有 CORS 错误

完成以上配置后，你的情感分析工具就完全连接并可以正常使用了！🚀 
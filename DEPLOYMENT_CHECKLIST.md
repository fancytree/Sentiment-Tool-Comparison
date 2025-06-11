# 🚀 Render.com 部署检查清单

## ✅ 前端和后端连接配置完成

### 已完成的配置

#### 1. 前端 API 配置 ✅
- [x] 创建了 `ai-demo-frontend/src/config/api.ts` 配置文件
- [x] 自动检测开发/生产环境
- [x] 开发环境：自动使用 `http://localhost:8001`
- [x] 生产环境：使用相对路径或环境变量 `VITE_API_URL`
- [x] 更新了所有页面的 API 调用：
  - [x] LLMSentiment.tsx
  - [x] TransformerSentiment.tsx  
  - [x] GeneralAnalysis.tsx

#### 2. 后端 CORS 配置 ✅
- [x] 支持开发环境：`localhost:5173`, `localhost:3000`
- [x] 支持生产环境：`*.onrender.com` 域名
- [x] 支持自定义域名：通过 `FRONTEND_URL` 环境变量
- [x] 灵活的域名配置系统

#### 3. 环境变量配置 ✅
- [x] 后端支持 `ENV`, `FRONTEND_URL`, `OPENAI_API_KEY`
- [x] 前端支持 `VITE_API_URL`

## 📋 部署步骤

### 第一步：部署后端
1. 在 render.com 创建 **Web Service**
2. 连接 GitHub 仓库
3. 设置配置：
   ```
   Name: sentiment-api (或你喜欢的名称)
   Root Directory: backend
   Build Command: pip install -r requirements.txt
   Start Command: ./start.sh
   ```
4. 设置环境变量：
   ```
   OPENAI_API_KEY=your-openai-api-key
   ENV=production
   ```
5. 点击 **Deploy**
6. 等待部署完成，记录后端 URL（例如：`https://sentiment-api.onrender.com`）

### 第二步：部署前端
1. 在 render.com 创建 **Static Site**
2. 连接 GitHub 仓库
3. 设置配置：
   ```
   Name: sentiment-app (或你喜欢的名称)
   Root Directory: ai-demo-frontend
   Build Command: npm install && npm run build
   Publish Directory: dist
   ```
4. 设置环境变量：
   ```
   VITE_API_URL=https://sentiment-api.onrender.com
   ```
   （使用第一步记录的后端 URL）
5. 点击 **Deploy**
6. 等待部署完成，记录前端 URL（例如：`https://sentiment-app.onrender.com`）

### 第三步：更新后端 CORS
1. 回到后端服务设置
2. 添加环境变量：
   ```
   FRONTEND_URL=https://sentiment-app.onrender.com
   ```
   （使用第二步记录的前端 URL）
3. 重新部署后端服务

## 🔍 验证部署

### 1. 后端健康检查
访问：`https://your-backend-url/health`
应该返回：`{"status":"healthy"}`

### 2. 前端访问测试
访问前端 URL，检查：
- [x] 页面正常加载
- [x] 没有 CORS 错误（检查浏览器控制台）
- [x] API 调用正常工作

### 3. 功能测试
- [x] LLM 情感分析：输入文本，点击分析
- [x] Transformer 情感分析：输入文本，点击分析  
- [x] 文件上传：上传 CSV 文件进行批量分析
- [x] 聊天功能：在 LLM 页面测试聊天
- [x] 文件下载：下载分析结果

## 🐛 故障排除

### 常见问题

#### 1. CORS 错误
**症状**：浏览器控制台显示 CORS 错误
**解决**：
- 检查后端 `FRONTEND_URL` 环境变量是否正确
- 确认前端和后端 URL 匹配
- 重新部署后端服务

#### 2. API 调用失败
**症状**：前端无法连接到后端
**解决**：
- 检查前端 `VITE_API_URL` 环境变量
- 测试后端健康检查端点
- 检查网络请求状态码

#### 3. 环境变量未生效
**症状**：配置没有按预期工作
**解决**：
- 确认环境变量名称正确
- 重新部署服务使环境变量生效
- 检查构建日志

### 调试工具
1. **浏览器开发者工具**：
   - Console：查看错误信息
   - Network：查看 API 请求状态
   
2. **Render.com 日志**：
   - 查看构建日志
   - 查看运行时日志

## 📝 配置模板

### 后端环境变量
```
OPENAI_API_KEY=sk-your-openai-api-key
ENV=production
FRONTEND_URL=https://your-frontend-domain.onrender.com
```

### 前端环境变量
```
VITE_API_URL=https://your-backend-domain.onrender.com
```

## 🎉 部署完成

当所有检查项都通过后，你的情感分析工具就成功部署并连接了！

- 前端：用户界面和交互
- 后端：API 服务和数据处理
- 连接：CORS 和环境变量配置

现在用户可以通过前端 URL 访问完整的情感分析工具了。 
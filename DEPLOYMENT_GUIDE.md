# 前后端连接部署指南

## 🔗 前后端连接配置

### 1. 后端部署 (render.com)

#### 环境变量设置
在 render.com 后端服务的环境变量中设置：

```
OPENAI_API_KEY=your-openai-api-key
ENV=production
FRONTEND_URL=https://your-frontend-domain.onrender.com
```

#### 启动命令
```
Start Command: ./start.sh
Build Command: pip install -r requirements.txt
```

### 2. 前端部署 (render.com)

#### 环境变量设置
在 render.com 前端服务的环境变量中设置：

```
VITE_API_URL=https://your-backend-domain.onrender.com
```

#### 构建命令
```
Build Command: npm install && npm run build
Start Command: npm run preview
```

### 3. 域名配置

假设你的服务域名如下：
- 后端：`https://sentiment-api.onrender.com`
- 前端：`https://sentiment-app.onrender.com`

#### 后端环境变量
```
FRONTEND_URL=https://sentiment-app.onrender.com
```

#### 前端环境变量
```
VITE_API_URL=https://sentiment-api.onrender.com
```

### 4. API 端点自动配置

前端代码已经配置为：
- **开发环境**：自动使用 `http://localhost:8001`
- **生产环境**：使用环境变量 `VITE_API_URL` 或相对路径

### 5. CORS 配置

后端已配置支持：
- 开发环境：`localhost:5173`, `localhost:3000`
- 生产环境：所有 `*.onrender.com` 域名
- 自定义域名：通过 `FRONTEND_URL` 环境变量

### 6. 部署步骤

1. **部署后端**：
   - 在 render.com 创建 Web Service
   - 连接到你的 GitHub 仓库
   - 设置根目录为 `backend`
   - 配置环境变量
   - 部署

2. **获取后端 URL**：
   - 部署完成后，复制后端服务的 URL
   - 例如：`https://sentiment-api.onrender.com`

3. **部署前端**：
   - 在 render.com 创建 Static Site
   - 连接到你的 GitHub 仓库
   - 设置根目录为 `ai-demo-frontend`
   - 设置环境变量 `VITE_API_URL` 为后端 URL
   - 部署

4. **更新后端配置**：
   - 获取前端 URL 后，更新后端的 `FRONTEND_URL` 环境变量
   - 重新部署后端服务

### 7. 验证连接

部署完成后，访问前端 URL 并测试：
- 健康检查：前端应该能够连接到后端
- API 调用：情感分析功能应该正常工作
- 文件上传：批量分析功能应该正常工作

### 8. 故障排除

如果遇到连接问题：

1. **检查 CORS 错误**：
   - 确认后端 `FRONTEND_URL` 设置正确
   - 检查浏览器控制台的 CORS 错误

2. **检查 API 端点**：
   - 确认前端 `VITE_API_URL` 设置正确
   - 测试后端健康检查：`https://your-backend-url/health`

3. **检查网络请求**：
   - 打开浏览器开发者工具
   - 查看 Network 标签页的请求状态

### 9. 本地开发

本地开发时：
- 后端：`cd backend && python main.py`
- 前端：`cd ai-demo-frontend && npm run dev`
- 前端会自动连接到 `http://localhost:8001`

### 10. 环境变量模板

#### 后端 (.env)
```
OPENAI_API_KEY=sk-...
ENV=production
FRONTEND_URL=https://your-frontend-domain.onrender.com
```

#### 前端 (.env.production)
```
VITE_API_URL=https://your-backend-domain.onrender.com
``` 
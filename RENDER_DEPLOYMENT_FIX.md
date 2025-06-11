# 🔧 Render.com 部署问题修复指南

## 问题：Vite "host not allowed" 错误

### 错误信息
```
Blocked request. This host ("sentiment-tool-comparison.onrender.com") is not allowed.
To allow this host, add "sentiment-tool-comparison.onrender.com" to `preview.allowedHosts` in vite.config.js.
```

### ✅ 已修复的配置

#### 1. 更新了 `vite.config.ts`
添加了 `preview` 配置来允许 render.com 域名：

```typescript
preview: {
  port: 4173,
  host: true,
  // 允许所有 render.com 的域名访问
  allowedHosts: [
    'localhost',
    '127.0.0.1',
    '.onrender.com',
    'sentiment-tool-comparison.onrender.com',
    // 添加其他可能的域名
    '.render.com',
  ],
},
```

#### 2. 创建了 `render.yaml` 配置文件
为 render.com 提供了专门的部署配置。

### 🚀 部署步骤（更新版）

#### 方法一：使用 Web Service（推荐）

1. **创建 Web Service**（不是 Static Site）
2. **设置配置**：
   ```
   Name: sentiment-frontend
   Root Directory: ai-demo-frontend
   Build Command: npm install && npm run build
   Start Command: npm run preview -- --host 0.0.0.0 --port $PORT
   ```
3. **环境变量**：
   ```
   VITE_API_URL=https://your-backend-domain.onrender.com
   PORT=10000
   ```

#### 方法二：使用 Static Site + 自定义配置

1. **创建 Static Site**
2. **设置配置**：
   ```
   Name: sentiment-frontend
   Root Directory: ai-demo-frontend
   Build Command: npm install && npm run build
   Publish Directory: dist
   ```
3. **环境变量**：
   ```
   VITE_API_URL=https://your-backend-domain.onrender.com
   ```

### 📝 package.json 脚本更新

确保 `package.json` 中有正确的 preview 脚本：

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "preview:host": "vite preview --host 0.0.0.0"
  }
}
```

### 🔍 验证修复

1. **本地测试**：
   ```bash
   npm run build
   npm run preview
   ```
   访问 `http://localhost:4173` 应该正常工作

2. **生产环境测试**：
   - 部署后访问你的 render.com URL
   - 检查浏览器控制台是否还有 "host not allowed" 错误
   - 测试 API 调用是否正常

### 🐛 如果仍有问题

#### 选项 1：添加你的具体域名
在 `vite.config.ts` 的 `allowedHosts` 中添加你的确切域名：

```typescript
allowedHosts: [
  'localhost',
  '127.0.0.1',
  '.onrender.com',
  'your-exact-domain.onrender.com', // 添加你的确切域名
  '.render.com',
],
```

#### 选项 2：使用通配符（不推荐用于生产）
```typescript
allowedHosts: 'all', // 允许所有主机（仅用于调试）
```

#### 选项 3：使用环境变量
```typescript
allowedHosts: process.env.ALLOWED_HOSTS?.split(',') || [
  'localhost',
  '127.0.0.1',
  '.onrender.com',
],
```

然后在 render.com 设置环境变量：
```
ALLOWED_HOSTS=localhost,127.0.0.1,.onrender.com,your-domain.onrender.com
```

### 📋 完整的 render.com 配置

#### 前端服务配置
```
Service Type: Web Service
Name: sentiment-frontend
Root Directory: ai-demo-frontend
Build Command: npm install && npm run build
Start Command: npm run preview -- --host 0.0.0.0 --port $PORT

Environment Variables:
VITE_API_URL=https://your-backend-domain.onrender.com
PORT=10000
```

#### 后端服务配置
```
Service Type: Web Service
Name: sentiment-backend
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: ./start.sh

Environment Variables:
OPENAI_API_KEY=your-openai-api-key
ENV=production
FRONTEND_URL=https://your-frontend-domain.onrender.com
```

### ✅ 修复完成

现在你的前端应该可以在 render.com 上正常运行，不会再出现 "host not allowed" 错误了！ 
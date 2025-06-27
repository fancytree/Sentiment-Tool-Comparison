# AI.meichai.net

这是一个基于 React + Radix Themes 前端和 Python FastAPI 后端的全栈项目。

## 项目结构

```
/ai.meichai.net/
├── frontend/               # React + Radix Themes
│   ├── public/
│   ├── src/
│   │   ├── components/     # 通用组件（按钮、卡片等）
│   │   ├── pages/         # 每个 Demo 页面
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── vite.config.ts
│
├── backend/               # Python FastAPI 后端
│   ├── main.py           # FastAPI 入口
│   ├── routers/
│   │   ├── sentiment.py
│   └── models/           # AI 模型加载逻辑
```

## 开发环境设置

### 前端开发

1. 进入前端目录：
```bash
cd frontend
```

2. 安装依赖：
```bash
npm install
```

3. 启动开发服务器：
```bash
npm run dev
```

### 后端开发

1. 创建并激活虚拟环境：
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 启动后端服务器：
```bash
uvicorn main:app --reload
```

## 技术栈

- 前端：React + Radix Themes + Vite
- 后端：Python FastAPI
- AI 模型：待定

## 功能特性

- 待添加 

# AI分析平台

该平台包含两个主要功能：Transformer Sentiment Analysis和General Analysis。

## 后端启动指南

### 安装依赖

```bash
pip install -r requirements.txt
pip install textblob pandas
```

### 启动后端服务

重要提示：必须先进入backend目录，再启动服务

```bash
cd backend
uvicorn app.main:app --reload --port 8001
```

不要使用以下命令（会导致模块导入错误）：
```bash
# 错误方式 - 不要使用
uvicorn backend.app.main:app --reload --port 8001
```

## 前端启动指南

```bash
cd ai-demo-frontend
npm install
npm start
```

## API端点

### Transformer Sentiment Analysis
- `/api/transformer-sentiment/analyze` - 分析单个文本
- `/api/transformer-sentiment/upload` - 上传并分析CSV文件
- `/api/transformer-sentiment/download/{filename}` - 下载分析结果

### General Analysis
- `/api/general/analyze` - 分析单个文本
- `/api/general/upload` - 上传并分析CSV文件
- `/api/general/download/{filename}` - 下载分析结果
- `/api/general/sentiment_data` - 获取情感分析统计数据

## 问题排查

如果遇到API 404错误：
1. 确保后端服务正确启动（见上述启动指南）
2. 确保端口号(8001)与前端代码中请求的端口号一致
3. 确保依赖项已安装：textblob, pandas等

## 数据格式

上传的CSV文件应包含Content列，该列将被用于情感分析。 
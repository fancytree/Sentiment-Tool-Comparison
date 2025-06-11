# AI Demo 后端服务

这是AI Demo展示平台的后端服务，使用Python FastAPI框架开发。

## 功能列表

1. 情感分析 API
2. 更多功能待添加...

## 环境要求

- Python 3.8+
- pip

## 安装步骤

1. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 运行服务

```bash
uvicorn app.main:app --reload
```

服务将在 http://localhost:8000 运行

## API 文档

启动服务后，访问 http://localhost:8000/docs 查看完整的API文档。

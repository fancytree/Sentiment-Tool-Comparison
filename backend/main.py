from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from llm_sentiment import app as llm_sentiment_app
from transformer_sentiment import app as transformer_sentiment_app
from general import app as general_app

app = FastAPI()

# 获取环境变量
ENV = os.getenv("ENV", "development")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# 配置 CORS - 支持更灵活的域名配置
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# 添加环境变量中的前端 URL
if FRONTEND_URL:
    allowed_origins.append(FRONTEND_URL)

# 在生产环境中，允许所有 render.com 的子域名
if ENV == "production":
    allowed_origins.extend([
        "https://*.onrender.com",
        "https://sentiment-analysis-tool.onrender.com",
        "https://sentiment-tool-comparison.onrender.com",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 LLM 情感分析路由
app.include_router(llm_sentiment_app, prefix="/api/llm-sentiment")

# 挂载 Transformer 情感分析路由
app.include_router(transformer_sentiment_app, prefix="/api/transformer-sentiment")

# 挂载通用分析路由
app.include_router(general_app, prefix="/api/general")

# 确保输出目录存在
os.makedirs("output", exist_ok=True)

# 挂载静态文件目录
app.mount("/output", StaticFiles(directory="output"), name="output")

@app.get("/")
async def root():
    return {"message": "Welcome to the API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        workers=1  # 减少到1个工作进程以节省内存
    ) 
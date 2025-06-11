from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import sentiment, llm, transformer_sentiment, general

# 创建FastAPI应用实例
app = FastAPI(
    title="AI Demo API",
    description="AI演示平台的后端API服务",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=False,  # 不允许携带凭证
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有请求头
)

# 注册路由
app.include_router(sentiment.router)
app.include_router(general.router)  # 添加通用分析路由
app.include_router(llm.router)
app.include_router(transformer_sentiment.router)

@app.get("/")
async def root():
    """API根路径"""
    return {"message": "欢迎使用AI Demo API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

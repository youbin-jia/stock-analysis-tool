from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from api.stocks import router as stocks_router
from api.funds import router as funds_router
from api.comparison import router as comparison_router
from tasks.scheduler import init_database_and_cache, start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    await init_database_and_cache()
    start_scheduler()

    yield

    # 关闭时
    stop_scheduler()


app = FastAPI(
    title="股票分析工具 API",
    description="A股股票实时行情、历史数据和对比分析API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(stocks_router)
app.include_router(funds_router)
app.include_router(comparison_router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "股票分析工具 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "timestamp": "2024-01-01T00:00:00"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

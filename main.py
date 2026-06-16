import asyncio
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import config
from src.router import v1_router
from src.utils.draft_downloader import download_draft
from src.utils.logger import logger
from src.middlewares import PrepareMiddleware, ResponseMiddleware, TraceContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.utils.draft_cleanup import draft_cleanup_background_loop

    cleanup_task = asyncio.create_task(draft_cleanup_background_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task


# 1. 创建 FastAPI 应用
app: FastAPI = FastAPI(title="CapCut Mate API", version="1.0", lifespan=lifespan)

# 本地开发/Electron 客户端下载草稿文件时使用；Docker 部署仍可继续使用 nginx 暴露 output。
OUTPUT_DIR = os.path.join(config.PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

# 2. 注册路由
app.include_router(router=v1_router, prefix="/openapi/capcut-mate", tags=["capcut-mate"])

# 3. 添加中间件（最后注册的 TraceContextMiddleware 最先处理请求，用于 W3C trace_id）
app.add_middleware(middleware_class=PrepareMiddleware)
app.add_middleware(middleware_class=ResponseMiddleware)
app.add_middleware(middleware_class=TraceContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. 打印所有路由
for r in app.routes:
    # 1. 取 HTTP 方法列表
    methods = getattr(r, "methods", None) or [getattr(r, "method", "WS")]
    # 2. 安全地取路径
    path = getattr(r, "path", "<unknown>")
    # 3. 安全地取函数名
    name = getattr(r, "name", "<unnamed>")
    logger.info("Route: %s %s -> %s", ",".join(sorted(methods)), path, name)

logger.info("CapCut Mate API")

# 5. 启动
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=30000, log_config=None, log_level="info")

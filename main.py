from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config.settings import settings
import uvicorn
import os

# 디렉토리 생성
os.makedirs(settings.RESULTS_DIR, exist_ok=True)
os.makedirs(settings.LOG_DIR, exist_ok=True)
os.makedirs(settings.SQL_FILES_DIR, exist_ok=True)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 라우트 등록
from app.api.routes import db_routes, telnet_routes, sql_routes, csv_routes, config_routes

app.include_router(db_routes.router, prefix="/api/db", tags=["Database"])
app.include_router(telnet_routes.router, prefix="/api/telnet", tags=["Telnet"])
app.include_router(sql_routes.router, prefix="/api/sql", tags=["SQL"])
app.include_router(csv_routes.router, prefix="/api/csv", tags=["CSV"])
app.include_router(config_routes.router, prefix="/api/config", tags=["Config"])


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

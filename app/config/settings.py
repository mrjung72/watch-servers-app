from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

# 프로젝트 루트 경로
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
REQUEST_DIR = BASE_DIR / "request"
RESULTS_DIR = BASE_DIR / "results"
LOG_DIR = BASE_DIR / "log"
SQL_FILES_DIR = REQUEST_DIR / "sql_files"


class Settings(BaseSettings):
    app_name: str = "Watch Servers"
    app_version: str = "1.0.2"
    debug: bool = True
    
    # 서버 설정
    host: str = "127.0.0.1"
    port: int = 8000
    
    # DB 설정 파일 경로
    db_config_file: str = str(CONFIG_DIR / "dbinfo.json")
    
    # 언어 설정
    default_language: str = "en"
    
    # 타임아웃 설정 (초)
    db_connection_timeout: int = 5
    telnet_timeout: int = 3
    
    # CSV 파일 최대 크기 (KB)
    max_csv_size_kb: int = 200
    
    # 최대 행 수
    max_csv_rows: int = 500
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

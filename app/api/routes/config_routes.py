from fastapi import APIRouter, HTTPException
import json
import os
from typing import Dict, Any
from app.config.settings import settings
from app.database.factory import DatabaseFactory

router = APIRouter()


@router.get("/db-info")
async def get_db_config():
    """DB 설정 정보 조회"""
    try:
        if not os.path.exists(settings.db_config_file):
            return {"databases": {}}
        
        with open(settings.db_config_file, 'r', encoding='utf-8') as f:
            db_configs = json.load(f)
        
        # 비밀번호 마스킹
        masked_configs = {}
        for db_name, config in db_configs.items():
            masked_config = config.copy()
            masked_config['password'] = '***'
            masked_configs[db_name] = masked_config
        
        return {"databases": masked_configs}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/db-info")
async def add_db_config(db_name: str, config: Dict[str, Any]):
    """DB 설정 추가"""
    try:
        # 기존 설정 로드
        if os.path.exists(settings.db_config_file):
            with open(settings.db_config_file, 'r', encoding='utf-8') as f:
                db_configs = json.load(f)
        else:
            db_configs = {}
        
        # 설정 유효성 검사
        db_type = config.get('type', 'mssql')
        DatabaseFactory.validate_config(db_type, config)
        
        # 설정 추가
        db_configs[db_name] = config
        
        # 저장
        os.makedirs(os.path.dirname(settings.db_config_file), exist_ok=True)
        with open(settings.db_config_file, 'w', encoding='utf-8') as f:
            json.dump(db_configs, f, indent=2, ensure_ascii=False)
        
        return {"message": f"Database configuration added: {db_name}"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/db-info/{db_name}")
async def update_db_config(db_name: str, config: Dict[str, Any]):
    """DB 설정 수정"""
    try:
        # 기존 설정 로드
        if not os.path.exists(settings.db_config_file):
            raise HTTPException(status_code=404, detail="Configuration file not found")
        
        with open(settings.db_config_file, 'r', encoding='utf-8') as f:
            db_configs = json.load(f)
        
        if db_name not in db_configs:
            raise HTTPException(status_code=404, detail=f"Database configuration not found: {db_name}")
        
        # 설정 유효성 검사
        db_type = config.get('type', 'mssql')
        DatabaseFactory.validate_config(db_type, config)
        
        # 설정 수정
        db_configs[db_name] = config
        
        # 저장
        with open(settings.db_config_file, 'w', encoding='utf-8') as f:
            json.dump(db_configs, f, indent=2, ensure_ascii=False)
        
        return {"message": f"Database configuration updated: {db_name}"}
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/db-info/{db_name}")
async def delete_db_config(db_name: str):
    """DB 설정 삭제"""
    try:
        # 기존 설정 로드
        if not os.path.exists(settings.db_config_file):
            raise HTTPException(status_code=404, detail="Configuration file not found")
        
        with open(settings.db_config_file, 'r', encoding='utf-8') as f:
            db_configs = json.load(f)
        
        if db_name not in db_configs:
            raise HTTPException(status_code=404, detail=f"Database configuration not found: {db_name}")
        
        # 설정 삭제
        del db_configs[db_name]
        
        # 저장
        with open(settings.db_config_file, 'w', encoding='utf-8') as f:
            json.dump(db_configs, f, indent=2, ensure_ascii=False)
        
        return {"message": f"Database configuration deleted: {db_name}"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-info")
async def get_system_info():
    """시스템 정보 조회"""
    import platform
    import socket
    
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
        
        return {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug,
            "host": settings.host,
            "port": settings.port,
            "system": {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "hostname": platform.node(),
                "local_ip": local_ip
            },
            "directories": {
                "config": settings.db_config_file,
                "request": str(settings.REQUEST_DIR),
                "results": str(settings.RESULTS_DIR),
                "log": str(settings.LOG_DIR),
                "sql_files": str(settings.SQL_FILES_DIR)
            },
            "supported_databases": DatabaseFactory.get_supported_types()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-db/{db_name}")
async def test_db_connection(db_name: str):
    """DB 연결 테스트"""
    try:
        # 설정 로드
        if not os.path.exists(settings.db_config_file):
            raise HTTPException(status_code=404, detail="Configuration file not found")
        
        with open(settings.db_config_file, 'r', encoding='utf-8') as f:
            db_configs = json.load(f)
        
        if db_name not in db_configs:
            raise HTTPException(status_code=404, detail=f"Database configuration not found: {db_name}")
        
        db_config = db_configs[db_name]
        db_type = db_config.get('type', 'mssql')
        
        # 연결 테스트
        connection = DatabaseFactory.create_connection(db_type, db_config)
        result = await connection.test_connection()
        
        return {
            "db_name": db_name,
            "db_type": db_type,
            "server": f"{db_config['server']}:{db_config['port']}",
            "database": db_config['database'],
            "user": db_config['user'],
            "test_result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

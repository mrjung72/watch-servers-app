from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Optional
import os
import json
from datetime import datetime
from app.database.factory import DatabaseFactory
from app.config.settings import settings

router = APIRouter()


@router.post("/execute")
async def execute_sql(db_name: str, sql_name: str):
    """SQL 파일 실행 (파라미터 파일 사용)"""
    try:
        # SQL 파일 경로
        sql_file_path = os.path.join(settings.SQL_FILES_DIR, f"{sql_name}.sql")
        csv_param_path = os.path.join(settings.SQL_FILES_DIR, f"{sql_name}.csv")
        json_param_path = os.path.join(settings.SQL_FILES_DIR, f"{sql_name}.json")
        
        # 파일 존재 확인
        if not os.path.exists(sql_file_path):
            raise HTTPException(status_code=404, detail=f"SQL file not found: {sql_name}.sql")
        
        # 파라미터 파일 확인
        param_file_path = None
        param_type = None
        
        if os.path.exists(json_param_path):
            param_file_path = json_param_path
            param_type = 'json'
        elif os.path.exists(csv_param_path):
            param_file_path = csv_param_path
            param_type = 'csv'
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Parameter file not found: {sql_name}.csv or {sql_name}.json"
            )
        
        # SQL 파일 읽기
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            raw_query = f.read()
        
        # DB 지시어 처리 (#DATABASE dbname)
        lines = raw_query.split('\n')
        cleaned_lines = []
        specified_db_name = None
        
        for line in lines:
            trimmed = line.strip()
            if trimmed.upper().startswith('#DATABASE') or trimmed.upper().startswith('#DB'):
                parts = trimmed.split()
                if len(parts) >= 2:
                    specified_db_name = parts[1]
            else:
                cleaned_lines.append(line)
        
        query = '\n'.join(cleaned_lines)
        
        # DB 설정 로드
        with open(settings.db_config_file, 'r', encoding='utf-8') as f:
            db_configs = json.load(f)
        
        # DB 이름 확인
        target_db_name = specified_db_name if specified_db_name else db_name
        
        if target_db_name not in db_configs:
            raise HTTPException(status_code=404, detail=f"Database configuration not found: {target_db_name}")
        
        db_config = db_configs[target_db_name]
        db_type = db_config.get('type', 'mssql')
        
        # 파라미터 읽기
        if param_type == 'json':
            with open(param_file_path, 'r', encoding='utf-8') as f:
                param_data = json.load(f)
            if isinstance(param_data, dict):
                param_rows = [param_data]
            else:
                param_rows = param_data
        else:
            import pandas as pd
            param_df = pd.read_csv(param_file_path)
            param_rows = param_df.to_dict('records')
        
        # DB 연결
        connection = DatabaseFactory.create_connection(db_type, db_config)
        await connection.connect()
        
        try:
            results = []
            total_count = 0
            error_count = 0
            
            for idx, params in enumerate(param_rows):
                result = await connection.execute_query(query, params)
                
                result_data = {
                    "parameter_set": idx + 1,
                    "parameters": params,
                    "success": result.get('success', False),
                    "row_count": result.get('row_count', 0),
                    "rows": result.get('rows', []),
                    "error": result.get('error_message')
                }
                
                results.append(result_data)
                
                if result.get('success'):
                    total_count += result.get('row_count', 0)
                else:
                    error_count += 1
            
            # 결과 CSV 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"{sql_name}_{target_db_name}_{timestamp}.csv"
            csv_path = os.path.join(settings.RESULTS_DIR, 'sql_files', csv_filename)
            
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            
            # CSV 내용 생성
            csv_content = f"Database Information\n"
            csv_content += f"DB Name,{target_db_name}\n"
            csv_content += f"DB Type,{db_type}\n"
            csv_content += f"Server,{db_config['server']}:{db_config['port']}\n"
            csv_content += f"Database,{db_config['database']}\n"
            csv_content += f"Execution Time,{datetime.now().isoformat()}\n"
            csv_content += "\n"
            
            for result in results:
                csv_content += f"Parameters - Set {result['parameter_set']}\n"
                for key, value in result['parameters'].items():
                    csv_content += f"{key},{value}\n"
                
                if result['error']:
                    csv_content += f"Error,{result['error']}\n\n"
                else:
                    csv_content += f"Result Count,{result['row_count']}\n\n"
                    
                    if result['rows']:
                        columns = list(result['rows'][0].keys())
                        csv_content += ','.join(columns) + '\n'
                        for row in result['rows']:
                            values = [str(row.get(col, '')) for col in columns]
                            csv_content += ','.join(values) + '\n'
                    
                    csv_content += "\n" + "=" * 50 + "\n\n"
            
            with open(csv_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            
            return {
                "db_name": target_db_name,
                "db_type": db_type,
                "sql_name": sql_name,
                "total_parameter_sets": len(param_rows),
                "total_result_rows": total_count,
                "error_count": error_count,
                "results": results,
                "csv_saved": csv_path
            }
            
        finally:
            await connection.disconnect()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-sql")
async def upload_sql_files(
    sql_file: UploadFile = File(...),
    param_file: Optional[UploadFile] = File(None)
):
    """SQL 파일 및 파라미터 파일 업로드"""
    try:
        # SQL 파일 저장
        sql_name = sql_file.filename.replace('.sql', '') if sql_file.filename else 'uploaded'
        sql_path = os.path.join(settings.SQL_FILES_DIR, f"{sql_name}.sql")
        
        with open(sql_path, 'wb') as f:
            f.write(await sql_file.read())
        
        # 파라미터 파일 저장
        param_path = None
        if param_file:
            param_ext = os.path.splitext(param_file.filename)[1]
            param_path = os.path.join(settings.SQL_FILES_DIR, f"{sql_name}{param_ext}")
            
            with open(param_path, 'wb') as f:
                f.write(await param_file.read())
        
        return {
            "message": "Files uploaded successfully",
            "sql_file": sql_path,
            "param_file": param_path,
            "sql_name": sql_name
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_sql_files():
    """SQL 파일 목록 조회"""
    try:
        if not os.path.exists(settings.SQL_FILES_DIR):
            return {"files": []}
        
        files = []
        for filename in os.listdir(settings.SQL_FILES_DIR):
            if filename.endswith('.sql'):
                file_path = os.path.join(settings.SQL_FILES_DIR, filename)
                files.append({
                    "name": filename,
                    "size": os.path.getsize(file_path),
                    "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                })
        
        return {"files": files}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

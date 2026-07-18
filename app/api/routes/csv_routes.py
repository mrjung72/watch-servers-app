from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Optional
import pandas as pd
import os
import json
import re
from datetime import datetime
from app.database.factory import DatabaseFactory
from app.config.settings import settings

router = APIRouter()


def format_date(date: datetime, format_str: str) -> str:
    """날짜 포맷팅"""
    result = format_str
    result = result.replace('yyyy', str(date.year))
    result = result.replace('YYYY', str(date.year))
    result = result.replace('yy', str(date.year)[-2:])
    result = result.replace('YY', str(date.year)[-2:])
    result = result.replace('MM', str(date.month).zfill(2))
    result = result.replace('M', str(date.month))
    result = result.replace('dd', str(date.day).zfill(2))
    result = result.replace('DD', str(date.day).zfill(2))
    result = result.replace('HH', str(date.hour).zfill(2))
    result = result.replace('mm', str(date.minute).zfill(2))
    result = result.replace('ss', str(date.second).zfill(2))
    return result


def substitute_date_variables(filepath: str) -> str:
    """날짜 변수 치환 ${DATE:format}"""
    pattern = r'\$\{DATE:([^}]+)\}'
    now = datetime.now()
    
    def replace_match(match):
        format_str = match.group(1)
        return format_date(now, format_str)
    
    return re.sub(pattern, replace_match, filepath)


def validate_query(query: str) -> dict:
    """쿼리 검증 (SELECT 및 안전한 프로시저만 허용)"""
    normalized = query.strip().upper()
    
    if not normalized:
        return {"valid": False, "error": "Query is empty"}
    
    # SELECT 허용
    is_select = normalized.startswith('SELECT')
    is_exec = normalized.startswith('EXEC') or normalized.startswith('EXECUTE')
    
    # 안전한 시스템 프로시저
    safe_procs = [
        'SP_HELP', 'SP_HELPTEXT', 'SP_HELPDB', 'SP_COLUMNS', 'SP_TABLES',
        'SP_STORED_PROCEDURES', 'SP_WHO', 'SP_SPACEUSED'
    ]
    
    if is_exec:
        is_safe = any(proc in normalized for proc in safe_procs)
        if not is_safe:
            return {"valid": False, "error": "Only safe read-only procedures allowed"}
    elif not is_select:
        return {"valid": False, "error": "Only SELECT queries allowed"}
    
    # 위험한 키워드 확인
    dangerous = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE', 'ALTER', 'CREATE', 'XP_CMDSHELL']
    for keyword in dangerous:
        if keyword in normalized:
            return {"valid": False, "error": f"Dangerous keyword: {keyword}"}
    
    return {"valid": True, "error": None}


@router.post("/query-batch")
async def execute_csv_query_batch(db_name: str, csv_file: UploadFile = File(...)):
    """CSV 파일에 정의된 쿼리 일괄 실행"""
    try:
        # CSV 파일 읽기
        contents = await csv_file.read()
        df = pd.read_csv(pd.io.common.BytesIO(contents))
        
        # 필수 컬럼 확인
        required_columns = ['sql', 'result_filepath']
        missing_columns = [col for col in required_columns if col.lower() not in [c.lower() for c in df.columns]]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # DB 설정 로드
        with open(settings.db_config_file, 'r', encoding='utf-8') as f:
            db_configs = json.load(f)
        
        if db_name not in db_configs:
            raise HTTPException(status_code=404, detail=f"Database configuration not found: {db_name}")
        
        db_config = db_configs[db_name]
        db_type = db_config.get('type', 'mssql')
        
        # DB 연결
        connection = DatabaseFactory.create_connection(db_type, db_config)
        await connection.connect()
        
        try:
            # 결과 디렉토리 생성
            results_dir = os.path.join(settings.RESULTS_DIR, 'sql2csv_result')
            os.makedirs(results_dir, exist_ok=True)
            
            results = []
            success_count = 0
            error_count = 0
            
            for idx, row in df.iterrows():
                # 컬럼명 대소문자 무시하고 찾기
                sql = None
                result_filepath = None
                
                for col in df.columns:
                    if col.lower() == 'sql':
                        sql = row[col]
                    elif col.lower() == 'result_filepath':
                        result_filepath = row[col]
                
                if not sql or not result_filepath:
                    continue
                
                # 쿼리 검증
                validation = validate_query(sql)
                if not validation['valid']:
                    results.append({
                        "index": idx + 1,
                        "sql": sql,
                        "filepath": result_filepath,
                        "success": False,
                        "error": validation['error']
                    })
                    error_count += 1
                    continue
                
                # 날짜 변수 치환
                processed_filepath = substitute_date_variables(result_filepath)
                
                # DB 변수 치환
                final_filepath = processed_filepath.replace('${DB_NAME}', db_name)
                
                # 쿼리 실행
                result = await connection.execute_query(sql, {})
                
                # 결과 저장
                full_path = os.path.join(results_dir, final_filepath)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                if result.get('success') and result.get('rows'):
                    columns = list(result['rows'][0].keys())
                    csv_content = ','.join(columns) + '\n'
                    
                    for row_data in result['rows']:
                        values = []
                        for col in columns:
                            val = row_data.get(col, '')
                            if val is None:
                                val = ''
                            val_str = str(val).replace('\n', ' ').replace('\r', ' ')
                            if ',' in val_str or '"' in val_str:
                                val_str = f'"{val_str.replace(\'"\', \'\'\')}"'
                            values.append(val_str)
                        csv_content += ','.join(values) + '\n'
                    
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(csv_content)
                    
                    results.append({
                        "index": idx + 1,
                        "sql": sql[:100] + '...' if len(sql) > 100 else sql,
                        "filepath": final_filepath,
                        "success": True,
                        "row_count": result.get('row_count', 0)
                    })
                    success_count += 1
                else:
                    error_msg = result.get('error_message', 'No results')
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(f"Error: {error_msg}\n")
                    
                    results.append({
                        "index": idx + 1,
                        "sql": sql[:100] + '...' if len(sql) > 100 else sql,
                        "filepath": final_filepath,
                        "success": False,
                        "error": error_msg
                    })
                    error_count += 1
            
            return {
                "db_name": db_name,
                "db_type": db_type,
                "total_queries": len(results),
                "success_count": success_count,
                "error_count": error_count,
                "results": results
            }
            
        finally:
            await connection.disconnect()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/csv-to-db")
async def csv_to_db_import(mapping_csv: UploadFile = File(...)):
    """CSV 데이터를 DB로 일괄 입력"""
    try:
        # 매핑 CSV 읽기
        contents = await mapping_csv.read()
        df = pd.read_csv(pd.io.common.BytesIO(contents))
        
        # 필수 컬럼 확인
        required_columns = ['DB_NAME', 'TABLE_NAME', 'CSV_FILEPATH']
        missing_columns = [col for col in required_columns if col.upper() not in [c.upper() for c in df.columns]]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # DB 설정 로드
        with open(settings.db_config_file, 'r', encoding='utf-8') as f:
            db_configs = json.load(f)
        
        # DB별로 그룹화
        db_groups = {}
        for _, row in df.iterrows():
            db_name = None
            table_name = None
            csv_path = None
            
            for col in df.columns:
                if col.upper() == 'DB_NAME':
                    db_name = row[col]
                elif col.upper() == 'TABLE_NAME':
                    table_name = row[col]
                elif col.upper() == 'CSV_FILEPATH':
                    csv_path = row[col]
            
            if not all([db_name, table_name, csv_path]):
                continue
            
            # 날짜 변수 치환
            processed_path = substitute_date_variables(csv_path)
            
            if db_name not in db_groups:
                db_groups[db_name] = []
            db_groups[db_name].append({
                "table_name": table_name,
                "csv_path": processed_path,
                "original_path": csv_path
            })
        
        results = []
        success_count = 0
        error_count = 0
        
        # DB별로 처리
        for db_name, items in db_groups.items():
            if db_name not in db_configs:
                results.append({
                    "db_name": db_name,
                    "success": False,
                    "error": "Database configuration not found"
                })
                error_count += len(items)
                continue
            
            db_config = db_configs[db_name]
            db_type = db_config.get('type', 'mssql')
            
            connection = DatabaseFactory.create_connection(db_type, db_config)
            await connection.connect()
            
            try:
                for item in items:
                    table_name = item['table_name']
                    csv_path = item['csv_path']
                    
                    # CSV 파일 존재 확인
                    if not os.path.exists(csv_path):
                        results.append({
                            "db_name": db_name,
                            "table_name": table_name,
                            "csv_path": csv_path,
                            "success": False,
                            "error": "CSV file not found"
                        })
                        error_count += 1
                        continue
                    
                    # CSV 데이터 읽기
                    data_df = pd.read_csv(csv_path)
                    if data_df.empty:
                        results.append({
                            "db_name": db_name,
                            "table_name": table_name,
                            "csv_path": csv_path,
                            "success": False,
                            "error": "CSV file is empty"
                        })
                        error_count += 1
                        continue
                    
                    columns = list(data_df.columns)
                    
                    # MSSQL Identity/Computed 컬럼 제외
                    if db_type.lower() == 'mssql':
                        try:
                            identity_cols = await connection.get_identity_columns(table_name)
                            computed_cols = await connection.get_computed_columns(table_name)
                            
                            exclude_cols = set([c.lower() for c in identity_cols + computed_cols])
                            columns = [c for c in columns if c.lower() not in exclude_cols]
                            
                            if not columns:
                                results.append({
                                    "db_name": db_name,
                                    "table_name": table_name,
                                    "csv_path": csv_path,
                                    "success": False,
                                    "error": "All columns are identity/computed"
                                })
                                error_count += 1
                                continue
                        except Exception as e:
                            pass
                    
                    # INSERT 쿼리 생성
                    placeholders = ', '.join([f'@{c}' for c in columns])
                    insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                    
                    inserted = 0
                    insert_errors = 0
                    
                    for _, row_data in data_df.iterrows():
                        params = {col: row_data[col] for col in columns}
                        
                        try:
                            await connection.execute_query(insert_sql, params)
                            inserted += 1
                        except Exception as e:
                            insert_errors += 1
                    
                    results.append({
                        "db_name": db_name,
                        "table_name": table_name,
                        "csv_path": csv_path,
                        "success": insert_errors == 0,
                        "inserted": inserted,
                        "errors": insert_errors,
                        "total_rows": len(data_df)
                    })
                    
                    if insert_errors == 0:
                        success_count += 1
                    else:
                        error_count += 1
                        
            finally:
                await connection.disconnect()
        
        return {
            "total_mappings": len(results),
            "success_count": success_count,
            "error_count": error_count,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

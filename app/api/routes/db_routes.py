from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List
import pandas as pd
import os
from datetime import datetime
from app.models.schemas import DBConnectionRequest, DBConnectionResult
from app.services.db_service import DBService
from app.config.settings import settings

router = APIRouter()


@router.post("/check")
async def check_db_connection(request: DBConnectionRequest):
    """단일 DB 연결 확인"""
    try:
        result = await DBService.check_db_connection(request.dict())
        
        # 결과 포맷팅
        local_ip = DBService.get_local_ip()
        
        permissions = result.get('permissions', {})
        operation_errors = []
        if permissions.get('selectError'):
            operation_errors.append(f"SELECT: {permissions['selectError']}")
        if permissions.get('insertError'):
            operation_errors.append(f"INSERT: {permissions['insertError']}")
        if permissions.get('deleteError'):
            operation_errors.append(f"DELETE: {permissions['deleteError']}")
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "pc_ip": local_ip,
            "server_ip": request.server,
            "port": request.port,
            "db_name": request.db_name,
            "db_type": request.db_type,
            "db_userid": request.user,
            "result_code": "✅ SUCCESS" if result['success'] else "❌ FAILED",
            "error_code": result.get('error_code', ''),
            "error_msg": result.get('error_msg', ''),
            "collapsed_time": result['elapsed'],
            "perm_select": "Y" if permissions.get('select') else "N",
            "perm_insert": "Y" if permissions.get('insert') else "N",
            "perm_delete": "Y" if permissions.get('delete') else "N",
            "insert_success": "SUCCESS" if permissions.get('insert') else "FAILED" if permissions.get('insertQuery') else "SKIPPED",
            "delete_success": "SUCCESS" if permissions.get('delete') else "FAILED" if permissions.get('deleteQuery') else "SKIPPED",
            "insert_query": permissions.get('insertQuery', ''),
            "delete_query": permissions.get('deleteQuery', ''),
            "operation_errors": " | ".join(operation_errors)
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-batch")
async def check_db_connections_batch(csv_file: UploadFile = File(...)):
    """CSV 파일을 통한 일괄 DB 연결 확인"""
    try:
        # CSV 파일 읽기
        contents = await csv_file.read()
        
        # 파일 크기 확인
        size_kb = len(contents) / 1024
        if size_kb > settings.max_csv_size_kb:
            raise HTTPException(
                status_code=400,
                detail=f"CSV file too large ({size_kb:.2f}KB > {settings.max_csv_size_kb}KB)"
            )
        
        # CSV 파싱
        df = pd.read_csv(pd.io.common.BytesIO(contents))
        
        if len(df) > settings.max_csv_rows:
            raise HTTPException(
                status_code=400,
                detail=f"Too many rows ({len(df)} > {settings.max_csv_rows})"
            )
        
        # 필수 컬럼 확인
        required_columns = ['db_name', 'username', 'password', 'server_ip', 'port', 'db_type']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # 결과 저장
        results = []
        local_ip = DBService.get_local_ip()
        
        for _, row in df.iterrows():
            request_data = {
                'db_name': row['db_name'],
                'db_type': row.get('db_type', 'mssql'),
                'server': row['server_ip'],
                'port': int(row['port']),
                'database': row['db_name'],
                'user': row['username'],
                'password': row['password'],
                'timeout': 5,
                'select_sql': row.get('select_sql'),
                'crud_test_table': row.get('crud_test_table'),
                'crud_test_columns': row.get('crud_test_columns'),
                'crud_test_values': row.get('crud_test_values')
            }
            
            result = await DBService.check_db_connection(request_data)
            
            permissions = result.get('permissions', {})
            operation_errors = []
            if permissions.get('selectError'):
                operation_errors.append(f"SELECT: {permissions['selectError']}")
            if permissions.get('insertError'):
                operation_errors.append(f"INSERT: {permissions['insertError']}")
            if permissions.get('deleteError'):
                operation_errors.append(f"DELETE: {permissions['deleteError']}")
            
            result_data = {
                "timestamp": datetime.now().isoformat(),
                "pc_ip": local_ip,
                "server_ip": row['server_ip'],
                "port": int(row['port']),
                "db_name": row['db_name'],
                "db_type": row.get('db_type', 'mssql'),
                "db_userid": row['username'],
                "result_code": "✅ SUCCESS" if result['success'] else "❌ FAILED",
                "error_code": result.get('error_code', ''),
                "error_msg": result.get('error_msg', ''),
                "collapsed_time": result['elapsed'],
                "perm_select": "Y" if permissions.get('select') else "N",
                "perm_insert": "Y" if permissions.get('insert') else "N",
                "perm_delete": "Y" if permissions.get('delete') else "N",
                "insert_success": "SUCCESS" if permissions.get('insert') else "FAILED" if permissions.get('insertQuery') else "SKIPPED",
                "delete_success": "SUCCESS" if permissions.get('delete') else "FAILED" if permissions.get('deleteQuery') else "SKIPPED",
                "insert_query": permissions.get('insertQuery', ''),
                "delete_query": permissions.get('deleteQuery', ''),
                "operation_errors": " | ".join(operation_errors)
            }
            
            results.append(result_data)
        
        # 결과 CSV 저장
        if results:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            source_name = csv_file.filename.replace('.csv', '') if csv_file.filename else 'unknown'
            csv_filename = f"{source_name}_db_check_{timestamp}.csv"
            csv_path = os.path.join(settings.RESULTS_DIR, csv_filename)
            
            result_df = pd.DataFrame(results)
            result_df.to_csv(csv_path, index=False)
        
        return {
            "total_checked": len(results),
            "success_count": sum(1 for r in results if r['result_code'] == '✅ SUCCESS'),
            "failed_count": sum(1 for r in results if r['result_code'] == '❌ FAILED'),
            "results": results,
            "csv_saved": csv_path if results else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supported-types")
async def get_supported_db_types():
    """지원하는 DB 타입 목록"""
    from app.database.factory import DatabaseFactory
    return DatabaseFactory.get_supported_types()

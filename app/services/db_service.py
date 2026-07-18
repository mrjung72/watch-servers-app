import socket
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
from app.database.factory import DatabaseFactory
from app.config.settings import settings


class DBService:
    """데이터베이스 연결 확인 서비스"""
    
    @staticmethod
    def get_local_ip() -> str:
        """로컬 IP 주소 조회"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "unknown"
    
    @staticmethod
    async def check_db_connection(request: Dict[str, Any]) -> Dict[str, Any]:
        """DB 연결 확인"""
        db_type = request.get('db_type')
        config = {
            'server': request.get('server'),
            'port': request.get('port'),
            'database': request.get('database'),
            'user': request.get('user'),
            'password': request.get('password')
        }
        
        # 설정 유효성 검사
        DatabaseFactory.validate_config(db_type, config)
        
        # 연결 생성
        connection = DatabaseFactory.create_connection(db_type, config)
        
        start_time = datetime.now()
        result = {
            'success': False,
            'elapsed': 0,
            'db_type': db_type,
            'permissions': {
                'select': False,
                'insert': False,
                'delete': False
            }
        }
        
        try:
            await connection.connect()
            
            # 권한 확인 정보 준비
            test_table_info = None
            if request.get('select_sql') or request.get('crud_test_table'):
                test_table_info = {
                    'selectSql': request.get('select_sql'),
                    'table': request.get('crud_test_table'),
                    'columns': request.get('crud_test_columns').split(',') if request.get('crud_test_columns') else None,
                    'values': request.get('crud_test_values').split(',') if request.get('crud_test_values') else None
                }
            
            # 권한 확인
            permissions = await connection.check_permissions(test_table_info)
            result['permissions'] = permissions
            result['success'] = True
            
            await connection.disconnect()
            
        except Exception as e:
            result['error_code'] = type(e).__name__
            result['error_msg'] = str(e)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        result['elapsed'] = f"{elapsed:.2f}"
        
        return result
    
    @staticmethod
    def generate_crud_sqls(row: Dict[str, Any], db_type: str) -> Dict[str, Optional[str]]:
        """CRUD SQL 생성"""
        crud_test_table = row.get('crud_test_table')
        crud_test_columns = row.get('crud_test_columns')
        crud_test_values = row.get('crud_test_values')
        
        if not all([crud_test_table, crud_test_columns, crud_test_values]):
            return {'insert_sql': None, 'delete_sql': None}
        
        columns = [col.strip() for col in crud_test_columns.split(',')]
        values = [val.strip() for val in crud_test_values.split(',')]
        
        if len(columns) != len(values):
            return {'insert_sql': None, 'delete_sql': None}
        
        # INSERT SQL 생성
        if db_type.lower() == 'postgresql':
            insert_sql = f"INSERT INTO {crud_test_table} ({', '.join(columns)}) VALUES ({', '.join([f'${i+1}' for i in range(len(values))])})"
        else:
            quoted_values = [f"'{v}'" for v in values]
            insert_sql = f"INSERT INTO {crud_test_table} ({', '.join(columns)}) VALUES ({', '.join(quoted_values)})"
        
        # DELETE SQL 생성
        delete_sql = f"DELETE FROM {crud_test_table} WHERE {columns[0]} = '{values[0]}'"
        
        return {'insert_sql': insert_sql, 'delete_sql': delete_sql}

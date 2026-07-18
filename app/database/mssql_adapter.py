from typing import Dict, Any, Optional, List
import pymssql
import asyncio
from datetime import datetime
from .base import BaseDatabase


class MSSQLAdapter(BaseDatabase):
    """MSSQL 데이터베이스 어댑터"""
    
    async def connect(self):
        """MSSQL 연결"""
        loop = asyncio.get_event_loop()
        self.connection = await loop.run_in_executor(
            None,
            pymssql.connect,
            self.config.get('server'),
            self.config.get('user'),
            self.config.get('password'),
            self.config.get('database'),
            self.config.get('port', 1433),
            'utf8',
            30  # login_timeout
        )
    
    async def disconnect(self):
        """연결 종료"""
        if self.connection:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.connection.close)
            self.connection = None
    
    async def test_connection(self) -> Dict[str, Any]:
        """연결 테스트"""
        try:
            await self.connect()
            cursor = self.connection.cursor()
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, cursor.execute, "SELECT 1")
            result = await loop.run_in_executor(None, cursor.fetchone)
            await self.disconnect()
            return {
                "success": True,
                "message": "Connection successful"
            }
        except Exception as e:
            return {
                "success": False,
                "error_code": str(type(e).__name__),
                "error_message": str(e)
            }
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """쿼리 실행"""
        cursor = self.connection.cursor()
        loop = asyncio.get_event_loop()
        
        try:
            if params:
                # 파라미터 바인딩 (pymssql은 %(name)s 형식)
                await loop.run_in_executor(None, cursor.execute, query, params)
            else:
                await loop.run_in_executor(None, cursor.execute, query)
            
            # 결과 조회
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = await loop.run_in_executor(None, cursor.fetchall)
                result = [
                    dict(zip(columns, row))
                    for row in rows
                ]
            else:
                result = []
            
            row_count = cursor.rowcount if cursor.rowcount >= 0 else len(result)
            
            return {
                "success": True,
                "rows": result,
                "row_count": row_count
            }
        except Exception as e:
            return {
                "success": False,
                "error_message": str(e)
            }
    
    async def check_permissions(self, test_table_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """권한 확인"""
        permissions = {
            "select": False,
            "insert": False,
            "delete": False,
            "select_error": None,
            "insert_error": None,
            "delete_error": None,
            "insert_query": None,
            "delete_query": None
        }
        
        cursor = self.connection.cursor()
        loop = asyncio.get_event_loop()
        
        # SELECT 권한 확인
        if test_table_info and test_table_info.get('selectSql'):
            try:
                select_sql = test_table_info['selectSql']
                await loop.run_in_executor(None, cursor.execute, select_sql)
                await loop.run_in_executor(None, cursor.fetchmany, 1)
                permissions["select"] = True
            except Exception as e:
                permissions["select_error"] = str(e)
        
        # INSERT/DELETE 권한 확인
        if test_table_info and test_table_info.get('table') and test_table_info.get('columns') and test_table_info.get('values'):
            table = test_table_info['table']
            columns = test_table_info['columns']
            values = test_table_info['values']
            
            if len(columns) == len(values):
                # INSERT 쿼리 생성
                quoted_values = [f"'{v}'" for v in values]
                insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(quoted_values)})"
                permissions["insert_query"] = insert_sql
                
                try:
                    await loop.run_in_executor(None, cursor.execute, insert_sql)
                    self.connection.commit()
                    permissions["insert"] = True
                    
                    # DELETE 쿼리 생성 및 실행
                    delete_sql = f"DELETE FROM {table} WHERE {columns[0]} = '{values[0]}'"
                    permissions["delete_query"] = delete_sql
                    
                    try:
                        await loop.run_in_executor(None, cursor.execute, delete_sql)
                        self.connection.commit()
                        permissions["delete"] = True
                    except Exception as e:
                        permissions["delete_error"] = str(e)
                        self.connection.rollback()
                except Exception as e:
                    permissions["insert_error"] = str(e)
                    self.connection.rollback()
        
        return permissions
    
    async def get_identity_columns(self, table_name: str) -> List[str]:
        """Identity 컬럼 목록 조회"""
        cursor = self.connection.cursor()
        loop = asyncio.get_event_loop()
        
        try:
            query = """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = %s
                AND COLUMNPROPERTY(OBJECT_ID(TABLE_NAME), COLUMN_NAME, 'IsIdentity') = 1
            """
            await loop.run_in_executor(None, cursor.execute, query, table_name)
            rows = await loop.run_in_executor(None, cursor.fetchall)
            return [row[0] for row in rows] if rows else []
        except Exception:
            return []
    
    async def get_computed_columns(self, table_name: str) -> List[str]:
        """Computed 컬럼 목록 조회"""
        cursor = self.connection.cursor()
        loop = asyncio.get_event_loop()
        
        try:
            query = """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = %s
                AND IS_COMPUTED = 1
            """
            await loop.run_in_executor(None, cursor.execute, query, table_name)
            rows = await loop.run_in_executor(None, cursor.fetchall)
            return [row[0] for row in rows] if rows else []
        except Exception:
            return []

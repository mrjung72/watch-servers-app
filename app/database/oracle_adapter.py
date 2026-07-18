from typing import Dict, Any, Optional, List
import oracledb
import asyncio
from .base import BaseDatabase


class OracleAdapter(BaseDatabase):
    """Oracle 데이터베이스 어댑터"""
    
    async def connect(self):
        """Oracle 연결"""
        loop = asyncio.get_event_loop()
        
        # Oracle 연결 설정
        dsn = f"{self.config.get('server')}:{self.config.get('port', 1521)}/{self.config.get('database')}"
        
        self.connection = await loop.run_in_executor(
            None,
            oracledb.connect,
            user=self.config.get('user'),
            password=self.config.get('password'),
            dsn=dsn
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
            await loop.run_in_executor(None, cursor.execute, "SELECT 1 FROM DUAL")
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
                # Oracle은 :param 형식 사용
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
                # INSERT 쿼리 생성 (Oracle은 :param 형식)
                param_placeholders = [f':{c}' for c in columns]
                insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(param_placeholders)})"
                permissions["insert_query"] = insert_sql
                
                try:
                    param_dict = dict(zip(columns, values))
                    await loop.run_in_executor(None, cursor.execute, insert_sql, param_dict)
                    self.connection.commit()
                    permissions["insert"] = True
                    
                    # DELETE 쿼리 생성 및 실행
                    delete_sql = f"DELETE FROM {table} WHERE {columns[0]} = :{columns[0]}"
                    permissions["delete_query"] = delete_sql
                    
                    try:
                        await loop.run_in_executor(None, cursor.execute, delete_sql, {columns[0]: values[0]})
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
        """Oracle은 Identity 컬럼 조회"""
        cursor = self.connection.cursor()
        loop = asyncio.get_event_loop()
        
        try:
            query = """
                SELECT COLUMN_NAME
                FROM ALL_TAB_COLUMNS
                WHERE TABLE_NAME = UPPER(:table_name)
                AND IDENTITY_COLUMN = 'YES'
            """
            await loop.run_in_executor(None, cursor.execute, query, {"table_name": table_name})
            rows = await loop.run_in_executor(None, cursor.fetchall)
            return [row[0] for row in rows] if rows else []
        except Exception:
            return []
    
    async def get_computed_columns(self, table_name: str) -> List[str]:
        """Oracle은 Virtual 컬럼 조회"""
        cursor = self.connection.cursor()
        loop = asyncio.get_event_loop()
        
        try:
            query = """
                SELECT COLUMN_NAME
                FROM ALL_TAB_COLUMNS
                WHERE TABLE_NAME = UPPER(:table_name)
                AND VIRTUAL_COLUMN = 'YES'
            """
            await loop.run_in_executor(None, cursor.execute, query, {"table_name": table_name})
            rows = await loop.run_in_executor(None, cursor.fetchall)
            return [row[0] for row in rows] if rows else []
        except Exception:
            return []

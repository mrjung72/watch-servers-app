from typing import Dict, Any, Optional, List
import aiomysql
import asyncio
from .base import BaseDatabase


class MySQLAdapter(BaseDatabase):
    """MySQL 데이터베이스 어댑터"""
    
    async def connect(self):
        """MySQL 연결"""
        self.connection = await aiomysql.connect(
            host=self.config.get('server'),
            port=self.config.get('port', 3306),
            user=self.config.get('user'),
            password=self.config.get('password'),
            db=self.config.get('database'),
            charset='utf8mb4',
            autocommit=False
        )
    
    async def disconnect(self):
        """연결 종료"""
        if self.connection:
            await self.connection.close()
            self.connection = None
    
    async def test_connection(self) -> Dict[str, Any]:
        """연결 테스트"""
        try:
            await self.connect()
            async with self.connection.cursor() as cursor:
                await cursor.execute("SELECT 1")
                result = await cursor.fetchone()
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
        async with self.connection.cursor() as cursor:
            try:
                if params:
                    await cursor.execute(query, params)
                else:
                    await cursor.execute(query)
                
                # 결과 조회
                if cursor.description:
                    columns = [col[0] for col in cursor.description]
                    rows = await cursor.fetchall()
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
        
        async with self.connection.cursor() as cursor:
            # SELECT 권한 확인
            if test_table_info and test_table_info.get('selectSql'):
                try:
                    select_sql = test_table_info['selectSql']
                    await cursor.execute(select_sql)
                    await cursor.fetchmany(1)
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
                    insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join([f'%s' for _ in values])})"
                    permissions["insert_query"] = insert_sql
                    
                    try:
                        await cursor.execute(insert_sql, values)
                        await self.connection.commit()
                        permissions["insert"] = True
                        
                        # DELETE 쿼리 생성 및 실행
                        delete_sql = f"DELETE FROM {table} WHERE {columns[0]} = %s"
                        permissions["delete_query"] = delete_sql
                        
                        try:
                            await cursor.execute(delete_sql, (values[0],))
                            await self.connection.commit()
                            permissions["delete"] = True
                        except Exception as e:
                            permissions["delete_error"] = str(e)
                            await self.connection.rollback()
                    except Exception as e:
                        permissions["insert_error"] = str(e)
                        await self.connection.rollback()
        
        return permissions
    
    async def get_identity_columns(self, table_name: str) -> List[str]:
        """MySQL은 Auto Increment 컬럼 조회"""
        async with self.connection.cursor() as cursor:
            try:
                query = """
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = %s
                    AND EXTRA LIKE '%auto_increment%'
                """
                await cursor.execute(query, table_name)
                rows = await cursor.fetchall()
                return [row[0] for row in rows] if rows else []
            except Exception:
                return []
    
    async def get_computed_columns(self, table_name: str) -> List[str]:
        """MySQL은 Computed 컬럼 조회"""
        async with self.connection.cursor() as cursor:
            try:
                query = """
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = %s
                    AND EXTRA LIKE '%generated%'
                """
                await cursor.execute(query, table_name)
                rows = await cursor.fetchall()
                return [row[0] for row in rows] if rows else []
            except Exception:
                return []

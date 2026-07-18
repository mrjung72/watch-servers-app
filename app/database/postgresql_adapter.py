from typing import Dict, Any, Optional, List
import asyncpg
import asyncio
from .base import BaseDatabase


class PostgreSQLAdapter(BaseDatabase):
    """PostgreSQL 데이터베이스 어댑터"""
    
    async def connect(self):
        """PostgreSQL 연결"""
        self.connection = await asyncpg.connect(
            host=self.config.get('server'),
            port=self.config.get('port', 5432),
            user=self.config.get('user'),
            password=self.config.get('password'),
            database=self.config.get('database')
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
            await self.connection.fetchval("SELECT 1")
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
        try:
            if params:
                # asyncpg는 $1, $2 형식 사용
                # params를 dict에서 list로 변환 필요
                param_values = list(params.values())
                rows = await self.connection.fetch(query, *param_values)
            else:
                rows = await self.connection.fetch(query)
            
            result = [dict(row) for row in rows]
            
            return {
                "success": True,
                "rows": result,
                "row_count": len(result)
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
        
        # SELECT 권한 확인
        if test_table_info and test_table_info.get('selectSql'):
            try:
                select_sql = test_table_info['selectSql']
                await self.connection.fetchrow(select_sql)
                permissions["select"] = True
            except Exception as e:
                permissions["select_error"] = str(e)
        
        # INSERT/DELETE 권한 확인
        if test_table_info and test_table_info.get('table') and test_table_info.get('columns') and test_table_info.get('values'):
            table = test_table_info['table']
            columns = test_table_info['columns']
            values = test_table_info['values']
            
            if len(columns) == len(values):
                # INSERT 쿼리 생성 (PostgreSQL은 $1, $2 형식)
                placeholders = ', '.join([f'${i+1}' for i in range(len(values))])
                insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                permissions["insert_query"] = insert_sql
                
                try:
                    await self.connection.execute(insert_sql, *values)
                    permissions["insert"] = True
                    
                    # DELETE 쿼리 생성 및 실행
                    delete_sql = f"DELETE FROM {table} WHERE {columns[0]} = $1"
                    permissions["delete_query"] = delete_sql
                    
                    try:
                        await self.connection.execute(delete_sql, values[0])
                        permissions["delete"] = True
                    except Exception as e:
                        permissions["delete_error"] = str(e)
                except Exception as e:
                    permissions["insert_error"] = str(e)
        
        return permissions
    
    async def get_identity_columns(self, table_name: str) -> List[str]:
        """PostgreSQL은 Serial 컬럼 조회"""
        try:
            query = """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s
                AND column_default LIKE 'nextval%'
            """
            # PostgreSQL은 %s 대신 $1 사용
            rows = await self.connection.fetch(query.replace('%s', '$1'), table_name)
            return [row['column_name'] for row in rows] if rows else []
        except Exception:
            return []
    
    async def get_computed_columns(self, table_name: str) -> List[str]:
        """PostgreSQL은 Generated 컬럼 조회"""
        try:
            query = """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s
                AND is_generated = 'YES'
            """
            rows = await self.connection.fetch(query.replace('%s', '$1'), table_name)
            return [row['column_name'] for row in rows] if rows else []
        except Exception:
            return []

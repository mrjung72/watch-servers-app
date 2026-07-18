from typing import Dict, Any
from .base import BaseDatabase
from .mssql_adapter import MSSQLAdapter
from .mysql_adapter import MySQLAdapter
from .postgresql_adapter import PostgreSQLAdapter
from .oracle_adapter import OracleAdapter


class DatabaseFactory:
    """데이터베이스 팩토리"""
    
    @staticmethod
    def create_connection(db_type: str, config: Dict[str, Any]) -> BaseDatabase:
        """DB 타입에 따른 어댑터 생성"""
        normalized_type = db_type.lower()
        
        if normalized_type in ['mssql', 'sqlserver']:
            return MSSQLAdapter(config)
        elif normalized_type in ['mysql', 'mariadb']:
            return MySQLAdapter(config)
        elif normalized_type in ['postgresql', 'postgres']:
            return PostgreSQLAdapter(config)
        elif normalized_type == 'oracle':
            return OracleAdapter(config)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    @staticmethod
    def get_supported_types():
        """지원하는 DB 타입 목록"""
        return [
            {"type": "mssql", "name": "Microsoft SQL Server", "port": 1433},
            {"type": "mysql", "name": "MySQL", "port": 3306},
            {"type": "mariadb", "name": "MariaDB", "port": 3306},
            {"type": "postgresql", "name": "PostgreSQL", "port": 5432},
            {"type": "oracle", "name": "Oracle Database", "port": 1521}
        ]
    
    @staticmethod
    def validate_config(db_type: str, config: Dict[str, Any]) -> bool:
        """설정 유효성 검사"""
        required_fields = ['server', 'port', 'database', 'user', 'password']
        missing_fields = [field for field in required_fields if not config.get(field)]
        
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        port = int(config.get('port', 0))
        if port < 1 or port > 65535:
            raise ValueError("Port must be between 1 and 65535")
        
        return True

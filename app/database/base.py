from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio


class BaseDatabase(ABC):
    """데이터베이스 어댑터 기본 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
    
    @abstractmethod
    async def connect(self):
        """데이터베이스 연결"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """데이터베이스 연결 종료"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """연결 테스트"""
        pass
    
    @abstractmethod
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """쿼리 실행"""
        pass
    
    @abstractmethod
    async def check_permissions(self, test_table_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """권한 확인 (SELECT, INSERT, DELETE)"""
        pass
    
    @abstractmethod
    async def get_identity_columns(self, table_name: str) -> List[str]:
        """Identity 컬럼 목록 조회 (MSSQL용)"""
        pass
    
    @abstractmethod
    async def get_computed_columns(self, table_name: str) -> List[str]:
        """Computed 컬럼 목록 조회 (MSSQL용)"""
        pass

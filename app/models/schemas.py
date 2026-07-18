from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class DBConnectionRequest(BaseModel):
    """DB 연결 확인 요청"""
    db_name: str
    db_type: str
    server: str
    port: int
    database: str
    user: str
    password: str
    timeout: Optional[int] = 5
    select_sql: Optional[str] = None
    crud_test_table: Optional[str] = None
    crud_test_columns: Optional[str] = None
    crud_test_values: Optional[str] = None


class DBConnectionResult(BaseModel):
    """DB 연결 결과"""
    timestamp: str
    pc_ip: str
    server_ip: str
    port: int
    db_name: str
    db_type: str
    db_userid: str
    result_code: str
    error_code: Optional[str] = None
    error_msg: Optional[str] = None
    collapsed_time: str
    perm_select: str
    perm_insert: str
    perm_delete: str
    insert_success: Optional[str] = None
    delete_success: Optional[str] = None
    insert_query: Optional[str] = None
    delete_query: Optional[str] = None
    operation_errors: Optional[str] = None


class TelnetCheckRequest(BaseModel):
    """텔넷 연결 확인 요청"""
    server_ip: str
    port: int
    server_name: Optional[str] = None
    timeout: Optional[int] = 3


class TelnetCheckResult(BaseModel):
    """텔넷 연결 결과"""
    timestamp: str
    pc_ip: str
    server_ip: str
    port: int
    server_name: Optional[str] = None
    result_code: str
    error_code: Optional[str] = None
    error_msg: Optional[str] = None
    collapsed_time: str


class SQLExecuteRequest(BaseModel):
    """SQL 실행 요청"""
    db_name: str
    sql_name: str
    parameters: Optional[List[Dict[str, Any]]] = None


class CSVQueryRequest(BaseModel):
    """CSV 기반 쿼리 요청"""
    db_name: str
    csv_path: str


class CSVToDBRequest(BaseModel):
    """CSV to DB 요청"""
    mapping_csv_path: str


class ConfigDBInfo(BaseModel):
    """DB 설정 정보"""
    type: str
    server: str
    port: int
    database: str
    user: str
    password: str

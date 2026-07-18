import socket
import asyncio
from typing import Dict, Any
from datetime import datetime


class TelnetService:
    """텔넷 연결 확인 서비스"""
    
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
    async def check_port(ip: str, port: int, timeout: int) -> Dict[str, Any]:
        """포트 연결 확인"""
        result = {
            'is_connected': False,
            'error_code': '',
            'error_msg': '',
            'collapsed_time': 0
        }
        
        start_time = datetime.now()
        
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            
            result['is_connected'] = True
            
        except asyncio.TimeoutError:
            result['error_code'] = 'ETIMEDOUT'
            result['error_msg'] = f'Connection timed out in {timeout}s'
            
        except Exception as e:
            result['error_code'] = type(e).__name__
            result['error_msg'] = str(e)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        result['collapsed_time'] = f"{elapsed:.2f}"
        
        return result

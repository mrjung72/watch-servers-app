from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List
import pandas as pd
import os
from datetime import datetime
from app.models.schemas import TelnetCheckRequest, TelnetCheckResult
from app.services.telnet_service import TelnetService
from app.config.settings import settings

router = APIRouter()


@router.post("/check")
async def check_telnet_connection(request: TelnetCheckRequest):
    """단일 텔넷 연결 확인"""
    try:
        result = await TelnetService.check_port(
            request.server_ip,
            request.port,
            request.timeout or settings.telnet_timeout
        )
        
        local_ip = TelnetService.get_local_ip()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "pc_ip": local_ip,
            "server_ip": request.server_ip,
            "port": request.port,
            "server_name": request.server_name or '',
            "result_code": "SUCCESS" if result['is_connected'] else "FAILED",
            "error_code": result.get('error_code', ''),
            "error_msg": result.get('error_msg', ''),
            "collapsed_time": result['collapsed_time']
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-batch")
async def check_telnet_connections_batch(csv_file: UploadFile = File(...)):
    """CSV 파일을 통한 일괄 텔넷 연결 확인"""
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
        required_columns = ['server_ip', 'port']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # 결과 저장
        results = []
        local_ip = TelnetService.get_local_ip()
        
        for _, row in df.iterrows():
            result = await TelnetService.check_port(
                row['server_ip'],
                int(row['port']),
                settings.telnet_timeout
            )
            
            result_data = {
                "timestamp": datetime.now().isoformat(),
                "pc_ip": local_ip,
                "server_ip": row['server_ip'],
                "port": int(row['port']),
                "server_name": row.get('server_name', ''),
                "result_code": "SUCCESS" if result['is_connected'] else "FAILED",
                "error_code": result.get('error_code', ''),
                "error_msg": result.get('error_msg', ''),
                "collapsed_time": result['collapsed_time']
            }
            
            results.append(result_data)
        
        # 결과 CSV 저장
        if results:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            source_name = csv_file.filename.replace('.csv', '') if csv_file.filename else 'unknown'
            csv_filename = f"{source_name}_telnet_check_{timestamp}.csv"
            csv_path = os.path.join(settings.RESULTS_DIR, csv_filename)
            
            result_df = pd.DataFrame(results)
            result_df.to_csv(csv_path, index=False)
        
        return {
            "total_checked": len(results),
            "success_count": sum(1 for r in results if r['result_code'] == 'SUCCESS'),
            "failed_count": sum(1 for r in results if r['result_code'] == 'FAILED'),
            "results": results,
            "csv_saved": csv_path if results else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

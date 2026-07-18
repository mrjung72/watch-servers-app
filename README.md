# Watch Servers

FastAPI 기반 서버 모니터링 및 데이터베이스 유틸리티 API 서비스

## 개요

Watch Servers는 데이터베이스 연결 확인, 텔넷 연결 확인, SQL 실행, CSV 기반 일괄 처리 등의 기능을 제공하는 REST API 서비스입니다.

## 주요 기능

### 1. 데이터베이스 연결 확인
- 단일 DB 연결 테스트
- CSV 파일을 통한 일괄 DB 연결 확인
- 권한 확인 (SELECT, INSERT, DELETE)
- 연결 결과 CSV 자동 저장

### 2. 텔넷 연결 확인
- 단일 서버 포트 연결 테스트
- CSV 파일을 통한 일괄 텔넷 확인
- 연결 결과 CSV 자동 저장

### 3. SQL 실행
- SQL 파일 업로드 및 실행
- 파라미터 파일 지원 (CSV/JSON)
- DB 지시어 지원 (#DATABASE dbname)
- 실행 결과 CSV 자동 저장

### 4. CSV 기반 쿼리 실행
- CSV 파일에 정의된 쿼리 일괄 실행
- 날짜 변수 치환 지원 (${DATE:yyyyMMddHHmmss})
- DB 변수 치환 지원 (${DB_NAME})
- 쿼리 검증 (SELECT 및 안전한 프로시저만 허용)

### 5. CSV to DB
- CSV 데이터를 DB 테이블로 일괄 입력
- 매핑 CSV 파일로 대상 테이블 지정
- MSSQL Identity/Computed 컬럼 자동 제외
- 자동 타입 변환

### 6. 설정 관리
- DB 설정 CRUD API
- 시스템 정보 조회
- DB 연결 테스트

## 지원 데이터베이스

| DB 타입 | 드라이버 | 기본 포트 |
|---------|----------|-----------|
| MSSQL | pymssql | 1433 |
| MySQL | aiomysql | 3306 |
| MariaDB | aiomysql | 3306 |
| PostgreSQL | asyncpg | 5432 |
| Oracle | oracledb | 1521 |
| Tibero | cx_Oracle | 8629 |

## 프로젝트 구조

# Python
__pycache__/
*.py[cod]
*$py.class
*.pyo
*.pyd

# Virtual environments
.venv/
venv/
env/
ENV/

# Environment files
.env
.env.*
!.env.example

# IDE / Editor
.idea/
.vscode/
*.swp
*.swo

# Logs
log/
logs/
*.log

# Build / Distribution
build/
dist/
release/
*.spec~

# PyInstaller
*.manifest
*.toc
*.pyz
*.pkg

# Test / Coverage
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/

# Cache
.cache/
.mypy_cache/
.ruff_cache/

# OS files
.DS_Store
Thumbs.db
desktop.ini

# Project runtime outputs
results/
request/uploads/

```
watch-servers/
├── main.py                          # FastAPI 메인 애플리케이션
├── requirements.txt                 # Python 의존성
├── config/
│   └── dbinfo.json                 # DB 설정 파일
├── app/
│   ├── config/
│   │   └── settings.py             # 애플리케이션 설정
│   ├── api/
│   │   └── routes/
│   │       ├── db_routes.py        # DB 관련 API
│   │       ├── telnet_routes.py    # 텔넷 관련 API
│   │       ├── sql_routes.py       # SQL 실행 API
│   │       ├── csv_routes.py       # CSV 처리 API
│   │       └── config_routes.py    # 설정 관리 API
│   ├── database/
│   │   ├── base.py                 # DB 어댑터 기본 클래스
│   │   ├── factory.py              # DB 팩토리
│   │   ├── mssql_adapter.py        # MSSQL 어댑터
│   │   ├── mysql_adapter.py        # MySQL 어댑터
│   │   ├── postgresql_adapter.py   # PostgreSQL 어댑터
│   │   └── oracle_adapter.py       # Oracle 어댑터
│   ├── models/
│   │   └── schemas.py              # Pydantic 모델
│   └── services/
│       ├── db_service.py           # DB 서비스
│       └── telnet_service.py       # 텔넷 서비스
├── request/
│   └── sql_files/                  # SQL 파일 디렉토리
├── results/                         # 결과 저장 디렉토리
└── log/                            # 로그 디렉토리
```

## 설치

### 1. Python 설치
Python 3.8 이상 필요

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. DB 설정
`config/dbinfo.json` 파일에 데이터베이스 설정 추가

```json
{
  "my_database": {
    "type": "mssql",
    "server": "localhost",
    "port": 1433,
    "database": "my_db",
    "user": "sa",
    "password": "your_password"
  }
}
```

## 실행

### 개발 모드
```bash
python main.py
```

또는 uvicorn 직접 실행:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 프로덕션 모드
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API 엔드포인트

### DB 연결 확인
- `POST /api/db/check` - 단일 DB 연결 확인
- `POST /api/db/check-batch` - CSV 파일 일괄 확인
- `GET /api/db/supported-types` - 지원 DB 타입 목록

### 텔넷 연결 확인
- `POST /api/telnet/check` - 단일 텔넷 연결 확인
- `POST /api/telnet/check-batch` - CSV 파일 일괄 확인

### SQL 실행
- `POST /api/sql/execute` - SQL 파일 실행
- `POST /api/sql/upload-sql` - SQL 파일 업로드
- `GET /api/sql/list` - SQL 파일 목록

### CSV 처리
- `POST /api/csv/query-batch` - CSV 기반 쿼리 일괄 실행
- `POST /api/csv/csv-to-db` - CSV 데이터 DB 입력

### 설정 관리
- `GET /api/config/db-info` - DB 설정 조회
- `POST /api/config/db-info` - DB 설정 추가
- `PUT /api/config/db-info/{db_name}` - DB 설정 수정
- `DELETE /api/config/db-info/{db_name}` - DB 설정 삭제
- `GET /api/config/system-info` - 시스템 정보 조회
- `GET /api/config/test-db/{db_name}` - DB 연결 테스트

### 기본
- `GET /` - 앱 정보
- `GET /health` - 헬스 체크
- `GET /docs` - Swagger UI (API 문서)
- `GET /redoc` - ReDoc (API 문서)

## API 사용 예시

### DB 연결 확인
```bash
curl -X POST "http://localhost:8000/api/db/check" \
  -H "Content-Type: application/json" \
  -d '{
    "db_name": "my_database",
    "db_type": "mssql",
    "server": "localhost",
    "port": 1433,
    "database": "my_db",
    "user": "sa",
    "password": "password",
    "timeout": 5
  }'
```

### 텔넷 연결 확인
```bash
curl -X POST "http://localhost:8000/api/telnet/check" \
  -H "Content-Type: application/json" \
  -d '{
    "server_ip": "192.168.1.100",
    "port": 8080,
    "server_name": "Web Server",
    "timeout": 3
  }'
```

### SQL 실행
```bash
curl -X POST "http://localhost:8000/api/sql/execute?db_name=my_database&sql_name=my_query"
```

### CSV 기반 쿼리 실행
```bash
curl -X POST "http://localhost:8000/api/csv/query-batch?db_name=my_database" \
  -F "csv_file=@queries.csv"
```

## CSV 파일 형식

### DB 연결 확인 CSV
```csv
db_name,username,password,server_ip,port,db_type,select_sql,crud_test_table,crud_test_columns,crud_test_values
my_db,sa,password,localhost,1433,mssql,"SELECT top 3 * FROM users",users,"id,name","1,Test User"
```

### 텔넷 연결 확인 CSV
```csv
server_ip,port,server_name
192.168.1.100,8080,Web Server
192.168.1.101,3306,MySQL Server
```

### CSV 기반 쿼리 CSV
```csv
SQL,result_filepath
"SELECT * FROM users;",results/users_${DATE:yyyyMMddHHmmss}.csv
"SELECT * FROM orders;",results/orders_${DATE:yyyyMMddHHmmss}.csv
```

### CSV to DB 매핑 CSV
```csv
DB_NAME,TABLE_NAME,CSV_FILEPATH
my_database,users,request/users_data.csv
my_database,orders,request/orders_data.csv
```

## 날짜 변수 포맷

`${DATE:format}` 형식으로 사용 가능한 포맷:
- `yyyy` - 4자리 연도
- `yy` - 2자리 연도
- `MM` - 월 (01-12)
- `dd` - 일 (01-31)
- `HH` - 시간 (00-23)
- `mm` - 분 (00-59)
- `ss` - 초 (00-59)

예시: `${DATE:yyyyMMddHHmmss}` → `20260718124130`

## 설정

### 환경 변수 (`.env` 파일)
```env
APP_NAME=Watch Servers
DEBUG=True
HOST=0.0.0.0
PORT=8000
DB_CONNECTION_TIMEOUT=5
TELNET_TIMEOUT=3
MAX_CSV_SIZE_KB=200
MAX_CSV_ROWS=500
```

## 라이선스

MIT License

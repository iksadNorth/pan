# Docker Compose를 사용한 실행 가이드

## 구성

이 Docker Compose 설정은 다음 서비스를 포함합니다:

- **selenium-hub**: Selenium Grid Hub (포트 4444, ARM64)
- **chrome-node-1**: Chrome Node 1 (최대 4개 세션, ARM64, VNC/noVNC 지원)
- **chrome-node-2**: Chrome Node 2 (최대 4개 세션, ARM64, VNC/noVNC 지원)
- **api-server**: FastAPI 서버 (포트 8000)

## 실행 방법

### 전체 서비스 시작

```bash
docker-compose up -d
```

### 서비스 상태 확인

```bash
docker-compose ps
```

### 로그 확인

```bash
# 전체 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f api-server
docker-compose logs -f selenium-hub
```

### 서비스 중지

```bash
docker-compose down
```

### 서비스 재시작

```bash
docker-compose restart
```

## 접속 정보

- **FastAPI 서버**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **Selenium Grid Hub**: http://localhost:4444
- **Grid 상태 확인**: http://localhost:4444/status

### VNC 접속 (브라우저 화면 확인용)

각 Chrome Node는 VNC를 통해 접속할 수 있습니다:

- **Chrome Node 1 noVNC**: http://localhost:7901
  - 비밀번호: `q1w2e3r4`
- **Chrome Node 2 noVNC**: http://localhost:7902
  - 비밀번호: `q1w2e3r4`

VNC 클라이언트를 사용하는 경우:
- **Chrome Node 1 VNC**: `localhost:5901`
- **Chrome Node 2 VNC**: `localhost:5902`
  - 비밀번호: `q1w2e3r4`

## 환경 변수

FastAPI 서버는 다음 환경 변수를 사용합니다:

- `SIDE_STORAGE_DIR`: Side 파일 저장 디렉토리 (기본값: `/app/storage/sides`)
- `LOCK_STORAGE_DIR`: Lock 파일 저장 디렉토리 (기본값: `/app/storage/locks`)
- `SELENIUM_GRID_URL`: Selenium Grid Hub URL (기본값: `http://selenium-hub:4444`)

## 볼륨

- `./storage`: Side 파일과 Lock 파일이 영구 저장됩니다.
- `./logs`: 모든 서비스의 로그 파일이 저장됩니다.
  - `logs/selenium-hub/`: Selenium Grid Hub 로그
  - `logs/chrome-node-1/`: Chrome Node 1 로그
  - `logs/chrome-node-2/`: Chrome Node 2 로그
  - `logs/api-server/`: FastAPI 서버 로그 (`api.log`)

## 로그 확인

### 실시간 로그 확인

```bash
# 전체 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f api-server
docker-compose logs -f selenium-hub
docker-compose logs -f chrome-node-1
docker-compose logs -f chrome-node-2
```

### 로그 파일 확인

```bash
# API 서버 로그
tail -f logs/api-server/api.log

# 특정 시간의 로그 저장
./scripts/save-logs.sh
```

## 문제 해결

### 컨테이너가 시작되지 않는 경우

```bash
# 로그 확인
docker-compose logs

# 컨테이너 재빌드
docker-compose build --no-cache
docker-compose up -d
```

### Selenium Grid 연결 문제

1. Grid Hub가 정상적으로 시작되었는지 확인:
   ```bash
   curl http://localhost:4444/status
   ```

2. Chrome Node가 Hub에 연결되었는지 확인:
   ```bash
   docker-compose logs chrome-node-1
   docker-compose logs chrome-node-2
   ```

### 포트 충돌

포트 4444 또는 8000이 이미 사용 중인 경우, `docker-compose.yml`에서 포트 매핑을 변경하세요.


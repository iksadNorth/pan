# Pan

**Pan**은 그리스 신화의 양치기 신으로, 양들을 목장에 풀어놓고 풀을 뜯어먹게 하며 양털을 취하는 것처럼, 이 프로젝트는 Selenium IDE가 내보내는 `.side` 파일을 Selenium WebDriver로 실행하여 HTML이라는 풀을 뜯어먹고 데이터라는 양털을 취하는 FastAPI 기반 웹 서버입니다.

Selenium Grid를 활용한 세션 풀링과 동시성 제어를 통해 안정적이고 효율적인 테스트 실행 환경을 제공합니다.


## 주요 의의

- **Selenium IDE, Grid 그리고 WebDriver 기술의 통합**: QA 및 웹 크롤링 자동화 파이프라인 완성
- **Session Pool 구현**: 세션을 서버 가동 시, 미리 확보함으로서 연산 속도 최적화. DB의 Connection Pool에서 착안한 아이디어.
- **동시성 제어**: 파일 시스템 기반 Lock을 통한 세션 동시 접근 제어. 세션을 점유한 요청이 존재한다면, 이후 요청을 거절.
- **템플릿 엔진을 통한 다향성 확보**: Jinja2 템플릿을 통해 1개의 시나리오로 N개의 시나리오 생성.

## 주요 성과

1. QA 시나리오 실행 속도 최적화
    - [순차실행 -> 병렬실행]: Selenium Standalone에서 Selenium Grid로 형태를 바꿈으로서 병렬 연산 구현
    - [세션 Pool을 통한 Warm Up]: 요청마다 윈도우창을 띄우는 것이 아닌 미리 윈도우창을 띄우고 크롤링 수행
2. 동시성 제어를 통한 작업 간 간섭 방지
    - [파일 기반 Lock]: 각 세션마다 Lock 파일이 존재하며, Lock 파일이 존재한다면, 다른 요청에 의해 방해되지 않게 독점성 확보
3. 템플릿 엔진을 통해 파라미터 활용성 극대화
    - Side 파일자체를 Jinja2 템플릿 엔진으로 렌더링을 하므로 동일한 테스트 시나리오가 N개의 시나리오의 효과를 냄.
4. 유지보수성 확보를 위한 Side 저장소 및 Lock 관리 주체의 추상화
    - [SideRepository]: 차후 시나리오 파일[Side 파일] 저장소가 FileSystem에서 MongoDB로 변경되는 것을 고려해 SideRepository로 추상화
    - [LockRepository]: 차후 Lock 관리 체계가 FileSystem에서 Redis로 변경되는 것을 고려해 LockRepository로 추상화
5. 세션 Pool의 세션 확보 작업을 비동기적으로 처리
    - FastAPI의 lifespan 중 세션 확보 작업시간[대략 2분]을 동기처리가 아닌 비동기처리로 바꿔 서버 가동시간 단축
6. 로직 흐름을 쉽게 로깅하기 위해 데코레이터 사용
    - [@log_method_call]: 오류 파악을 위해 그때그때마다 로깅 작업을 하는 것이 아닌 각 메서드마다의 실행 순서 및 Return값을 감시함으로서 쉽게 오류 파악


## 프로젝트 구조

```
src/
├── models.py              # 데이터 모델 (SideProject, SideTest, SideSuite, SideCommand)
├── loader.py              # Side 파일 로딩 및 파싱
├── parser.py              # Jinja2 템플릿 파서
├── runner.py              # 테스트 실행 로직
├── session_pool.py        # Selenium Grid 세션 풀 관리
├── logger_config.py       # 로깅 설정
└── repositories/
    ├── side_repository.py              # Side 파일 저장소 인터페이스
    ├── filesystem_side_repository.py   # FileSystem 기반 side 파일 저장소 구현체
    ├── lock_repository.py              # Lock 관리 인터페이스
    └── filesystem_lock_repository.py   # FileSystem 기반 Lock 관리 구현체
```

## 주요 클래스

### 테스트 실행 (`runner.py`)

#### `SeleniumSideRunner`
Side 프로젝트를 실행하는 메인 러너 클래스입니다.

**주요 메서드**:
- `run_suite(suite: SideSuite) -> None`: Suite 실행
- `run_test(test: SideTest) -> None`: 단일 테스트 실행
- `run_suite_with_driver(suite: SideSuite, driver: WebDriver) -> None`: 기존 WebDriver로 Suite 실행
- `run_test_with_driver(test: SideTest, driver: WebDriver) -> None`: 기존 WebDriver로 테스트 실행


### 세션 풀 관리 (`session_pool.py`)

#### `SessionPool`
Selenium Grid 세션을 풀링하여 관리하는 클래스입니다.

**주요 기능**:
- **초기화**: 애플리케이션 시작 시 가능한 한 많은 세션을 미리 생성
- **세션 재사용**: 생성된 세션을 풀에 보관하여 재사용
- **자동 복구**: 손상된 세션 자동 감지 및 재생성
- **세션 유효성 검증**: 세션 사용 전 유효성 확인

**주요 메서드**:
- `initialize() -> None`: 세션 풀 초기화 (비동기)
- `list_sessions() -> list[str]`: 사용 가능한 세션 ID 목록 반환
- `acquire_session(session_id: str) -> ContextManager[WebDriver]`: 세션 획득 (context manager)
- `cleanup() -> None`: 모든 세션 정리


### 템플릿 파서 (`parser.py`)

#### `Parser`
Jinja2 템플릿에서 사용할 수 있는 파서 클래스입니다.

**주요 메서드**:
- `render(side_content: str) -> str`: 템플릿 렌더링
- `getToday(format: str) -> str`: 현재 시간 반환
- `getRandomNumber(min_val: int, max_val: int) -> int`: 랜덤 숫자 생성
- `getRandomString(length: int) -> str`: 랜덤 문자열 생성
- `getFaker() -> Faker`: Faker 객체 반환 (한국 로케이션)

**사용 예시**:
```json
{
  "command": "type",
  "target": "id=username",
  "value": "{{ parser.getFaker().email() }}"
}
```


### 저장소 패턴 (`repositories/`)

#### `SideRepository` / `FilesystemSideRepository`
Side 파일을 저장하고 관리하는 인터페이스 및 구현체입니다.

**주요 메서드**:
- `save(side_id: str, content: str) -> None`: Side 파일 저장
- `get(side_id: str) -> str`: Side 파일 조회
- `list_all() -> List[str]`: 모든 Side 파일 ID 목록
- `delete(side_id: str) -> None`: Side 파일 삭제
- `exists(side_id: str) -> bool`: 파일 존재 여부 확인

#### `LockRepository` / `FilesystemLockRepository`
Lock 관리를 위한 인터페이스 및 파일 시스템 기반 구현체입니다.

**주요 메서드**:
- `acquire(lock_key: str, timeout: float) -> ContextManager[str]`: Lock 획득
- `is_locked(lock_key: str) -> bool`: Lock 상태 확인

**동작 원리**: 파일 시스템의 파일 존재 여부를 이용한 간단한 lock 메커니즘을 구현합니다. `acquire()`는 context manager를 반환하여 `with` 문에서 사용하면 자동으로 해제됩니다.


## 주요 API

### Side 파일 관리

#### `POST /api/v1/sides/{side_id}`
Side 파일을 업로드합니다.

**Request Body**:
```json
{
  "content": "{ ... side 파일 JSON ... }"
}
```

**Response**: `201 Created`
```json
{
  "message": "Side 파일 '{side_id}'이(가) 성공적으로 업로드되었습니다."
}
```

#### `GET /api/v1/sides`
저장된 모든 Side 파일 목록을 조회합니다.

**Response**: `200 OK`
```json
{
  "sides": ["side1", "side2", "side3"]
}
```

#### `GET /api/v1/sides/{side_id}`
특정 Side 파일의 내용을 조회합니다.

**Response**: `200 OK`
```json
{
  "side_id": "side1",
  "content": "{ ... side 파일 JSON ... }"
}
```

### 세션 실행

#### `GET /api/v1/sessions`
세션 풀에 있는 사용 가능한 세션 목록을 조회합니다.

**Response**: `200 OK`
```json
{
  "sessions": ["session1", "session2", "session3"]
}
```

#### `POST /api/v1/sessions`
가용한 세션을 자동으로 찾아서 Side 파일을 실행합니다.

**Request Body**:
```json
{
  "side_id": "side1",
  "suite": "Default Suite",  // 선택
  "test": "로그인 테스트",     // 선택 (suite와 함께 사용 불가)
  "param": {                  // 선택 (템플릿 파라미터)
    "username": "testuser",
    "password": "testpass"
  }
}
```

**Response**: `200 OK` (HTML 문서)

**동작 방식**:
1. 사용 가능한 세션 목록 조회
2. Lock이 잠겨있지 않은 세션 찾기
3. Lock 획득 시도
4. 성공하면 해당 세션에서 테스트 실행
5. 모든 세션이 사용 중이면 `503 Service Unavailable` 반환


## 요구 사항

- Python 3.10+
- Selenium Grid (Docker Compose로 실행 가능)
- 의존성: `pip install -e .` 또는 `uv sync`

## 실행 방법

1. Selenium Grid 시작 (Docker Compose 사용):
```bash
docker-compose up -d
```

2. API 서버 실행:
```bash
uvicorn main:app --reload
```

3. API 문서 확인:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

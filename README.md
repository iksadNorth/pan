# Pan

**Pan**은 그리스 신화의 양치기 신으로, 양들을 목장에 풀어놓고 풀을 뜯어먹게 하며 양털을 취하는 것처럼, 이 프로젝트는 Selenium IDE가 내보내는 `.side` 파일을 Selenium WebDriver로 실행하여 HTML이라는 풀을 뜯어먹고 데이터라는 양털을 취하는 FastAPI 기반 웹 서버입니다.

Selenium Grid를 활용한 세션 풀링과 동시성 제어를 통해 안정적이고 효율적인 테스트 실행 환경을 제공합니다.

## 주요 기능

- **Side 파일 관리**: `.side` 파일의 업로드, 조회, 수정, 삭제
- **Selenium Grid 통합**: Selenium Grid를 통한 분산 테스트 실행
- **세션 풀링**: 세션 재사용을 통한 성능 최적화
- **동시성 제어**: 파일 시스템 기반 Lock을 통한 세션 동시 접근 제어
- **템플릿 지원**: Jinja2 템플릿을 통한 동적 파라미터 처리
- **자동 복구**: 손상된 세션 자동 재생성

## 해결한 문제점

### 1. 세션 생성 오버헤드 문제
**문제**: 매번 새로운 WebDriver 세션을 생성하면 초기화 시간이 오래 걸리고 리소스가 낭비됩니다.

**해결**: `SessionPool` 클래스를 통해 애플리케이션 시작 시 미리 세션을 생성하고 풀에 보관하여 재사용합니다. 이를 통해 테스트 실행 시간을 크게 단축했습니다.

### 2. 동시 실행 시 세션 충돌 문제
**문제**: 여러 요청이 동시에 같은 세션을 사용하려고 하면 충돌이 발생합니다.

**해결**: `FilesystemLockRepository`를 통해 파일 시스템 기반 Lock 메커니즘을 구현하여, 각 세션당 하나의 작업만 실행되도록 보장합니다.

### 3. 세션 손상 시 복구 문제
**문제**: 네트워크 오류나 예기치 못한 상황으로 세션이 손상되면 테스트가 실패합니다.

**해결**: `SessionPool.acquire_session()` 메서드에서 세션 유효성을 확인하고, 손상된 세션은 자동으로 재생성하여 안정성을 확보했습니다.

### 4. 동적 테스트 데이터 생성 문제
**문제**: 테스트에 동적인 데이터(랜덤 값, 현재 시간 등)가 필요할 때 `.side` 파일을 수정해야 합니다.

**해결**: `Parser` 클래스를 통해 Jinja2 템플릿을 지원하여, 실행 시점에 동적 데이터를 주입할 수 있습니다.

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
    ├── side_repository.py           # Side 파일 저장소 인터페이스
    ├── filesystem_side_repository.py # 파일 시스템 기반 구현
    ├── lock_repository.py           # Lock 관리 인터페이스
    └── filesystem_lock_repository.py # 파일 시스템 기반 Lock 구현
```

## 주요 클래스

### 데이터 모델 (`models.py`)

#### `SideProject`
Selenium IDE 프로젝트를 나타내는 최상위 모델입니다.

```python
@dataclass
class SideProject:
    id: str
    name: str
    url: str | None
    tests: Dict[str, SideTest]
    suites: List[SideSuite]
```

**주요 메서드**:
- `get_suite(suite_name: str | None) -> SideSuite`: Suite 이름으로 Suite 객체 조회
- `get_test_by_name(test_name: str) -> SideTest`: 테스트 이름으로 Test 객체 조회

#### `SideTest`
개별 테스트 케이스를 나타냅니다.

```python
@dataclass
class SideTest:
    id: str
    name: str
    commands: List[SideCommand]
```

#### `SideSuite`
여러 테스트를 그룹화한 Suite입니다.

```python
@dataclass
class SideSuite:
    id: str
    name: str
    tests: List[str]  # 테스트 ID 목록
    persist_session: bool
    parallel: bool
    timeout: Optional[int]
```

#### `SideCommand`
Selenium IDE 명령어를 나타냅니다.

```python
@dataclass
class SideCommand:
    id: str
    command: str      # 명령어 타입 (open, click, type 등)
    target: str       # 대상 요소 (locator)
    value: str        # 값
    comment: str | None
```

### 테스트 실행 (`runner.py`)

#### `SeleniumSideRunner`
Side 프로젝트를 실행하는 메인 러너 클래스입니다.

**주요 메서드**:
- `run_suite(suite: SideSuite) -> None`: Suite 실행
- `run_test(test: SideTest) -> None`: 단일 테스트 실행
- `run_suite_with_driver(suite: SideSuite, driver: WebDriver) -> None`: 기존 WebDriver로 Suite 실행
- `run_test_with_driver(test: SideTest, driver: WebDriver) -> None`: 기존 WebDriver로 테스트 실행

#### `CommandExecutor`
Selenium IDE 명령어를 실제 Selenium WebDriver 동작으로 변환하는 클래스입니다.

**지원하는 명령어**:
- `open`: URL 열기
- `click`: 요소 클릭
- `clickAndWait`: 클릭 후 대기
- `type`: 텍스트 입력
- `sendKeys`: 키 입력 (특수 키 포함)
- `pause`: 대기
- `mouseOver`: 마우스 오버
- `setWindowSize`: 창 크기 설정
- `assertText`: 텍스트 검증
- `assertElementPresent`: 요소 존재 검증
- `storeText`: 텍스트 저장

**특수 기능**:
- Locator 자동 인식: `css=`, `xpath=`, `id=`, `name=` 등의 prefix 자동 처리
- 특수 키 매핑: `${KEY_ENTER}`, `${KEY_TAB}` 등을 Selenium Keys로 변환

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

### 로더 (`loader.py`)

#### `load_side_project(json_payload: str) -> SideProject`
Selenium IDE `.side` JSON 문자열을 `SideProject` 객체로 변환합니다.

**처리 과정**:
1. JSON 문자열 파싱
2. `SideCommand` 객체 생성
3. `SideTest` 객체 생성 (commands 포함)
4. `SideSuite` 객체 생성
5. `SideProject` 객체 생성 및 반환

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

#### `PATCH /api/v1/sides/{side_id}`
Side 파일을 수정합니다.

**Request Body**:
```json
{
  "content": "{ ... 수정된 side 파일 JSON ... }"
}
```

#### `DELETE /api/v1/sides/{side_id}`
Side 파일을 삭제합니다.

**Response**: `204 No Content`

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

#### `POST /api/v1/sessions/{session_id}`
특정 세션에서 Side 파일을 실행합니다.

**Request Body**:
```json
{
  "side_id": "side1",
  "suite": "Default Suite",  // 선택
  "test": "로그인 테스트",     // 선택
  "param": {                  // 선택
    "username": "testuser"
  }
}
```

**Response**: `200 OK` (HTML 문서)

**동작 방식**:
1. 세션에 대한 Lock 획득 시도 (timeout: 30초)
2. Side 파일 로드 및 템플릿 렌더링 (param이 있는 경우)
3. 세션에서 테스트 실행
4. 실행 결과 HTML 반환

## 환경 변수

- `SIDE_STORAGE_DIR`: Side 파일 저장 디렉토리 (기본값: `./storage/sides`)
- `LOCK_STORAGE_DIR`: Lock 파일 저장 디렉토리 (기본값: `./storage/locks`)
- `SELENIUM_GRID_URL`: Selenium Grid Hub URL (기본값: `http://localhost:4444`)
- `SESSION_POOL_INIT_TIMEOUT`: 세션 풀 초기화 타임아웃 (초) (기본값: `30.0`)
- `LOG_DIR`: 로그 파일 저장 디렉토리 (기본값: `./logs/api-server`)
- `LOG_LEVEL`: 로그 레벨 (기본값: `INFO`)

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

## 로깅

프로젝트는 구조화된 로깅 시스템을 제공합니다:

- **파일 로깅**: `LOG_DIR/api.log`에 저장
- **콘솔 로깅**: 표준 출력으로 출력
- **메서드 호출 로깅**: `@log_method_call` 데코레이터로 자동 로깅 (DEBUG 레벨)

## 아키텍처 특징

### Repository 패턴
저장소 로직을 인터페이스와 구현체로 분리하여, 향후 데이터베이스나 클라우드 스토리지로 쉽게 전환할 수 있습니다.

### Context Manager 패턴
세션과 Lock 관리는 context manager를 사용하여 자동으로 리소스를 정리하도록 구현했습니다.

### 비동기 초기화
세션 풀 초기화는 백그라운드에서 비동기로 실행되어 애플리케이션 시작 시간을 단축합니다.

# Pan

**Pan**은 그리스 신화의 양치기 신으로, 양들을 목장에 풀어놓고 풀을 뜯어먹게 하며 양털을 취하는 것처럼, 이 프로젝트는 Selenium IDE가 내보내는 `.side` 파일을 Selenium WebDriver로 실행하여 HTML이라는 풀을 뜯어먹고 데이터라는 양털을 취하는 FastAPI 기반 웹 서버입니다.

![양치기 그림](documents/shepherd.png)

*그림 0: 양치기 소년 그림*

Selenium Grid를 활용한 세션 풀링과 동시성 제어를 통해 안정적이고 효율적인 테스트 실행 환경을 제공합니다.

![시스템 아키텍처](documents/architecture-diagram.png)

*그림 1: Pan 시스템 아키텍처 - FastAPI 서버, Selenium Grid, 세션 풀, 저장소의 관계*

## 왜 이런 식으로 만들었나요?

- **크롤링 데이터 수집할 때마다 HTML 구조 분석하는 거 너무 힘들다..**
  - 화면 녹화 매크로 툴을 사용해보자! - [1]
- **웹 프로덕트 테스트를 수기로 하니까 너무 귀찮다. 해야하는 건데 후순위로 밀리게 되네..**
  - 화면 녹화 매크로 툴을 사용해보자! - [2]
- **1개의 페이지를 재귀적으로 크롤링하니까 20분 정도 걸리네. 너무 오래걸린다..**
  - 병렬 분산 처리를 통해 시간 단축을 해보자!
- **데이터 파이프라인에 편입하려면 Airflow 이미지 크기가 비대해진다. 빌드 시간이 너무 오래걸린다..**
  - REST API 웹서버로 만들어서 HTTP 통신으로 단순화해보자!
- **크롤링할 때마다 크롬창을 띄워야 하니 리소스 낭비가 너무 심하다..**
  - 서버 가동 시, 미리 크롬창을 여러 개 띄워놓고 재활용해보자!

### 시연 영상 1: Selenium IDE로 매크로 Side 파일 생성

![demo](documents/demo-make-side.gif)

*영상 1-1: Selenium IDE를 사용하여 웹 자동화 매크로를 녹화하고 .side 파일로 내보내는 과정*

![demo](documents/demo-side-macro.gif)

*영상 1-2: .side 파일를 이용한 매크로 실행 [Selenium IDE]*

### 시연 영상 2: Side 파일 등록

![demo](documents/demo-upload-side.gif)

*영상 2: Swagger UI를 통해 생성한 .side 파일을 Pan API에 업로드하는 과정*

### 시연 영상 3: noVNC를 통한 세션 모니터링

![demo](documents/demo-monitor-session.gif)

*영상 3: Selenium Grid Node의 noVNC를 통해 실제 브라우저 세션이 실행되는 모습을 실시간으로 확인*

### 시연 영상 4: 특정 세션에서 Side 파일 실행

![demo](documents/demo-siderun-in-session.gif)

*영상 4: 등록된 Side 파일을 특정 세션에서 실행하고 결과를 확인하는 과정*

### 시연 영상 5: 템플릿 파라미터를 활용한 동적 시나리오 실행

![demo](documents/demo-siderun-dynamic.gif)

*영상 5: Jinja2 템플릿이 포함된 Side 파일에 다양한 파라미터를 전달하여 동적으로 시나리오를 생성하고 실행하는 과정*

## 주요 의의

- **Selenium IDE, Grid 그리고 WebDriver 기술의 통합**: QA 및 웹 크롤링 자동화 파이프라인 완성
- **Session Pool 구현**: 서버 가동 시 세션을 미리 확보하여 연산 속도 최적화. DB의 Connection Pool에서 착안한 아이디어
- **동시성 제어**: 파일 시스템 기반 Lock을 통한 세션 동시 접근 제어. 세션을 점유한 요청이 존재할 경우, 이후 요청은 대기 또는 거절
- **템플릿 엔진을 통한 다양성 확보**: Jinja2 템플릿을 통해 1개의 시나리오로 N개의 시나리오 생성

## 주요 성과

1. **QA 시나리오 실행 속도 최적화**
    - **순차 실행 → 병렬 실행**: Selenium Standalone에서 Selenium Grid로 전환하여 병렬 연산 구현
    
    ![순차 실행 vs 병렬 실행](documents/sequential-vs-parallel.png)
    *그림 2: 순차 실행과 병렬 실행 비교*
    
    - **세션 Pool을 통한 Warm Up**: 요청마다 브라우저 세션을 생성하는 대신, 서버 시작 시 미리 세션을 확보하여 크롤링 수행

2. **동시성 제어를 통한 작업 간 간섭 방지**
    - **파일 기반 Lock**: 각 세션마다 Lock 파일을 생성하여, 세션이 점유 중일 때 다른 요청의 접근을 차단하여 독점성 확보
    
    ![Lock 메커니즘](documents/lock-mechanism.png)
    *그림 3: 파일 기반 Lock을 통한 세션 동시성 제어*

3. **템플릿 엔진을 통한 파라미터 활용성 극대화**
    - Side 파일 자체를 Jinja2 템플릿으로 렌더링하여, 동일한 테스트 시나리오로 다양한 파라미터 조합의 시나리오를 생성
    
    ![템플릿 렌더링](documents/template-rendering.png)
    *그림 4: Jinja2 템플릿을 통한 1:N 시나리오 생성*

4. **유지보수성 확보를 위한 저장소 및 Lock 관리 추상화**
    - **SideRepository**: Side 파일 저장소를 인터페이스로 추상화하여, FileSystem에서 MongoDB 등으로의 전환 용이
    - **LockRepository**: Lock 관리 체계를 인터페이스로 추상화하여, FileSystem에서 Redis 등으로의 전환 용이

5. **세션 Pool 초기화 작업의 비동기 처리**
    - FastAPI의 lifespan 중 세션 확보 작업(약 2분)을 비동기로 처리하여 서버 가동 시간 단축

6. **로직 흐름 추적을 위한 데코레이터 기반 로깅**
    - **@log_method_call**: 각 메서드의 실행 순서 및 반환값을 자동으로 로깅하여 오류 파악 용이성 향상


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

![세션 풀 동작 흐름](documents/session-pool-flow.png)
*그림 5: 세션 풀의 초기화, 사용, 재사용, 복구 흐름*

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

**Request**: `multipart/form-data`
- `file`: 업로드할 Side 파일 (.side 파일)

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
특정 Side 파일을 다운로드합니다.

**Response**: `200 OK`
- Content-Type: `application/json`
- 파일 다운로드 (.side 파일)

#### `PATCH /api/v1/sides/{side_id}`
Side 파일을 수정합니다.

**Request**: `multipart/form-data`
- `file`: 수정할 Side 파일 (.side 파일)

**Response**: `200 OK`
```json
{
  "message": "Side 파일 '{side_id}'이(가) 성공적으로 수정되었습니다."
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
2. Lock이 잠겨있지 않은 세션 탐색
3. Lock 획득 시도
4. 성공 시 해당 세션에서 테스트 실행
5. 모든 세션이 사용 중이면 `503 Service Unavailable` 반환

![API 실행 흐름](documents/api-execution-flow.png)
*그림 6: POST /api/v1/sessions API의 전체 실행 흐름*


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

![Swagger UI](documents/swagger-ui-screenshot.png)
*그림 7: Swagger UI를 통한 API 테스트 예시*

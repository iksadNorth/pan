# src/ 디렉토리

이 디렉토리는 Pan 프로젝트의 핵심 비즈니스 로직을 담고 있습니다. 각 모듈은 명확한 단일 책임을 가지며, 모듈 간 의존성은 최소화되어 있습니다.

## ⚠️ 수정 시 주의사항

이 디렉토리의 모듈들은 신중하게 설계된 책임 분리를 기반으로 합니다. 코드를 수정하기 전에 반드시 다음을 확인하세요:

1. **모듈의 원래 책임을 벗어나지 마세요**
2. **로직 중복을 만들지 마세요** - 공통 로직은 적절한 서비스나 유틸리티 모듈에 위치시켜야 합니다
3. **의존성 방향을 확인하세요** - 상위 레이어 → 하위 레이어 순서로 의존해야 합니다
4. **Repository 패턴을 준수하세요** - 데이터 영속성 로직은 `repositories/` 디렉토리를 통해 접근해야 합니다

## 모듈 목록

### `models.py`
- **역할**: 도메인 모델 정의**
- **책임**:
  - `SideProject`, `SideTest`, `SideSuite`, `SideCommand` 데이터 클래스 정의
  - 도메인 로직 메서드 (`get_suite()`, `get_test_by_name()`)
- **수정 시 주의사항**:
  - 비즈니스 로직이나 인프라 관련 코드를 포함하지 마세요
  - 순수한 데이터 구조와 도메인 메서드만 포함해야 합니다
  - 다른 모듈에 의존하지 않는 독립적인 모듈입니다

### `loader.py`
- **역할**: Side 파일 JSON 파싱
- **책임**:
  - JSON 문자열을 도메인 모델(`SideProject`)로 변환
  - JSON 구조 검증 및 파싱
  - `load_side_project()` 함수 제공
- **수정 시 주의사항**:
  - 템플릿 렌더링 로직을 포함하지 마세요. `parser.py`의 역할입니다
  - 파일 I/O 로직을 포함하지 마세요. Repository의 역할입니다
  - `models.py`에만 의존합니다

### `parser.py`
- **역할**: Jinja2 템플릿 렌더링
- **책임**:
  - Jinja2 템플릿 엔진을 사용한 Side 파일 렌더링
  - 템플릿 변수 및 헬퍼 함수 제공 (`getToday()`, `getRandomNumber()`, `js_file()` 등)
  - JavaScript 파일 로드 및 주입
- **수정 시 주의사항**:
  - Side 파일 파싱 로직을 포함하지 마세요. `loader.py`의 역할입니다
  - 파일 저장/로드 로직을 포함하지 마세요. Repository의 역할입니다
  - 환경 변수 `JS_STORAGE_DIR`을 사용하여 JavaScript 파일 경로를 결정합니다

### `runner.py`
- **역할**: Selenium 명령 실행 엔진
- **책임**:
  - Selenium IDE 명령어 실행 (`open`, `click`, `type`, `sendKeys`, `storeText` 등)
  - JavaScript 코드 실행 (`execute_javascript()`)
  - Side 프로젝트 실행 (`SeleniumSideRunner`, `execute_side_on_driver()`)
  - Locator 해석 및 요소 찾기
- **수정 시 주의사항**:
  - 세션 관리 로직을 포함하지 마세요. `session_pool.py`의 역할입니다
  - Side 파일 로드/렌더링 로직을 포함하지 마세요. `SideService`의 역할입니다
  - Lock 관리 로직을 포함하지 마세요. `LockRepository`의 역할입니다
  - `models.py`에 의존합니다

### `side_service.py`
- **역할**: Side 파일 로드 및 렌더링 서비스
- **책임**:
  - Side 파일 로드 및 Jinja2 템플릿 렌더링 통합
  - `SideFileNotFoundError`, `SideFileParseError`, `SideTemplateRenderError` 예외 정의
  - `load_and_render()` 메서드 제공
- **수정 시 주의사항**:
  - **이 모듈은 `main.py`와 `websocket_manager.py`에서 공통으로 사용됩니다**
  - 로직을 변경하면 두 곳 모두에 영향을 미치므로 신중하게 수정하세요
  - 파일 I/O는 반드시 `SideRepository`를 통해 수행하세요
  - `loader.py`, `parser.py`, `repositories/`에 의존합니다

### `session_pool.py`
- **역할**: Selenium Grid 세션 풀 관리
- **책임**:
  - WebDriver 세션 생성, 조회, 유효성 검사, 정리
  - 세션 풀 초기화 및 생명주기 관리
  - `list_sessions()`, `has_session()`, `acquire_session()` 메서드 제공
- **수정 시 주의사항**:
  - **Lock 관련 로직을 포함하지 마세요.** Lock 관리는 `LockRepository`의 책임입니다
  - 세션 실행 로직을 포함하지 마세요. `runner.py`의 역할입니다
  - `iter_available_sessions()` 같은 Lock 의존성 메서드를 추가하지 마세요
  - Selenium WebDriver에만 의존하는 독립적인 모듈입니다

### `websocket_manager.py`
- **역할**: 웹소켓 연결 및 세션 관리
- **책임**:
  - 웹소켓 연결 수락/해제 및 자동 Lock 관리
  - 웹소켓 메시지 처리 (JavaScript 실행, Side 실행, 페이지 소스 조회)
  - 연결별 세션 ID 및 Lock UUID 관리
- **수정 시 주의사항**:
  - **Side 파일 로드/렌더링 로직을 직접 구현하지 마세요.** `SideService`를 사용하세요
  - 세션 실행 로직을 직접 구현하지 마세요. `runner.py`의 메서드를 재사용하세요
  - 웹소켓 연결 관리에만 집중하세요
  - `SideService`, `SessionPool`, `LockRepository`, `runner.py`에 의존합니다

### `exception_handlers.py`
- **역할**: FastAPI 예외 핸들러 등록
- **책임**:
  - 도메인 예외를 HTTP 예외로 변환
  - 일관된 에러 응답 형식 제공
  - `register_exception_handlers(app)` 함수 제공
- **수정 시 주의사항**:
  - 새로운 도메인 예외가 추가되면 여기에 핸들러를 등록하세요
  - 엔드포인트에서 직접 예외 변환 로직을 작성하지 마세요
  - `side_service.py`의 예외 클래스에 의존합니다

### `logger_config.py`
- **역할**: 로깅 설정
- **책임**:
  - 애플리케이션 전역 로깅 설정
  - `get_logger()`, `log_method_call` 데코레이터 제공
- **수정 시 주의사항**:
  - 로깅 설정만 담당하며, 다른 비즈니스 로직을 포함하지 마세요

## 모듈 간 의존성 관계

```
websocket_manager.py
  ├── side_service.py
  │   ├── repositories/side_repository.py
  │   ├── parser.py
  │   └── loader.py
  │       └── models.py
  ├── session_pool.py
  ├── repositories/lock_repository.py
  └── runner.py
      └── models.py

side_service.py
  ├── repositories/side_repository.py
  ├── parser.py
  ├── loader.py
  │   └── models.py
  └── (예외 클래스 정의)

runner.py
  └── models.py

exception_handlers.py
  └── side_service.py (예외 클래스)
```

## 인수인계 시 확인사항

이 디렉토리의 코드를 수정할 때 다음을 확인하세요:

1. ✅ 모듈의 원래 책임을 벗어나지 않았는가?
2. ✅ 로직 중복이 발생하지 않았는가? (특히 Side 파일 로드/렌더링)
3. ✅ 의존성 방향이 올바른가? (상위 → 하위 레이어)
4. ✅ Repository 패턴을 준수하고 있는가?
5. ✅ 예외 처리가 `exception_handlers.py`에 등록되어 있는가?

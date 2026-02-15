# Pan

**Pan**은 그리스 신화의 양치기 신으로, 양들을 목장에 풀어놓고 풀을 뜯어먹게 하며 양털을 취하는 것처럼, 이 프로젝트는 HTML이라는 풀을 뜯어먹고 데이터라는 양털을 취하는 FastAPI 기반 웹 서버입니다.

![양치기 그림](documents/shepherd.png)

*그림 0: 양치기 소년 그림*

Selenium Grid를 활용한 세션 풀링과 동시성 제어를 통해 안정적이고 효율적인 크롤링 실행 환경을 제공합니다.

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
- **세션 재활용을 하니까 동시에 하나의 세션을 사용하면 간섭이 일어나네..**
  - 요청당 Lock을 부여해서 동시성 제어를 구현해보자!
- **아니 네이버에 검색하는 시나리오를 키워드마다 녹화해야 하나? 녹화 작업에 시간을 너무 많이 쏟아야 하는데..**
  - Side 파일 자체를 Jinja2 템플릿화해서 1번의 녹화로 N개의 시나리오로 만들어보자!

## 이거 어떻게 사용하는 거에요?

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

### 시연 영상 4: 템플릿 파라미터를 활용한 동적 시나리오 실행

![demo](documents/demo-make-dynamic-side.gif)

*영상 4-1: Jinja2 템플릿이 포함된 Side 시나리오를 생성하는 과정*

![demo](documents/demo-siderun-dynamic.gif)

*영상 4-2: Jinja2 템플릿이 포함된 Side 파일에 다양한 파라미터를 전달하여 동적으로 시나리오를 실행하는 과정*

## 그래서 의도한 대로 성과가 나왔나요?

1. **크롤링 속도 최적화**
    - **순차 실행 vs 병렬 실행**: 전자 작업(약 20분)을 후자 작업(약 2분)로 단축

2. **세션 Pool 확보 최적화**
    - **세션 확보 X vs 세션 확보 O**:  전자 작업(약 11초)을 후자 작업(약 6초)로 단축

3. **템플릿 엔진을 통한 파라미터 활용성 극대화**
    - **10개 키워드 검색에 대한 녹화작업 vs 동적 파라미터로 10개 키워드 검색 녹화작업**:  전자 작업(약 18분)을 후자 작업(약 2분)로 단축

4. **세션 Pool 초기화 작업의 비동기 처리**
    - **동기적 세션 확보 vs 비동기적 세션 확보**: 동기적 세션 확보 작업(약 2분)을 비동기적 세션 확보 작업(약 5초)로 단축


## 프로젝트 구조

이 프로젝트는 **단일 책임 원칙(SRP)**과 **관심사의 분리(SoC)**를 엄격히 준수하도록 설계되었습니다. 각 모듈은 명확한 역할과 책임을 가지며, 모듈 간 의존성은 최소화되어 있습니다.

### ⚠️ 중요: 코드 수정 시 주의사항

**이 프로젝트의 모듈 구조는 신중하게 설계된 책임 분리를 기반으로 합니다. 코드를 수정하기 전에 반드시 다음 사항을 확인하세요:**

1. **모듈 간 의존성 방향을 확인하세요**
   - 상위 레이어(API) → 서비스 레이어 → 도메인 레이어 → 인프라 레이어 순서로 의존해야 합니다
   - 역방향 의존성을 만들지 마세요

2. **각 모듈의 책임 범위를 벗어나지 마세요**
   - 예: `session_pool.py`는 세션 관리만 담당하며, Lock 관련 로직은 포함하지 않습니다
   - 예: `websocket_manager.py`는 웹소켓 연결 관리만 담당하며, Side 파일 로드/렌더링은 `SideService`에 위임합니다

3. **로직 중복을 만들지 마세요**
   - 공통 로직은 적절한 서비스나 유틸리티 모듈에 위치시켜야 합니다
   - 예: Side 파일 로드/렌더링은 `SideService`에만 존재해야 합니다

4. **Repository 패턴을 준수하세요**
   - 데이터 영속성 로직은 반드시 `repositories/` 디렉토리의 인터페이스를 통해 접근해야 합니다
   - 직접 파일 시스템 접근을 하지 마세요

5. **예외 처리는 `exception_handlers.py`에서 관리합니다**
   - 도메인 예외는 커스텀 예외 클래스로 정의하고, HTTP 예외 변환은 예외 핸들러에서 처리합니다
   - 엔드포인트에서 직접 예외 변환 로직을 작성하지 마세요

### 디렉토리 구조

```
pan/
├── main.py                           # FastAPI 애플리케이션 진입점
├── src/
│   ├── models.py                     # 도메인 모델 정의
│   ├── loader.py                     # Side 파일 JSON 파싱
│   ├── parser.py                     # Jinja2 템플릿 렌더링
│   ├── runner.py                     # Selenium 명령 실행 엔진
│   ├── side_service.py              # Side 파일 로드/렌더링 서비스
│   ├── session_pool.py              # Selenium Grid 세션 풀 관리
│   ├── websocket_manager.py         # 웹소켓 연결 및 세션 관리
│   ├── exception_handlers.py         # FastAPI 예외 핸들러 등록
│   ├── logger_config.py             # 로깅 설정
│   ├── README.md                     # src/ 디렉토리 모듈 상세 설명
│   └── repositories/                 # 저장소 패턴 구현
│       ├── side_repository.py       # Side 파일 저장소 인터페이스
│       ├── filesystem_side_repository.py  # FileSystem 기반 구현체
│       ├── lock_repository.py       # Lock 관리 인터페이스
│       ├── filesystem_lock_repository.py # FileSystem 기반 구현체
│       └── README.md                 # repositories/ 디렉토리 모듈 상세 설명
└── storage/
    ├── sides/                        # Side 파일 저장 디렉토리
    ├── locks/                        # Lock 파일 저장 디렉토리
    └── js/                           # JavaScript 파일 저장 디렉토리
```

### 각 모듈의 역할과 책임

> **상세한 모듈 설명은 각 디렉토리의 README.md를 참조하세요:**
> - `src/README.md`: src/ 디렉토리의 모든 모듈 상세 설명
> - `src/repositories/README.md`: repositories/ 디렉토리의 모든 모듈 상세 설명

#### `main.py`
- **역할**: FastAPI 애플리케이션 진입점 및 HTTP 엔드포인트 정의
- **책임**: FastAPI 앱 초기화, REST API/웹소켓 엔드포인트 정의, 의존성 주입
- **수정 시 주의사항**: 비즈니스 로직은 서비스 레이어에 위임, 예외 처리는 `exception_handlers.py` 사용

#### `src/` 디렉토리
- **상세 설명**: [src/README.md](src/README.md) 참조
- 주요 모듈:
  - `models.py`: 도메인 모델 정의
  - `loader.py`: Side 파일 JSON 파싱
  - `parser.py`: Jinja2 템플릿 렌더링
  - `runner.py`: Selenium 명령 실행 엔진
  - `side_service.py`: Side 파일 로드/렌더링 서비스
  - `session_pool.py`: Selenium Grid 세션 풀 관리
  - `websocket_manager.py`: 웹소켓 연결 및 세션 관리
  - `exception_handlers.py`: FastAPI 예외 핸들러 등록

#### `src/repositories/` 디렉토리
- **상세 설명**: [src/repositories/README.md](src/repositories/README.md) 참조
- 주요 모듈:
  - `side_repository.py`: Side 파일 저장소 인터페이스
  - `filesystem_side_repository.py`: FileSystem 기반 구현체
  - `lock_repository.py`: Lock 관리 인터페이스 및 세션 필터링
  - `filesystem_lock_repository.py`: FileSystem 기반 구현체

### 모듈 간 의존성 관계

```
main.py (API Layer)
  ├── side_service.py (Service Layer)
  │   ├── side_repository.py (Infrastructure Layer)
  │   ├── parser.py (Domain Layer)
  │   └── loader.py (Domain Layer)
  ├── websocket_manager.py (Service Layer)
  │   ├── side_service.py
  │   ├── session_pool.py (Infrastructure Layer)
  │   └── lock_repository.py (Infrastructure Layer)
  ├── runner.py (Domain Layer)
  │   └── models.py (Domain Layer)
  └── exception_handlers.py (API Layer)
      └── side_service.py (예외 클래스)
```

### 인수인계 시 확인사항

새로운 개발자나 AI 에이전트가 코드를 수정할 때 다음을 확인하세요:

1. **모듈의 원래 책임을 벗어나지 않았는가?**
2. **로직 중복이 발생하지 않았는가?** (특히 Side 파일 로드/렌더링)
3. **의존성 방향이 올바른가?** (상위 → 하위 레이어)
4. **예외 처리가 `exception_handlers.py`에 등록되어 있는가?**
5. **Repository 패턴을 준수하고 있는가?**

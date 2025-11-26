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

## API 문서 확인:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

![Swagger UI](documents/swagger-ui-screenshot.png)
*그림 7: Swagger UI를 통한 API 테스트 예시*

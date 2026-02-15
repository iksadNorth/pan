# src/repositories/ 디렉토리

이 디렉토리는 **Repository 패턴**을 구현하여 데이터 영속성을 추상화합니다. 인터페이스와 구현체를 분리하여 저장소 구현을 쉽게 교체할 수 있도록 설계되었습니다.

## ⚠️ 수정 시 주의사항

Repository 패턴의 핵심 원칙을 준수하세요:

1. **인터페이스와 구현체를 명확히 분리하세요**
   - 인터페이스는 비즈니스 로직과 무관한 순수한 데이터 접근 메서드만 정의합니다
   - 구현체는 특정 저장소 기술(FileSystem, Database 등)에 의존합니다

2. **비즈니스 로직을 포함하지 마세요**
   - Repository는 데이터 저장/조회만 담당합니다
   - 비즈니스 로직은 서비스 레이어(`side_service.py` 등)에 위치해야 합니다

3. **Lock 관련 로직은 `LockRepository`에 위치합니다**
   - 세션 필터링(`filter_available_sessions()`) 같은 Lock 관련 로직은 `LockRepository`에 있습니다
   - `SessionPool`에는 Lock 의존성을 추가하지 마세요

## 모듈 목록

### `side_repository.py`
- **역할**: Side 파일 저장소 인터페이스 정의
- **책임**:
  - `SideRepository` 추상 클래스 정의
  - `save()`, `get()`, `list_all()`, `delete()`, `exists()` 메서드 인터페이스
- **수정 시 주의사항**:
  - 인터페이스만 정의하고 구현 로직을 포함하지 마세요
  - 새로운 저장소 구현체를 추가할 때는 이 인터페이스를 구현하세요

### `filesystem_side_repository.py`
- **역할**: FileSystem 기반 Side 파일 저장소 구현체
- **책임**:
  - 파일 시스템을 사용한 Side 파일 저장/조회/삭제
  - JSON 유효성 검사
  - 안전한 파일명 변환
- **수정 시 주의사항**:
  - 비즈니스 로직을 포함하지 마세요
  - 파일 경로 처리 시 보안을 고려하세요 (경로 순회 공격 방지)
  - `side_repository.py`의 인터페이스를 정확히 구현해야 합니다

### `lock_repository.py`
- **역할**: Lock 관리 인터페이스 및 세션 필터링
- **책임**:
  - `LockRepository` 추상 클래스 정의
  - `acquire()`, `release()`, `get_lock_info()`, `is_locked()` 메서드 인터페이스
  - `filter_available_sessions()` 메서드: Lock이 잠겨있지 않은 세션 필터링
  - `LockInfo` 데이터 클래스 정의
- **수정 시 주의사항**:
  - **`filter_available_sessions()`는 Lock 관련 로직이므로 여기에 위치합니다**
  - `SessionPool`에 Lock 의존성을 추가하지 마세요
  - TTL(Time To Live) 기능을 지원합니다

### `filesystem_lock_repository.py`
- **역할**: FileSystem 기반 Lock 관리 구현체
- **책임**:
  - 파일 시스템을 사용한 Lock 생성/해제/조회
  - Lock 만료 시간 관리 (TTL)
  - Lock UUID 생성 및 관리
  - 만료된 Lock 자동 정리
- **수정 시 주의사항**:
  - Lock 파일과 Lock 정보 파일(`.lock.json`)을 분리하여 관리합니다
  - `_acquire_with_ttl_internal()` 같은 내부 메서드는 웹소켓 같은 특수한 경우에만 사용됩니다
  - `lock_repository.py`의 인터페이스를 정확히 구현해야 합니다

## Repository 패턴의 장점

1. **저장소 구현 교체 용이**: FileSystem → Database로 변경 시 구현체만 교체하면 됩니다
2. **테스트 용이성**: Mock Repository를 쉽게 만들 수 있습니다
3. **비즈니스 로직과 데이터 접근 로직 분리**: 단일 책임 원칙 준수

## 모듈 간 의존성

```
side_service.py
  └── side_repository.py (인터페이스)
      └── filesystem_side_repository.py (구현체)

websocket_manager.py
  └── lock_repository.py (인터페이스)
      └── filesystem_lock_repository.py (구현체)

main.py
  ├── side_repository.py
  └── lock_repository.py
```

## 인수인계 시 확인사항

이 디렉토리의 코드를 수정할 때 다음을 확인하세요:

1. ✅ 인터페이스와 구현체가 명확히 분리되어 있는가?
2. ✅ 비즈니스 로직이 포함되지 않았는가?
3. ✅ 새로운 저장소 구현체를 추가할 때 인터페이스를 정확히 구현했는가?
4. ✅ Lock 관련 로직이 `LockRepository`에 위치하는가? (`SessionPool`에 추가하지 않았는가?)

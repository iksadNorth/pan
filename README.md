## Selenium IDE 사이드 러너

이 프로젝트는 Selenium IDE가 내보내는 `.side` 파일을 직접 읽어 Selenium WebDriver로 실행할 수 있는 간단한 러너를 제공합니다.

### 요구 사항

- Python 3.10+
- 로컬에 설치된 브라우저 드라이버 (Chrome / Firefox / Edge)
- `pip install -e .` 로 의존성 설치

### 사용법

```bash
python -m ide-lab list ./examples/sample.side
python -m ide-lab run ./examples/sample.side --suite "Default Suite"
python -m ide-lab run ./examples/sample.side --test "로그인" --browser firefox --headless
```

옵션:

- `--suite`: 실행할 Suite 이름 (기본값: 첫 번째 Suite)
- `--test`: Suite 대신 단일 테스트 실행
- `--browser`: `chrome`, `firefox`, `edge`
- `--base-url`: `.side` 파일의 기본 URL을 덮어쓰기
- `--headless`: 헤드리스 모드로 실행
- `--implicit-wait`: 암묵적 대기 시간 (초)

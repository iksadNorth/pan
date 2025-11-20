FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 도구 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# uv 설치
RUN pip install --no-cache-dir uv

# 의존성 파일만 먼저 복사 (레이어 캐싱 최적화)
COPY pyproject.toml ./
COPY uv.lock* ./

# 의존성 설치 (uv를 사용하여 더 빠르게 설치)
RUN uv pip install --system --no-cache -e .

# 애플리케이션 코드 복사
COPY src/ ./src/
COPY main.py ./

# storage 디렉토리 생성
RUN mkdir -p /app/storage/sides /app/storage/locks

# 포트 노출
EXPOSE 8000

# 서버 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


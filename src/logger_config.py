"""로깅 설정 모듈."""

from __future__ import annotations

import logging
import os
from pathlib import Path


def setup_logging(log_dir: Path | str | None = None) -> logging.Logger:
    """로깅을 설정하고 루트 로거를 반환합니다.

    Args:
        log_dir: 로그 파일을 저장할 디렉토리 경로.
                 None이면 환경 변수 LOG_DIR을 사용하고,
                 환경 변수도 없으면 ./logs/api-server를 사용합니다.

    Returns:
        설정된 루트 로거
    """
    # 로그 디렉토리 설정
    if log_dir is None:
        log_dir = Path(os.getenv("LOG_DIR", "./logs/api-server"))
    else:
        log_dir = Path(log_dir)

    log_dir.mkdir(parents=True, exist_ok=True)

    # 파일 핸들러 설정
    log_file = log_dir / "api.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 기존 핸들러 제거 (중복 방지)
    root_logger.handlers.clear()

    # 핸들러 추가
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """이름으로 로거를 가져옵니다.

    Args:
        name: 로거 이름 (일반적으로 __name__ 사용)

    Returns:
        로거 인스턴스
    """
    return logging.getLogger(name)


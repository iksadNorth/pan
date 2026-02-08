"""jinja2 템플릿에서 사용할 Parser 클래스."""

from __future__ import annotations

import json
import os
import random
import string
from datetime import datetime
from pathlib import Path

from faker import Faker
from jinja2 import Template


class Parser:
    """jinja2 템플릿에서 사용할 Parser 객체.
    
    dict처럼 접근 가능하며, 메서드도 추가할 수 있습니다.
    예: {{ parser['key'] }}, {{ parser.getRandomNumber() }}
    """
    
    def __init__(self, params: dict[str, str] | None = None):
        """Parser를 초기화합니다.
        
        Args:
            params: 파라미터 딕셔너리
        """
        self._params = params or {}
        # 환경 변수에서 읽거나 기본값 사용 (시스템 설정이므로 클라이언트에서 조절 불가)
        default_dir = os.getenv("JS_STORAGE_DIR", "./storage/js")
        self._js_storage_dir = Path(default_dir)
    
    def render(self, side_content: str) -> str:
        """dict처럼 접근: parser['key']"""
        template = Template(side_content)
        faker = self.getFaker()
        return template.render(
            parser=self,
            faker=faker,
        )
    
    def __getitem__(self, key: str) -> str:
        """dict처럼 접근: parser['key']"""
        return self._params.get(key, "")
    
    def get(self, key: str, default: str = "") -> str:
        """dict.get()과 동일한 동작"""
        return self._params.get(key, default)
    
    def getToday(self, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        """현재시간을 표현합니다.
        
        Returns:
            현재시각. 
        """
        return datetime.now().strftime(format)
    
    def getRandomNumber(self, min_val: int = 0, max_val: int = 1000000) -> int:
        """랜덤 숫자를 반환합니다.
        
        Args:
            min_val: 최소값 (기본값: 0)
            max_val: 최대값 (기본값: 1000000)
        
        Returns:
            랜덤 정수
        """
        return random.randint(min_val, max_val)
    
    def getRandomString(self, length: int = 10) -> str:
        """랜덤 문자열을 반환합니다.
        
        Args:
            length: 문자열 길이 (기본값: 10)
        
        Returns:
            랜덤 문자열
        """
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def getFaker(self) -> Faker:
        """한국 로케이션으로 설정된 Faker 객체를 반환합니다.
        
        Returns:
            Faker 객체 (ko_KR 로케이션)
        
        사용 예:
            {{ faker.name() }}
            {{ faker.email() }}
            {{ faker.phone_number() }}
        """
        return Faker('ko_KR')
    
    def js_file(self, filename: str) -> str:
        """JS 파일을 읽어서 Jinja2 템플릿으로 렌더링한 후 JSON-safe 문자열로 반환합니다.
        
        JS 코드가 JSON의 comment 필드에 들어갈 때 제어 문자를 이스케이프 처리합니다.
        실제 실행 시에는 자동으로 언이스케이프되어 원래 JS 코드로 실행됩니다.
        
        Args:
            filename: JS 파일명 (예: "remove-old-elements.js")
        
        Returns:
            JSON-safe하게 이스케이프된 JS 코드 (개행 문자 등이 \\n 형태로 변환됨)
        
        사용 예:
            {{ parser.js_file('remove-old-elements.js') }}
        
        Raises:
            FileNotFoundError: JS 파일을 찾을 수 없을 때
        """
        js_file_path = self._js_storage_dir / filename
        if not js_file_path.exists():
            raise FileNotFoundError(f"JS 파일을 찾을 수 없습니다: {js_file_path}")
        
        # JS 파일 읽기
        js_content = js_file_path.read_text(encoding="utf-8")
        
        # Jinja2 템플릿으로 렌더링 (재귀적으로 parser와 faker 사용 가능)
        template = Template(js_content)
        rendered_js = template.render(
            parser=self,
            faker=self.getFaker(),
        )
        
        # JSON-safe하게 이스케이프 처리 (개행 문자 등을 \\n 형태로 변환)
        # json.dumps를 사용하면 문자열이 JSON-safe하게 이스케이프되고, 
        # 앞뒤의 따옴표를 제거하면 실제 JS 코드로 사용 가능
        return json.dumps(rendered_js)[1:-1]  # 앞뒤 따옴표 제거


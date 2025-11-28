"""jinja2 템플릿에서 사용할 Parser 클래스."""

from __future__ import annotations

import random
import string
from datetime import datetime

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


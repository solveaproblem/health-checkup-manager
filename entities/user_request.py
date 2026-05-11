from dataclasses import dataclass, field


@dataclass
class UserRequest:
    year: int
    requests: list[str] = field(default_factory=list)   # 검사 부위 키워드 (뇌, 허리 등)
    must_have: list[str] = field(default_factory=list)  # 꼭 포함되어야 할 검진 항목 (복부CT, 대장내시경 등)

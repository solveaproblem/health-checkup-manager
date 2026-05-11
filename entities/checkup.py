from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CheckupItem:
    raw_name: str
    value: float
    unit: str
    ref_range: str
    status: str                     # "정상" | "경계" | "이상"
    standard_key: Optional[str] = None


@dataclass
class Finding:
    text: str
    follow_up: bool = False
    category: Optional[str] = None


@dataclass
class CheckupResult:
    year: int
    hospital: str
    program: str
    items: dict[str, CheckupItem] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

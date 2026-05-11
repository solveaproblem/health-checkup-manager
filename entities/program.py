from dataclasses import dataclass, field


@dataclass
class Program:
    name: str
    price: int
    items: list[str] = field(default_factory=list)       # 필수 포함 항목
    optional_items: dict = field(default_factory=dict)   # 선택 항목
    notes: str = ""


@dataclass
class Hospital:
    name: str
    programs: list[Program] = field(default_factory=list)


@dataclass
class ProgramCatalog:
    year: int
    hospitals: list[Hospital] = field(default_factory=list)

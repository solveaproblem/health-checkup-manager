import json
from pathlib import Path
from entities import CheckupResult, CheckupItem, Finding, ProgramCatalog, Hospital, Program, UserRequest


class JsonRepository:
    def __init__(self, base_dir: str = "data"):
        self.base = Path(base_dir)
        self.checkups_dir = self.base / "checkups"
        self.programs_dir = self.base / "programs"
        self.requests_dir = self.base / "requests"
        self.aliases_file = self.base / "aliases.json"
        for d in [self.checkups_dir, self.programs_dir, self.requests_dir]:
            d.mkdir(parents=True, exist_ok=True)
        if not self.aliases_file.exists():
            self.aliases_file.write_text("{}", encoding="utf-8")

    # ── 별칭 ──────────────────────────────────────────────
    def get_aliases(self) -> dict:
        return json.loads(self.aliases_file.read_text(encoding="utf-8"))

    def save_alias(self, raw_name: str, standard_key: str):
        aliases = self.get_aliases()
        aliases[raw_name] = standard_key
        self.aliases_file.write_text(json.dumps(aliases, ensure_ascii=False, indent=2), encoding="utf-8")

    def resolve_key(self, raw_name: str) -> str:
        aliases = self.get_aliases()
        return aliases.get(raw_name, raw_name)

    # ── 검진 결과 ──────────────────────────────────────────
    def save_checkup(self, result: CheckupResult):
        path = self.checkups_dir / f"{result.year}.json"
        data = {
            "year": result.year,
            "hospital": result.hospital,
            "program": result.program,
            "items": {
                k: {
                    "raw_name": v.raw_name,
                    "value": v.value,
                    "unit": v.unit,
                    "ref_range": v.ref_range,
                    "status": v.status,
                    "standard_key": v.standard_key,
                }
                for k, v in result.items.items()
            },
            "findings": [
                {"text": f.text, "follow_up": f.follow_up, "category": f.category}
                for f in result.findings
            ],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_checkup(self, year: int) -> CheckupResult | None:
        path = self.checkups_dir / f"{year}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        items = {
            k: CheckupItem(**v) for k, v in data["items"].items()
        }
        findings = [Finding(**f) for f in data["findings"]]
        return CheckupResult(
            year=data["year"],
            hospital=data["hospital"],
            program=data["program"],
            items=items,
            findings=findings,
        )

    def list_checkup_years(self) -> list[int]:
        return sorted(int(p.stem) for p in self.checkups_dir.glob("*.json"))

    # ── 병원/프로그램 ──────────────────────────────────────
    def save_program_catalog(self, catalog: ProgramCatalog):
        path = self.programs_dir / f"{catalog.year}.json"
        data = {
            "year": catalog.year,
            "hospitals": [
                {
                    "name": h.name,
                    "programs": [
                        {"name": p.name, "price": p.price, "items": p.items, "optional_items": p.optional_items, "notes": p.notes}
                        for p in h.programs
                    ],
                }
                for h in catalog.hospitals
            ],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_program_catalog(self, year: int) -> ProgramCatalog | None:
        path = self.programs_dir / f"{year}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        hospitals = [
            Hospital(
                name=h["name"],
                programs=[Program(**p) for p in h["programs"]],
            )
            for h in data["hospitals"]
        ]
        return ProgramCatalog(year=data["year"], hospitals=hospitals)

    # ── 사용자 요구사항 ────────────────────────────────────
    def save_user_request(self, req: UserRequest):
        path = self.requests_dir / f"{req.year}.json"
        data = {"year": req.year, "requests": req.requests, "must_have": req.must_have}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_user_request(self, year: int) -> UserRequest | None:
        path = self.requests_dir / f"{year}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return UserRequest(
            year=data["year"],
            requests=data.get("requests", []),
            must_have=data.get("must_have", []),
        )

    # ── 프로그램 연도 목록 ─────────────────────────────────────────────────
    def list_program_years(self) -> list[int]:
        return sorted(int(p.stem) for p in self.programs_dir.glob("*.json"))

    # ── 항목 매핑 ──────────────────────────────────────────────────────────
    def get_item_mapping(self) -> dict:
        path = self.base / "item_mapping.json"
        if not path.exists():
            return {"confirmed": {}, "unconfirmed": []}
        return json.loads(path.read_text(encoding="utf-8"))

    def save_item_mapping(self, mapping: dict):
        path = self.base / "item_mapping.json"
        path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

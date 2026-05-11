from entities import CheckupResult, CheckupItem, Finding
from infrastructure.repositories import JsonRepository


class SaveCheckup:
    def __init__(self, repo: JsonRepository):
        self.repo = repo

    def execute(self, data: dict) -> CheckupResult:
        items = {}
        for raw_name, v in data.get("items", {}).items():
            standard_key = self.repo.resolve_key(raw_name)
            items[standard_key] = CheckupItem(
                raw_name=raw_name,
                value=v["value"],
                unit=v.get("unit", ""),
                ref_range=v.get("ref_range", ""),
                status=v.get("status", "알수없음"),
                standard_key=standard_key,
            )

        findings = [
            Finding(
                text=f["text"],
                follow_up=f.get("follow_up", False),
                category=f.get("category"),
            )
            for f in data.get("findings", [])
        ]

        result = CheckupResult(
            year=data["year"],
            hospital=data["hospital"],
            program=data.get("program", ""),
            items=items,
            findings=findings,
        )
        self.repo.save_checkup(result)
        return result

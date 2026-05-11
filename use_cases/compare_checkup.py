from infrastructure.repositories import JsonRepository


class CompareCheckup:
    def __init__(self, repo: JsonRepository):
        self.repo = repo

    def execute(self, years: list[int] | None = None) -> dict:
        all_years = years or self.repo.list_checkup_years()
        results = {y: self.repo.get_checkup(y) for y in all_years}
        results = {y: r for y, r in results.items() if r}

        # 전체 항목 키 수집
        all_keys = set()
        for r in results.values():
            all_keys.update(r.items.keys())

        # raw_name 수집 (가장 최근 연도 기준)
        raw_names: dict[str, str] = {}
        for year in sorted(results.keys(), reverse=True):
            for key, item in results[year].items.items():
                if key not in raw_names:
                    raw_names[key] = item.raw_name

        comparison = {}
        for key in all_keys:
            comparison[key] = {
                "raw_name": raw_names.get(key, key),
                "years": {},
            }
            for year, result in sorted(results.items()):
                item = result.items.get(key)
                if item:
                    comparison[key]["years"][year] = {
                        "value": item.value,
                        "unit": item.unit,
                        "status": item.status,
                        "ref_range": item.ref_range,
                    }
                else:
                    comparison[key]["years"][year] = None

        # 이상 수 내림차순, 경계 수 내림차순, 동점이면 key 알파벳순
        def sort_key(item):
            key, data = item
            abnormal = sum(1 for v in data["years"].values() if v and v["status"] == "이상")
            borderline = sum(1 for v in data["years"].values() if v and v["status"] == "경계")
            return (-abnormal, -borderline, key)

        sorted_comparison = dict(sorted(comparison.items(), key=sort_key))

        return {
            "years": sorted(results.keys()),
            "comparison": sorted_comparison,
        }

from infrastructure.repositories import JsonRepository


class GetFollowups:
    def __init__(self, repo: JsonRepository):
        self.repo = repo

    def execute(self) -> list[dict]:
        followups = []
        for year in self.repo.list_checkup_years():
            result = self.repo.get_checkup(year)
            if not result:
                continue
            for f in result.findings:
                if f.follow_up:
                    followups.append({
                        "year": year,
                        "category": f.category,
                        "text": f.text,
                    })
        return followups

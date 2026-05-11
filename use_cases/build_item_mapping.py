"""
BuildItemMapping 유스케이스

서버 시작 시 실행되어:
1. 모든 checkup 연도의 standard_key/raw_name을 수집
2. 모든 program 연도의 항목명을 수집
3. 규칙 기반 매칭으로 confidence 계산
4. confirmed 매핑은 그대로 유지, 새로 발견된 항목만 unconfirmed에 추가
"""

import re
from infrastructure.repositories import JsonRepository


SYNONYM_MAP: dict[str, list[str]] = {
    "total_cholesterol":  ["t.cholesterol", "총콜레스테롤"],
    "ldl_cholesterol":    ["ldl cholesterol", "ldl-chol", "저밀도콜레스테롤"],
    "hdl_cholesterol":    ["hdl cholesterol", "hdl-chol", "고밀도콜레스테롤"],
    "triglyceride":       ["triglyceride", "중성지방"],
    "crf":                ["심장위험인자"],
    "sgot":               ["ast(s-got)", "sgot"],
    "sgpt":               ["alt(s-gpt)", "sgpt"],
    "ggt":                ["r-gtp", "ggt", "감마-지티피"],
    "alp":                ["alp"],
    "d_bilirubin":        ["d.bilirubin", "직접빌리루빈"],
    "fasting_glucose":    ["glucose", "공복혈당"],
    "hba1c":              ["hba1c", "당화혈색소"],
    "creatinine":         ["creatinine", "크레아티닌"],
    "bun":                ["bun", "혈중요소질소"],
    "gfr":                ["gfr"],
    "tsh":                ["tsh"],
    "ft4":                ["free t4"],
    "wbc":                ["wbc"],
    "rbc":                ["rbc"],
    "hemoglobin":         ["hb", "hemoglobin", "혈색소"],
    "hct":                ["hct"],
    "platelets":          ["platelet", "혈소판"],
    "pdw":                ["pdw"],
    "fe":                 ["빈혈/fe", "fe"],
    "crp":                ["crp"],
    "uric_acid":          ["uric acid", "요산"],
    "ca19_9":             ["ca19-9"],
    "afp":                ["afp"],
    "cea":                ["cea"],
    "psa":                ["psa"],
    "vitamin_d":          ["vitamin d", "비타민d"],
    "testosterone":       ["testosteron", "남성호르몬"],
    "visceral_fat":       ["복부지방ct", "복부ct"],
    "fat_amount_ratio":   ["복부지방ct", "복부ct"],
    "bone_density_t_score": ["골밀도"],
    "bmi":                ["bmi", "체질량지수"],
    "weight":             ["신체계측"],
    "waist":              ["신체계측"],
    "systolic_bp":        ["혈압"],
    "diastolic_bp":       ["혈압"],
    "pulse":              ["ekg", "심전도"],
}

CATEGORY_MAP: dict[str, list[str]] = {
    "total_cholesterol":  ["혈중지질"],
    "ldl_cholesterol":    ["혈중지질"],
    "hdl_cholesterol":    ["혈중지질"],
    "triglyceride":       ["혈중지질"],
    "crf":                ["혈중지질", "순환기"],
    "sgot":               ["간기능"],
    "sgpt":               ["간기능"],
    "ggt":                ["간기능"],
    "alp":                ["간기능"],
    "d_bilirubin":        ["간기능"],
    "fasting_glucose":    ["당뇨"],
    "hba1c":              ["당뇨"],
    "creatinine":         ["신장기능"],
    "bun":                ["신장기능"],
    "gfr":                ["신장기능"],
    "tsh":                ["갑상선기능"],
    "ft4":                ["갑상선기능"],
    "wbc":                ["혈액질환"],
    "rbc":                ["혈액질환"],
    "hemoglobin":         ["혈액질환"],
    "hct":                ["혈액질환"],
    "platelets":          ["혈액질환"],
    "pdw":                ["혈액질환"],
    "fe":                 ["빈혈"],
    "crp":                ["면역/염증"],
    "uric_acid":          ["근골격계"],
    "ca19_9":             ["종양표지자"],
    "afp":                ["종양표지자"],
    "cea":                ["종양표지자"],
    "psa":                ["종양표지자"],
    "vitamin_d":          ["비타민"],
    "testosterone":       ["남성", "호르몬"],
    "visceral_fat":       ["CT"],
    "fat_amount_ratio":   ["CT"],
    "bone_density_t_score": ["골밀도"],
    "systolic_bp":        ["기초검사"],
    "diastolic_bp":       ["기초검사"],
    "bmi":                ["기초검사"],
    "weight":             ["기초검사"],
    "waist":              ["기초검사"],
    "pulse":              ["기초검사"],
}


def _normalize(text: str) -> str:
    return re.sub(r"[\s\-_./()（）]", "", text.lower())


def _score_match(standard_key: str, raw_name: str, program_item: str) -> float:
    prog_item_part = program_item.split("/")[-1].lower() if "/" in program_item else program_item.lower()
    prog_item_norm = _normalize(prog_item_part)
    prog_item_tokens = re.findall(r"[a-zA-Z가-힣]{2,}", prog_item_part)
    prog_item_tokens_norm = {_normalize(t) for t in prog_item_tokens}

    score = 0.0

    synonyms = SYNONYM_MAP.get(standard_key, [])
    for syn in synonyms:
        syn_norm = _normalize(syn)
        if syn_norm in prog_item_norm or prog_item_norm in syn_norm:
            score += 0.6
            break

    tokens = re.findall(r"[a-zA-Z가-힣]{3,}", raw_name.lower())
    for token in tokens:
        tok_norm = _normalize(token)
        if tok_norm in prog_item_tokens_norm:
            score += 0.3
            break

    prog_category = program_item.split("/")[0].lower() if "/" in program_item else ""
    categories = CATEGORY_MAP.get(standard_key, [])
    for cat in categories:
        if _normalize(cat) in _normalize(prog_category):
            score += 0.2
            break

    return min(score, 1.0)


class BuildItemMapping:
    CONFIDENCE_AUTO_CONFIRM = 0.6

    def __init__(self, repo: JsonRepository):
        self.repo = repo

    def execute(self) -> dict:
        mapping = self.repo.get_item_mapping()
        confirmed: dict[str, list[str]] = mapping.get("confirmed", {})
        unconfirmed: list[dict] = mapping.get("unconfirmed", [])
        existing_unconfirmed_keys = {u["standard_key"] for u in unconfirmed}

        checkup_items: dict[str, str] = {}
        for year in self.repo.list_checkup_years():
            result = self.repo.get_checkup(year)
            if not result:
                continue
            for key, item in result.items.items():
                if key not in checkup_items:
                    checkup_items[key] = item.raw_name

        all_program_items: list[str] = []
        for year in self.repo.list_program_years():
            catalog = self.repo.get_program_catalog(year)
            if not catalog:
                continue
            for hospital in catalog.hospitals:
                for program in hospital.programs:
                    all_program_items.extend(program.items)
                    for group in (program.optional_items or {}).values():
                        all_program_items.extend(group.get("items", []))
        all_program_items = list(dict.fromkeys(all_program_items))

        new_confirmed = 0
        new_unconfirmed = 0

        for std_key, raw_name in checkup_items.items():
            if std_key in confirmed:
                continue

            scored = []
            for prog_item in all_program_items:
                s = _score_match(std_key, raw_name, prog_item)
                if s > 0:
                    scored.append((s, prog_item))

            scored.sort(key=lambda x: -x[0])
            top = scored[:5]

            if not top:
                continue

            best_score = top[0][0]
            best_items = [item for score, item in top if score == best_score]

            if best_score >= self.CONFIDENCE_AUTO_CONFIRM:
                confirmed[std_key] = best_items
                new_confirmed += 1
            else:
                if std_key not in existing_unconfirmed_keys:
                    unconfirmed.append({
                        "standard_key": std_key,
                        "raw_name": raw_name,
                        "confidence": round(best_score, 2),
                        "candidates": [
                            {"item": item, "score": round(score, 2)}
                            for score, item in top
                        ],
                        "note": "자동 매핑 실패 — 수동 확인 후 confirmed에 추가하세요",
                    })
                    existing_unconfirmed_keys.add(std_key)
                    new_unconfirmed += 1

        self.repo.save_item_mapping({
            "_readme": "confirmed: 확정 매핑. unconfirmed: 자동 추론 실패 — 검토 필요.",
            "confirmed": confirmed,
            "unconfirmed": unconfirmed,
        })

        return {
            "total_checkup_keys": len(checkup_items),
            "total_program_items": len(all_program_items),
            "new_confirmed": new_confirmed,
            "new_unconfirmed": new_unconfirmed,
            "confirmed_total": len(confirmed),
            "unconfirmed_total": len(unconfirmed),
        }

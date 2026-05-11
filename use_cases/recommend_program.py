"""
RecommendProgram 유스케이스

추천 시나리오:
1. 검사부위만 입력 → 해당 부위 관련 항목을 포함하는 조합만 후보, 그 중 needed 최다 커버
2. 검진항목만 입력 → 해당 항목을 포함하는 조합만 후보, 그 중 needed 최다 커버
3. 둘 다 입력     → 검사부위 AND 검진항목 모두 포함하는 조합만 후보, 그 중 needed 최다 커버
4. 아무것도 없음  → 전체 조합 대상, needed 최다 커버
5. 매칭 0개       → 명확한 안내 메시지
"""

import re
import time
from itertools import combinations
from pathlib import Path
import json

from infrastructure.repositories import JsonRepository


# ── 상수 사전 ────────────────────────────────────────────────────────────────

FOLLOWUP_DUPLICATE_MAP: dict[str, str] = {
    "비타민d": "vitamin_d",
    "갑상선":  "tsh",
}

# followup category 중 프로그램으로 커버 불가한 항목 (needed에서 제외)
FOLLOWUP_SKIP_CATEGORIES: set[str] = {
    "생활습관/음주", "심뇌혈관위험도", "흉부/폐", "심전도", "골밀도",
    "간염", "혈액/a형간염", "혈액/b형간염", "유전자/암위험도",
    "복부비만", "비만", "간/간탄성도mri",
    # 기본 검진 포함 항목
    "신장/신장석회화", "비만/체중", "혈액/혈당", "혈액/당화혈색소", "복부/비만",
    # 등록된 프로그램에 없는 항목
    "안과/안저", "눈/안저검사",
}

DERIVED_ITEM_MAP: dict[str, str] = {
    "fat_amount_ratio": "visceral_fat",
}

FOLLOWUP_CATEGORY_MAP: dict[str, list[str]] = {
    "지질/콜레스테롤":              ["T.Cholesterol", "LDL Cholesterol", "HDL Cholesterol", "Triglyceride"],
    "내분비/이상지질혈증":          ["T.Cholesterol", "LDL Cholesterol", "HDL Cholesterol", "Triglyceride"],
    "혈액/콜레스테롤":              ["T.Cholesterol", "LDL Cholesterol", "HDL Cholesterol", "Triglyceride"],
    "혈액/이상지질혈증":            ["T.Cholesterol", "LDL Cholesterol", "HDL Cholesterol", "Triglyceride"],
    "비타민d":                      ["비타민D", "Vitamin D"],
    "내분비/비타민d":               ["비타민D", "Vitamin D"],
    "혈액/비타민d":                 ["비타민D", "Vitamin D"],
    "간/지방간":                    ["상복부초음파", "간스캔초음파"],
    "간/국소지방침착안된조직":      ["상복부초음파", "간스캔초음파"],
    "간·담낭/초음파":               ["상복부초음파", "간스캔초음파"],
    "담낭/용종":                    ["상복부초음파", "간스캔초음파"],
    "갑상선":                       ["갑상선초음파", "TSH", "Free T4", "Free T3"],
    "갑상선/결절":                  ["갑상선초음파"],
    "갑상선/낭종":                  ["갑상선초음파"],
    "경동맥/동맥경화":              ["경동맥초음파", "동맥경화검사", "MRA검사_경동맥"],
    "순환기/동맥경화":              ["경동맥초음파", "동맥경화검사"],
    "순환기/심혈관위험인자":        ["동맥경화검사", "경동맥초음파"],
    "심뇌혈관위험도":               ["동맥경화검사", "경동맥초음파"],
    "위/위내시경":                  ["위내시경", "상부내시경", "헬리코박터"],
    "위/만성표재성위염":            ["위내시경", "상부내시경"],
    "위/역류성식도염·미란성위염":   ["위내시경", "상부내시경"],
    "식도/역류성식도염":            ["위내시경", "상부내시경"],
    "대장/내시경":                  ["대장내시경"],
    "대장/용종·게실":               ["대장내시경"],
    "대장/게실":                    ["대장내시경"],
    "요추/척추":                    ["MRI검사_요추", "요추CT", "MRI검사_경추", "경추CT"],
    "심뇌혈관":                     ["경동맥초음파", "동맥경화검사", "심장초음파", "MRA검사_뇌혈관"],
    "눈/안저검사":                  ["안저"],
    "안과/안저":                    ["안저"],
}

KEYWORD_TO_ITEMS: dict[str, list[str]] = {
    "허리":       ["요추", "MRI검사_요추", "요추CT"],
    "척추":       ["요추", "MRI검사_요추", "요추CT", "경추", "MRI검사_경추", "경추CT"],
    "목":         ["경추", "MRI검사_경추", "경추CT"],
    "경추":       ["경추", "MRI검사_경추", "경추CT"],
    "요추":       ["요추", "MRI검사_요추", "요추CT"],
    "뇌":         ["뇌CT", "MRI검사_뇌", "MRA검사_뇌혈관"],
    "머리":       ["뇌CT", "MRI검사_뇌", "MRA검사_뇌혈관"],
    "뇌혈관":     ["MRA검사_뇌혈관"],
    "심장":       ["심장초음파", "심장 석회화", "심장(CK)", "심장(LDH)", "심장(호모시스테인)"],
    "혈관":       ["경동맥초음파", "동맥경화검사", "MRA검사_뇌혈관"],
    "경동맥":     ["경동맥초음파"],
    "폐":         ["폐CT", "폐활량", "Cyfra21-1"],
    "위":         ["위내시경", "헬리코박터"],
    "대장":       ["대장내시경"],
    "간":         ["상복부초음파", "간스캔초음파"],
    "담낭":       ["상복부초음파"],
    "췌장":       ["상복부초음파", "Amylase", "Lipase"],
    "갑상선":     ["갑상선초음파", "TSH", "Free T4", "Free T3"],
    "골밀도":     ["골밀도검사"],
    "뼈":         ["골밀도검사"],
    "비타민":     ["비타민D"],
    "전립선":     ["전립선초음파", "PSA"],
    "콜레스테롤": ["T.Cholesterol", "LDL", "HDL", "Triglyceride"],
    "지질":       ["T.Cholesterol", "LDL", "HDL", "Triglyceride"],
    "혈당":       ["Glucose", "HbA1c"],
    "당뇨":       ["Glucose", "HbA1c"],
    "암":         ["대장내시경", "폐CT", "AFP", "CEA", "CA19-9", "PSA", "Cyfra21-1"],
    "소화기":     ["위내시경", "대장내시경", "상복부초음파", "헬리코박터"],
}

MUST_HAVE_ALIASES: dict[str, list[str]] = {
    "복부ct":       ["복부지방CT", "복부CT"],
    "복부지방ct":   ["복부지방CT"],
    "대장내시경":   ["대장내시경"],
    "위내시경":     ["위내시경"],
    "골밀도":       ["골밀도검사"],
    "경동맥초음파": ["경동맥초음파"],
    "심장초음파":   ["심장초음파"],
    "갑상선초음파": ["갑상선초음파"],
    "비타민d":      ["비타민D"],
    "뇌ct":         ["뇌CT"],
    "폐ct":         ["폐CT"],
    "mri":          ["MRI"],
    "mra":          ["MRA"],
}


# ── 헬퍼 함수 ────────────────────────────────────────────────────────────────

def _load_basic_items(base_dir: str) -> set:
    path = Path(base_dir) / "basic_items.json"
    if not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")).get("items", {}).keys())


def _item_text(item: str) -> str:
    return item.split("/")[-1] if "/" in item else item


def _combo_item_parts(combo: set) -> set[str]:
    return {_item_text(i).lower() for i in combo}


def _combo_lower(combo: set) -> set[str]:
    return {i.lower() for i in combo}


def _resolve_keyword_targets(keywords: list[str]) -> list[str]:
    targets = []
    for kw in keywords:
        kw_lower = kw.lower().strip()
        matched = False
        for key, vals in KEYWORD_TO_ITEMS.items():
            if key in kw_lower or kw_lower in key:
                targets.extend(vals)
                matched = True
        if not matched:
            targets.append(kw_lower)
    return list(dict.fromkeys(targets))


def _combo_covers_targets(combo_lower: set[str], combo_parts: set[str], targets: list[str]) -> bool:
    for t in targets:
        t_lower = t.lower()
        for ci in combo_lower:
            if t_lower in ci or ci in t_lower:
                return True
    return False


def _get_all_combinations(program) -> list[tuple[set, dict]]:
    base = set(program.items)
    opt = program.optional_items or {}

    if not opt:
        return [(base, {})]

    group_options = []
    for group_name, group_info in opt.items():
        items = group_info.get("items", [])
        count = min(group_info.get("count", 1), len(items))
        if items:
            group_options.append((group_name, [list(c) for c in combinations(items, count)]))

    if not group_options:
        return [(base, {})]

    result = [(base, {})]
    for group_name, options in group_options:
        new_result = []
        for existing_set, existing_groups in result:
            for option in options:
                new_result.append((existing_set | set(option), {**existing_groups, group_name: option}))
        result = new_result

    return result


def _score_needed(combo: set, needed: list[dict], confirmed_mapping: dict) -> tuple[int, list, list]:
    parts = _combo_item_parts(combo)
    covered, not_covered = [], []

    for n in needed:
        std_key = n["key"]
        matched = False

        if std_key.startswith("followup_"):
            cat_raw = n["raw"].lower()
            map_targets = next(
                (vals for k, vals in FOLLOWUP_CATEGORY_MAP.items() if k in cat_raw or cat_raw in k),
                None
            )
            if map_targets:
                matched = any(t.lower() in p or p in t.lower() for t in map_targets for p in parts)
            else:
                cat_parts = [p.strip() for p in re.split(r"[/,]", cat_raw) if len(p.strip()) >= 2]
                matched = any(cp in p or p in cp for cp in cat_parts for p in parts)

        elif std_key in confirmed_mapping:
            matched = any(
                _item_text(m).lower() in parts or any(_item_text(m).lower() in p for p in parts)
                for m in confirmed_mapping[std_key]
            )
        else:
            raw_lower = n["raw"].lower()
            matched = any(raw_lower in p or p in raw_lower for p in parts)

        (covered if matched else not_covered).append(n)

    return len(covered), covered, not_covered


# ── 유스케이스 ───────────────────────────────────────────────────────────────

class RecommendProgram:

    def __init__(self, repo: JsonRepository):
        self.repo = repo

    def execute(self, year: int) -> dict:
        start_time = time.time()
        basic_items = _load_basic_items(self.repo.base)
        confirmed_mapping = self.repo.get_item_mapping().get("confirmed", {})

        # ── 1. needed 항목 수집 ──────────────────────────────────────────
        needed: list[dict] = []
        seen_keys: set = set()

        for y in sorted(self.repo.list_checkup_years()):
            result = self.repo.get_checkup(y)
            if not result:
                continue

            # 수치이상: 최신 연도 값으로 덮어씀
            for key, item in result.items.items():
                if item.status not in ("경계", "이상") or key in basic_items:
                    continue
                if DERIVED_ITEM_MAP.get(key) in {n["key"] for n in needed}:
                    continue
                existing = next((n for n in needed if n["key"] == key), None)
                if existing:
                    existing["detail"] = f"{y}년 {item.status} ({item.value} {item.unit})"
                else:
                    needed.append({"key": key, "raw": item.raw_name, "type": "수치이상",
                                   "detail": f"{y}년 {item.status} ({item.value} {item.unit})"})
                    seen_keys.add(key)

            # 추적관찰 소견 처리
            for f in result.findings:
                if not f.category:
                    continue
                cat_key = f"followup_{f.category}"

                if f.follow_up:
                    # 추적관찰 필요: 아직 없으면 추가, 있으면 최신 연도로 업데이트
                    if cat_key in seen_keys:
                        existing = next((n for n in needed if n["key"] == cat_key), None)
                        if existing:
                            existing["detail"] = f"{y}년 소견: {f.text[:40]}"
                        continue

                    # skip 조건 확인
                    dup_key = FOLLOWUP_DUPLICATE_MAP.get(f.category.lower().replace(" ", ""))
                    if dup_key and dup_key in {n["key"] for n in needed}:
                        seen_keys.add(cat_key)
                        continue
                    if f.category.lower().replace(" ", "") in FOLLOWUP_SKIP_CATEGORIES:
                        seen_keys.add(cat_key)
                        continue

                    needed.append({"key": cat_key, "raw": f.category, "type": "추적관찰",
                                   "detail": f"{y}년 소견: {f.text[:40]}"})
                    seen_keys.add(cat_key)

                else:
                    # follow_up=False: 이전에 추적관찰로 등록된 항목이면 해결된 것으로 제거
                    if cat_key in seen_keys:
                        needed = [n for n in needed if n["key"] != cat_key]
                        # seen_keys에는 유지 (재등록 방지)

        # ── 2. 사용자 입력 파싱 ──────────────────────────────────────────
        user_req = self.repo.get_user_request(year)
        # requests: 프로그램 대분류 필터 (예: ["뇌신경특화", "척추특화"])
        # 선택된 대분류가 있으면 해당 대분류 프로그램만 후보로 고려
        area_types = [r.strip() for r in (user_req.requests if user_req else []) if r.strip()]
        must_have_keywords = [m.strip() for m in (user_req.must_have if user_req else []) if m.strip()]
        has_area = bool(area_types)
        has_must = bool(must_have_keywords)

        def _prog_type(program_name: str) -> str:
            """프로그램명에서 대분류 추출: "뇌신경특화 (1차 검진전문기관)" → "뇌신경특화" """
            import re
            return re.sub(r'\s*\([^)]+\)', '', program_name).strip()

        # ── 3. 카탈로그 확인 ─────────────────────────────────────────────
        catalog = self.repo.get_program_catalog(year)
        if not catalog:
            return {"error": f"{year}년 등록된 병원/프로그램 정보가 없습니다.",
                    "tip": "먼저 프로그램 정보를 등록해주세요."}

        # ── 4. 브루트포스 탐색 ───────────────────────────────────────────
        total_combos = 0
        candidates = []

        for hospital in catalog.hospitals:
            for program in hospital.programs:
                # 대분류 필터: 선택된 대분류가 있으면 해당 프로그램만 후보
                if has_area and _prog_type(program.name) not in area_types:
                    continue
                all_combos = _get_all_combinations(program)
                total_combos += len(all_combos)
                best = None

                for combo, groups in all_combos:
                    cl = _combo_lower(combo)
                    cp = _combo_item_parts(combo)

                    if has_must:
                        def _kw_in_combo(kw: str) -> bool:
                            kw_l = kw.lower().strip()
                            aliases = MUST_HAVE_ALIASES.get(kw_l, [kw_l])
                            for alias in aliases:
                                alias_l = alias.lower()
                                for ci in cl:
                                    if alias_l in ci or ci in alias_l:
                                        return True
                            return False
                        if not all(_kw_in_combo(kw) for kw in must_have_keywords):
                            continue

                    n_score, covered, not_covered = _score_needed(combo, needed, confirmed_mapping)

                    if best is None or n_score > best[0]:
                        best = (n_score, combo, groups, covered, not_covered)

                if best is None:
                    continue

                n_score, best_combo, best_groups, covered, not_covered = best
                base_set = set(program.items)
                selected_by_group = {
                    g: {
                        "count": program.optional_items[g]["count"],
                        "items": [_item_text(i) for i in items if i not in base_set],
                    }
                    for g, items in best_groups.items()
                    if any(i not in base_set for i in items)
                }

                candidates.append({
                    "hospital": hospital.name,
                    "program": program.name,
                    "price": program.price,
                    "need_score": n_score,
                    "covered": covered,
                    "not_covered": not_covered,
                    "selected_by_group": selected_by_group,
                    "total_combos": len(all_combos),
                })

        elapsed = round(time.time() - start_time, 2)

        # ── 5. 매칭 없음 처리 ────────────────────────────────────────────
        if not candidates:
            if has_area and has_must:
                msg = f"'{', '.join(area_types)}' 프로그램에서 '{', '.join(must_have_keywords)}' 항목을 포함하는 조합이 없습니다."
                tip = "프로그램 분류 또는 필수 항목 조건을 완화해보세요."
            elif has_area:
                msg = f"'{', '.join(area_types)}' 프로그램을 찾지 못했습니다."
                tip = "다른 분류를 선택하거나, 선택 없이 추천받아보세요."
            elif has_must:
                msg = f"'{', '.join(must_have_keywords)}' 항목을 포함하는 프로그램이 없습니다."
                tip = "다른 항목명으로 시도하거나, 입력 없이 추천받아보세요."
            else:
                msg = "비교할 프로그램이 없습니다."
                tip = ""
            return {"error": msg, "tip": tip}

        # ── 6. 정렬 및 동점 처리 ─────────────────────────────────────────
        candidates.sort(key=lambda x: (-x["need_score"], len(x["not_covered"])))
        best_score = candidates[0]["need_score"]
        top = [c for c in candidates if c["need_score"] == best_score]
        is_tie = len(top) > 1
        top = top[:5]

        # ── 7. never_covered: 전체 candidates 기준 ───────────────────────
        all_covered_keys = {n["key"] for c in candidates for n in c["covered"]}
        never_covered = [n for n in needed if n["key"] not in all_covered_keys]

        return {
            "has_area": has_area,
            "has_must": has_must,
            "area_keywords": area_types,
            "must_have_keywords": must_have_keywords,
            "needed_count": len(needed),
            "is_tie": is_tie,
            "top_programs": [
                {
                    "hospital": c["hospital"],
                    "program": c["program"],
                    "price": c["price"],
                    "need_score": c["need_score"],
                    "covered": [{"item": n["raw"], "type": n["type"], "detail": n["detail"]}
                                for n in c["covered"]],
                    "not_covered": [{"item": n["raw"], "type": n["type"], "detail": n["detail"]}
                                    for n in c["not_covered"]],
                    "selected_by_group": c["selected_by_group"],
                    "total_combos": c["total_combos"],
                }
                for c in top
            ],
            "never_covered": [{"item": n["raw"], "type": n["type"], "detail": n["detail"]}
                               for n in never_covered],
            "total_combos_checked": total_combos,
            "elapsed_seconds": elapsed,
        }

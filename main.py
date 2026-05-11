import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from infrastructure.repositories import JsonRepository
from entities import ProgramCatalog, Hospital, Program, UserRequest
from use_cases import SaveCheckup, CompareCheckup, GetFollowups, RecommendProgram, BuildItemMapping

repo = JsonRepository(base_dir=str(Path(__file__).parent / "data"))

def clear_user_requests():
    requests_dir = Path(__file__).parent / "data" / "requests"
    if requests_dir.exists():
        for f in requests_dir.glob("*.json"):
            f.unlink()

def _run_item_mapping():
    uc = BuildItemMapping(repo)
    result = uc.execute()
    print(f"[item_mapping] confirmed={result['confirmed_total']} "
          f"(+{result['new_confirmed']}), "
          f"unconfirmed={result['unconfirmed_total']} "
          f"(+{result['new_unconfirmed']})")
    if result['new_unconfirmed'] > 0:
        print(f"[item_mapping] ⚠ 검토 필요 항목 {result['new_unconfirmed']}개 → data/item_mapping.json 의 unconfirmed 확인")

app = FastAPI(title="건강검진 이력 관리 시스템")

clear_user_requests()
_run_item_mapping()

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    ico = bytes([
        0,0,1,0,1,0,1,1,0,0,1,0,32,0,40,0,0,0,
        40,0,0,0,1,0,0,0,2,0,0,0,1,0,32,0,0,0,
        0,0,4,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    ])
    return Response(content=ico, media_type="image/x-icon")


# ── 페이지 ─────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


# ── 검진 결과 ───────────────────────────────────────────
class CheckupPayload(BaseModel):
    year: int
    hospital: str
    program: str = ""
    items: dict = {}
    findings: list = []


@app.post("/api/checkup")
async def save_checkup(payload: CheckupPayload):
    uc = SaveCheckup(repo)
    result = uc.execute(payload.model_dump())
    return {"ok": True, "year": result.year, "hospital": result.hospital}


@app.get("/api/checkup/{year}")
async def get_checkup(year: int):
    result = repo.get_checkup(year)
    if not result:
        raise HTTPException(404, f"{year}년 데이터 없음")
    return {
        "year": result.year,
        "hospital": result.hospital,
        "program": result.program,
        "items": {k: vars(v) for k, v in result.items.items()},
        "findings": [vars(f) for f in result.findings],
    }


@app.get("/api/checkup")
async def list_checkups():
    return {"years": repo.list_checkup_years()}


@app.get("/api/compare")
async def compare():
    uc = CompareCheckup(repo)
    return uc.execute()


@app.get("/api/followups")
async def followups():
    uc = GetFollowups(repo)
    return {"followups": uc.execute()}


# ── 별칭 관리 ───────────────────────────────────────────
class AliasPayload(BaseModel):
    raw_name: str
    standard_key: str


@app.post("/api/alias")
async def save_alias(payload: AliasPayload):
    repo.save_alias(payload.raw_name, payload.standard_key)
    return {"ok": True}


@app.get("/api/alias")
async def get_aliases():
    return repo.get_aliases()


# ── 병원/프로그램 ────────────────────────────────────────
class ProgramPayload(BaseModel):
    year: int
    hospitals: list


@app.post("/api/program")
async def save_program(payload: ProgramPayload):
    hospitals = [
        Hospital(
            name=h["name"],
            programs=[Program(**p) for p in h["programs"]],
        )
        for h in payload.hospitals
    ]
    catalog = ProgramCatalog(year=payload.year, hospitals=hospitals)
    repo.save_program_catalog(catalog)
    return {"ok": True}


@app.get("/api/program/{year}")
async def get_program(year: int):
    catalog = repo.get_program_catalog(year)
    if not catalog:
        raise HTTPException(404, f"{year}년 프로그램 없음")
    return catalog


# ── 사용자 요구사항 ─────────────────────────────────────
class UserRequestPayload(BaseModel):
    year: int
    requests: list[str] = []
    must_have: list[str] = []


@app.post("/api/request")
async def save_request(payload: UserRequestPayload):
    req = UserRequest(year=payload.year, requests=payload.requests, must_have=payload.must_have)
    repo.save_user_request(req)
    return {"ok": True}


@app.delete("/api/request/{year}")
async def delete_request(year: int):
    path = Path(repo.base) / "requests" / f"{year}.json"
    if path.exists():
        path.unlink()
    return {"ok": True}


# ── 추천 ────────────────────────────────────────────────
@app.get("/api/recommend/{year}")
async def recommend(year: int):
    uc = RecommendProgram(repo)
    try:
        result = uc.execute(year)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

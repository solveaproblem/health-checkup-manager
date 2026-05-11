# 건강검진 이력 관리 시스템

과거 건강검진 결과를 연도별로 관리하고, 올해 받을 검진 프로그램을 AI가 추천해주는 개인용 웹 애플리케이션입니다.

---

## 주요 기능

- **대시보드**: 연도별 검진 이력 요약 및 추적관찰 항목 확인
- **연도 비교**: 항목별 수치 추세 그래프 및 연도별 비교
- **추적관찰**: 의사 소견에서 추적관찰이 필요한 항목 목록
- **검진 추천**: 과거 이상 소견을 분석해 올해 최적 검진 프로그램 추천
- **결과 입력**: 새 검진 결과 JSON 입력
- **프로그램 등록**: 병원별 검진 프로그램 정보 등록

---

## 설치 방법

### 1. Python 설치

Python 3.11 이상이 필요합니다.
- 다운로드: https://www.python.org/downloads/
- 설치 시 **"Add Python to PATH"** 체크 필수

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 실행

**Windows:**
```bash
start.bat
```
또는
```bash
python main.py
```

### 4. 접속

브라우저에서 http://127.0.0.1:8000 접속

---

## 데이터 구조

```
data/
├── checkups/          ← 연도별 검진 결과 (직접 추가)
│   ├── 2023.json
│   ├── 2024.json
│   └── 2025.json
├── programs/          ← 연도별 병원/검진 프로그램 정보
│   └── 2026.json
├── aliases.json       ← 소견 카테고리 매핑 (자동 관리)
├── basic_items.json   ← 기본 검진 항목 목록 (자동 관리)
└── item_mapping.json  ← 검진 항목 매핑 (자동 관리)
```

---

## 검진 결과 JSON 만들기

### AI 도구(ChatGPT, Claude 등)에 요청하는 방법

검진 결과지(PDF 또는 사진)를 AI 도구에 첨부하고 아래와 같이 요청하세요:

---

**요청 예시:**

> 첨부한 건강검진 결과지를 아래 JSON 형식으로 변환해줘.
> 
> ```json
> {
>   "year": 2025,
>   "hospital": "병원명",
>   "program": "",
>   "items": {
>     "standard_key": {
>       "raw_name": "결과지에 표시된 항목명",
>       "value": 수치값(숫자),
>       "unit": "단위",
>       "ref_range": "정상범위",
>       "status": "정상 또는 경계 또는 이상"
>     }
>   },
>   "findings": [
>     {
>       "text": "소견 내용",
>       "follow_up": true,
>       "category": "소견 카테고리"
>     }
>   ]
> }
> ```
> 
> - `standard_key`는 영문 소문자+언더스코어로 항목을 식별하는 키 (예: `ldl_cholesterol`, `fasting_glucose`)
> - `status`는 반드시 `"정상"`, `"경계"`, `"이상"` 중 하나
> - `follow_up`은 의사가 추적관찰/재검을 권고한 경우 `true`, 정상 소견은 `false`
> - `category`는 소견의 분류 (예: `"지질/콜레스테롤"`, `"위/위내시경"`, `"갑상선"`)

---

### 주요 standard_key 목록

| standard_key | 항목명 |
|---|---|
| `height` | 신장 |
| `weight` | 체중 |
| `bmi` | 체질량지수(BMI) |
| `waist` | 허리둘레 |
| `systolic_bp` | 수축기 혈압 |
| `diastolic_bp` | 이완기 혈압 |
| `fasting_glucose` | 공복혈당 |
| `hba1c` | 당화혈색소 |
| `total_cholesterol` | 총콜레스테롤 |
| `ldl_cholesterol` | LDL 콜레스테롤 |
| `hdl_cholesterol` | HDL 콜레스테롤 |
| `triglyceride` | 중성지방 |
| `sgot` | AST(GOT) |
| `sgpt` | ALT(GPT) |
| `ggt` | 감마-GTP |
| `tsh` | 갑상선자극호르몬 |
| `creatinine` | 크레아티닌 |
| `gfr` | 사구체여과율 |
| `vitamin_d` | 비타민D |
| `visceral_fat` | 내장지방(복부CT) |
| `wbc` | 백혈구수 |
| `rbc` | 적혈구수 |
| `hemoglobin` | 혈색소 |
| `platelets` | 혈소판 |
| `uric_acid` | 요산 |
| `crp` | CRP(정량) |
| `bone_density_t_score` | 골밀도 T-score |
| `psa` | PSA(전립선특이항원) |
| `cea` | CEA |
| `afp` | AFP |
| `ca19_9` | CA19-9 |
| `testosterone` | 남성호르몬 |

---

### JSON 파일 저장 위치

변환된 JSON을 `data/checkups/연도.json` 으로 저장합니다.

예: `data/checkups/2024.json`

---

## 검진 프로그램 등록

올해 받을 수 있는 병원별 검진 프로그램 정보를 등록해야 추천 기능을 사용할 수 있습니다.

웹 UI의 **🏥 프로그램 등록** 탭에서 JSON 형식으로 입력하거나,
`data/programs/연도.json` 파일을 직접 생성합니다.

프로그램 JSON 형식:
```json
{
  "year": 2026,
  "hospitals": [
    {
      "name": "병원명",
      "programs": [
        {
          "name": "종합검진 (1차 검진전문기관)",
          "price": 350000,
          "items": [
            "기초검사/신체계측",
            "혈중지질/T.Cholesterol",
            "혈중지질/LDL Cholesterol"
          ],
          "optional_items": {
            "A": {
              "count": 1,
              "items": [
                "초음파/경동맥초음파",
                "CT/폐CT (저선량)",
                "MR/MRI검사_뇌"
              ]
            }
          },
          "notes": "선택A(1개): 경동맥초음파, 폐CT..."
        }
      ]
    }
  ]
}
```

---

## 자주 묻는 질문

**Q. 서버 시작이 느려요.**
A. 처음 실행 시 검진 항목 매핑을 자동으로 구성합니다. 잠시 기다리면 정상 동작합니다.

**Q. 추천 결과가 안 나와요.**
A. `data/programs/올해연도.json` 파일이 있어야 합니다. 프로그램 등록 탭에서 먼저 등록해주세요.

**Q. 검진 결과를 수정하고 싶어요.**
A. `data/checkups/연도.json` 파일을 직접 편집하거나, 결과 입력 탭에서 다시 저장하면 덮어씁니다.

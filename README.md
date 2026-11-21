# 올팍 운동 시간표

한국체육산업개발 4개 센터(올림픽수영장, 올림픽공원스포츠센터, 분당·일산 올림픽스포츠센터)의 강좌를 센터 가입 없이 **요일·시간대**로 한 번에 찾는 웹 화면입니다.
2026 한국체육산업개발 공공데이터 활용 경진대회 출품 시제품이며, 기관 공식 서비스가 아닙니다.

## 기능
- 요일·시작 시간대·센터·종목으로 강좌 찾기 (기본값: 평일 저녁·밤)
- 종목별 묶음: 강좌 수, 월 수강료 범위, 센터별 1회당 최저가
- 앞으로 4주 대형 공연일(KSPO DOME·올림픽홀·티켓링크 라이브 아레나) 달력, 겹치는 강좌에 '공연일' 표시
- 수강신청 바로가기, 매주 반복 일정(.ics) 만들기
- 운영 리포트(`#report`): 센터별 시작 시간대 정원, 종목·센터별 1회당 가격, 데이터 기준 월

## 파일 구성
| 파일 | 설명 |
|---|---|
| `index.html` | 화면 전체(HTML·CSS·JS 한 파일, 외부 라이브러리 없음) |
| `olpark.json` | 화면용 데이터(강좌 1,294개, 공연일 61회분) |
| `PretendardGOV-sub.woff2` | 정부 공식 서체 Pretendard GOV, 쓰는 글자만 남긴 파일(SIL OFL) |
| `.nojekyll` | GitHub Pages가 파일을 그대로 쓰게 하는 빈 파일 |
| `scripts/build_data.py` | 원본 CSV + 공연 일정 → `olpark.json` |
| `scripts/fetch_events.py` | 올림픽공원 일정안내의 공연 목록 받기 → `data_raw/events.json` |
| `.github/workflows/update-events.yml` | 매일 05:17(한국 시간) 공연 일정을 받아 바뀌었으면 `olpark.json`을 다시 만들어 올림 |
| `scripts/dl_filedata.py` | 공공데이터포털 파일데이터 내려받기 |
| `data_raw/g_*.csv` | 강좌정보 원본 4종(UTF-8로 변환한 것) |
| `data_raw/events.json` | 공연 일정(자동 갱신) |

디자인 기준: 범정부 UI/UX 디자인 시스템(KRDS) — 정부 청색 #256EF4, Pretendard GOV, 본문 17px, 버튼 48px.

## 내 컴퓨터에서 보기
`olpark.json`을 불러오므로 파일을 더블클릭하면 안 열립니다. 간단한 서버로 엽니다.
```bash
python3 -m http.server 8765
# 브라우저에서 http://localhost:8765
```

## GitHub Pages에 올리기
1. GitHub에서 **New repository** → 이름 예: `olpark-timetable` → **Public** → Create.
2. 저장소 화면의 **uploading an existing file**을 눌러 이 폴더의 파일을 모두 끌어 넣고 **Commit changes**.
   (`.nojekyll`처럼 점으로 시작하는 파일이 안 보이면 빼도 동작합니다.)
3. **Settings → Pages → Build and deployment → Source: Deploy from a branch**, Branch `main` / `/(root)` → Save.
4. 1~2분 뒤 `https://<아이디>.github.io/olpark-timetable/` 에서 열립니다. 이 주소를 기획서 1-3에 적습니다.

## 데이터 다시 만들기 (제출 직전 공연 일정 갱신 등)
1. 강좌정보(필요할 때만):
   ```bash
   for pk in 15101610 15110953 15118652 15114776; do python3 -I scripts/dl_filedata.py $pk data_raw/g_$pk.bin; done
   for f in data_raw/g_*.bin; do iconv -f cp949 -t utf-8 "$f" > "${f%.bin}.csv"; done
   ```
2. 공연 일정: **자동으로 갱신됩니다**(GitHub Actions '공연 일정 자동 갱신', 매일). 직접 받으려면 `python3 -I scripts/fetch_events.py data_raw/events.json 3` (이번 달부터 3개월). `events.json`이 없으면 예전 방식대로 일정안내 페이지를 저장한 `data_raw/ev.html`을 읽습니다.
3. 가공:
   ```bash
   pip install pandas
   python3 -I scripts/build_data.py data_raw olpark.json
   ```
4. 화면에 없던 글자가 새 데이터에 생기면 서체 파일을 다시 만듭니다(없으면 기본 서체로 표시될 뿐 동작엔 문제 없음).

## 처리 규칙 요약
- **현재 강좌**: 센터별 가장 최근 등록 월 + 최근 6개월 안에 등록되어 기간이 끝나지 않은 강좌. 같은 강좌명·시간·요일은 하나로.
- **시간 일치**: 강좌의 모든 요일이 고른 요일에 들고, 시작 시각이 고른 시간대 안.
- **공연 겹침**: 대형 공연장 3곳, 공연 시작 2시간 전~3시간 후와 강좌 시간이 겹치면 표시(가정값).
- **1회당 가격**: 월 수강료 ÷ (주당 횟수 × 4.3주).

## 자료 출처
공공데이터포털 한국체육산업개발 강좌정보 — 올림픽수영장(15101610), 올림픽스포츠센터(15110953), 분당(15118652), 일산(15114776). 올림픽공원 공연·행사 일정안내.
정확한 시간·수강료·신청은 한국체육산업개발 수강신청 누리집에서 확인하십시오.

## 공연일 알림 구독 (2026-11 추가)
- `scripts/make_feeds.py` 가 올림픽공원 안 두 센터 강좌마다 `feeds/c_<강좌번호>.ics` 를 만든다. 강좌 시간이 대형 공연 시작 2시간 전~3시간 후와 겹치는 날만 일정이 들어가고, 전날·수업 2시간 전 알림이 붙는다.
- 강좌번호는 센터·강좌명·시간·요일로 만든 고정값이라 데이터가 갱신돼도 구독 주소가 유지된다.
- 매일 자동 갱신 작업이 공연 일정과 함께 다시 만든다. 회원 정보는 모으지 않는다.
- 운영 리포트의 「공연일 겹침 강좌 명단」은 센터가 자기 수강생 연락처로 안내 문자를 보낼 수 있게 CSV로 내려받는다.
- 종목 카드의 「강좌 소개·수준별 진도」 링크는 스포츠센터 강좌 정보(공공데이터 15147992, `data_raw/course_info.csv`)와 종목 이름으로 연결한다(현재 강좌의 약 96%).

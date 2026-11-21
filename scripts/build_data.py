"""4개 센터 강좌 CSV + 올림픽공원 공연 일정 HTML -> 화면용 olpark.json
사용: python3 -I scripts/build_data.py data_raw olpark.json
"""
import sys, os, re, json, html as H, datetime as dt
import pandas as pd

RAW, OUT = sys.argv[1], sys.argv[2]
DAYS = "월화수목금토일"

SPEC = [  # 파일, 센터명, 공원내 여부, 칸 이름 매핑
    ("g_15101610.csv", "올림픽수영장", True,
     dict(월="시작월", 종목="강좌코드명", 시간="시작종료시간", 요일="요일", 대상="강습반", 금액="강좌금액", 기간="시작일자")),
    ("g_15110953.csv", "올림픽공원스포츠센터", True,
     dict(월="수강월", 종목="종목", 시간="수강시간", 요일="수강요일", 대상="수강대상", 금액="수강금액", 종료="수강종료일")),
    ("g_15118652.csv", "분당올림픽스포츠센터", False,
     dict(월="수강월", 종목="종목", 시간="시작종료시간", 요일="수강요일", 대상="수강대상", 금액="수강료", 종료="기간종료일")),
    ("g_15114776.csv", "일산올림픽스포츠센터", False,
     dict(월="시작월", 종목="종목", 시간="시작종료시간", 요일="요일", 대상="강습반", 금액="금액", 기간="시작일")),
]
DATASET = {"올림픽수영장": "15101610", "올림픽공원스포츠센터": "15110953",
           "분당올림픽스포츠센터": "15118652", "일산올림픽스포츠센터": "15114776"}


def hm(s):
    m = re.match(r"\s*(\d{1,2}):?(\d{2})", s or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def parse_time(s):
    parts = re.split(r"[~\-]", str(s))
    if len(parts) < 2:
        return None, None
    return hm(parts[0]), hm(parts[1])


def parse_days(s):
    s = str(s)
    return [i for i, d in enumerate(DAYS) if d in s.replace("(토)", "")]


courses, stats = [], {}
for fn, center, inpark, m in SPEC:
    d = pd.read_csv(f"{RAW}/{fn}", dtype=str)
    d["월"] = d[m["월"]].str[:7]
    d = d[(d["월"] >= "2013-01") & (d["월"] <= "2026-12")]  # 4025년 등 오기 제외
    if "기간" in m:
        d["종료"] = d[m["기간"]].str.split("~").str[-1].str[:7]
    else:
        d["종료"] = d[m["종료"]].str[:7]
    ref = d["월"].max()
    y, mo = int(ref[:4]), int(ref[5:7]) - 6
    if mo <= 0:
        y, mo = y - 1, mo + 12
    win = f"{y}-{mo:02d}"  # 최근 6개월 안에 등록된 강좌만 (종료일 9999 오래된 강좌 제외)
    act = d[(d["월"] == ref) | ((d["월"] < ref) & (d["월"] > win) & (d["종료"] >= ref))].copy()
    act["s"], act["e"] = zip(*act[m["시간"]].map(parse_time))
    act["days"] = act[m["요일"]].map(parse_days)
    act = act.sort_values("월").drop_duplicates(["강좌명", m["시간"], m["요일"]], keep="last")
    n0 = len(act)
    act = act[act["s"].notna() & act["days"].map(len).gt(0)]
    for _, r in act.iterrows():
        price = pd.to_numeric(str(r[m["금액"]]).replace(",", ""), errors="coerce")
        cap = pd.to_numeric(r["정원"], errors="coerce")
        courses.append(dict(
            c=center, park=inpark, sp=str(r[m["종목"]]).strip(), n=str(r["강좌명"]).strip(),
            s=int(r["s"]), e=int(r["e"]) if r["e"] == r["e"] and r["e"] else int(r["s"]) + 50,
            d=r["days"], t=(str(r[m["대상"]]).strip() if r[m["대상"]] == r[m["대상"]] else ""),
            p=None if price != price else int(price), cap=None if cap != cap else int(cap), m=r["월"]))
    stats[center] = dict(ref=ref, win=win, rows=len(d), active=n0, used=len(act), dataset=DATASET[center])

# ---- 공연 일정 ----
# 입력 1순위: data_raw/events.json (scripts/fetch_events.py 가 올림픽공원 일정안내의 목록 API에서 받은 것)
# 입력 2순위: data_raw/ev.html (일정안내 페이지를 브라우저에서 저장한 것)
DAYMAP = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}
for i, k in enumerate(DAYS):
    DAYMAP[k] = i


def venue_name(plc):
    p = plc.replace(" ", "")
    if "KSPO" in p or "체조" in p: return "KSPO DOME"
    if "티켓링크" in p or "핸드볼" in p: return "티켓링크 라이브 아레나"
    if "우리금융" in p: return "올림픽공원 우리금융아트홀"
    if "뮤즈" in p: return "뮤즈라이브"
    if "K-아트" in p or "K아트" in p: return "K-아트홀"
    if "올림픽홀" in p: return "올림픽홀"
    return plc.strip()


def to_min(ampm, h, mm):
    h = int(h); mm = int(mm or 0)
    if ampm in ("오후", "PM") and h < 12:
        h += 12
    if ampm is None and h < 9:   # '7시' 처럼 오전/오후 없이 쓴 저녁 공연
        h += 12
    return h * 60 + mm


# 시각 표기: 9:00:00PM / 오후 7시 30분 / 19시 30분 / 8PM / 19:30 / 오후 5(끝에 '시' 빠짐)
TIME = re.compile(r"(?P<h1>\d{1,2}):(?P<m1>\d{2})(?::\d{2})?\s*(?P<a1>PM|AM)"
                  r"|(?P<a2>오후|오전)?\s*(?P<h2>\d{1,2})\s*시(?:\s*(?P<m2>\d{1,2})\s*분)?"
                  r"|(?P<h3>\d{1,2})\s*(?P<a3>PM|AM)"
                  r"|(?<![\d.])(?P<h4>\d{1,2}):(?P<m4>\d{2})"
                  r"|(?P<a5>오후|오전)\s*(?P<h5>\d{1,2})(?![\d:.])")


def times_in(txt):
    out = []
    for g in TIME.finditer(txt):
        d = g.groupdict()
        if d["h1"]: v = to_min("오후" if d["a1"] == "PM" else "오전", d["h1"], d["m1"])
        elif d["h2"]: v = to_min(d["a2"], d["h2"], d["m2"])
        elif d["h3"]: v = to_min("오후" if d["a3"] == "PM" else "오전", d["h3"], None)
        elif d["h4"]: v = to_min("24h", d["h4"], d["m4"])
        else: v = to_min(d["a5"], d["h5"], None)
        out.append((g.start(), v))
    return out


def date_hit(day, ttxt):
    m, d, y = day.month, day.day, day.year
    pats = [rf"{m}월\s*{d}\s*(?:일|\()", rf"{y}\.\s*{m}\.\s*{d}(?!\d)", rf"(?<![\d.]){m}\.{d}(?!\d)"]
    hits = [re.search(p, ttxt) for p in pats]
    # "11월 14일(토) ~ 11월 15(일)" 처럼 기간을 뜻하는 날짜는 공연 시각 표기로 보지 않는다
    hits = [h for h in hits if h and "~" not in ttxt[max(0, h.start() - 4):h.start()] and "~" not in ttxt[h.end():h.end() + 6]]
    return min(hits, key=lambda h: h.start()) if hits else None


def expand(venue, title, a, b, ttxt):
    out = []
    allt = times_in(ttxt)
    any_date = re.search(r"\d{1,2}월\s*\d{1,2}\s*(?:일|\()|\d{1,2}\.\d{1,2}", ttxt) and "~" not in ttxt
    day = a
    while day <= b:
        st = None
        # 1) 날짜별 시각: "11월 27일(금) 오후 7시", "2026.11.21.(SAT) 6PM", "12.24(목) 8PM"
        mm = date_hit(day, ttxt)
        if mm:
            after = [x for x in allt if x[0] >= mm.end()]
            st = after[0][1] if after else None
        # 2) 요일별 시각: "금 오후 7시 / 토 오후 6시"
        if st is None:
            wd = day.weekday()
            for g in re.finditer(r"(?<![0-9가-힣A-Za-z])(?:MON|TUE|WED|THU|FRI|SAT|SUN|[월화수목금토일])+(?![가-힣A-Za-z])", ttxt):
                if any(DAYMAP[x] == wd for x in re.findall(r"MON|TUE|WED|THU|FRI|SAT|SUN|[월화수목금토일]", g.group(0))):
                    after = [x for x in allt if g.end() <= x[0] <= g.end() + 4]
                    if after:
                        st = after[0][1]; break
            mentions = "".join(re.findall(r"(?<![0-9가-힣])[월화수목금토일]+(?![가-힣])", ttxt))
            if st is None and mentions and DAYS[wd] not in mentions and not any_date:
                day += dt.timedelta(1); continue  # 공연 없는 요일
        # 3) 시각이 하나뿐이면 매일 같은 시각
        if st is None and len({v for _, v in allt}) == 1:
            st = allt[0][1]
        # 날짜별로 적힌 공연인데 이 날짜가 없으면 공연 없는 날
        if st is None and mm is None and any_date and allt:
            day += dt.timedelta(1); continue
        out.append(dict(date=day.isoformat(), v=venue, title=title, s=st))
        day += dt.timedelta(1)
    return out


def from_json(path):
    raw = json.load(open(path, encoding="utf-8"))
    seen, items = set(), []
    for month in raw.values():
        for e in month:
            if e["evtSeq"] in seen: continue
            seen.add(e["evtSeq"])
            items.append((venue_name(e["plc"]), e["title"].strip(), dt.date.fromisoformat(e["beginDt"]),
                          dt.date.fromisoformat(e["endDt"]), e.get("tm") or ""))
    return items


def from_html(path):
    s = open(path, encoding="utf-8", errors="ignore").read()
    t = re.sub(r"<script.*?</script>", "", s, flags=re.S)
    L = [l.strip() for l in H.unescape(re.sub(r"<[^>]+>", "\n", t)).split("\n") if l.strip() and l.strip() != "-->"]
    L = L[L.index("옥외/기타") + 1:]
    VENUES = {"KSPO DOME", "올림픽홀", "티켓링크 라이브 아레나", "올림픽공원 우리금융아트홀", "뮤즈라이브", "K-아트홀", "핸드볼경기장"}
    items, i = [], 0
    while i + 3 < len(L):
        if L[i] in VENUES and re.match(r"\d{4}-\d{2}-\d{2} ~ \d{4}-\d{2}-\d{2}", L[i + 2]):
            a, b = [dt.date.fromisoformat(x) for x in L[i + 2].split(" ~ ")]
            items.append((venue_name(L[i]), L[i + 1], a, b, L[i + 3])); i += 4
        else:
            i += 1
    return items


EVJSON = os.environ.get("EVENTS_JSON", f"{RAW}/events.json")
items = from_json(EVJSON) if os.path.exists(EVJSON) else from_html(f"{RAW}/ev.html")
events = [e for it in items for e in expand(*it)]
events.sort(key=lambda e: (e["date"], e["v"]))

# 화면용 압축 형식: rows = [센터번호, 공원내(0/1), 종목, 강좌명, 시작분, 종료분, 요일비트(월=1), 대상, 월수강료, 정원]
centers = [c for _, c, _, _ in SPEC]
rows = [[centers.index(x["c"]), int(x["park"]), x["sp"], x["n"], x["s"], x["e"],
         sum(1 << i for i in x["d"]), x["t"], x["p"], x["cap"]] for x in courses]
evs = [[e["date"], e["v"], e["title"], e["s"]] for e in events]
json.dump(dict(centers=centers, stats=stats, events=evs, rows=rows,
               built=(dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")),
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(json.dumps(stats, ensure_ascii=False, indent=1))
print("courses", len(courses), "events", len(events))


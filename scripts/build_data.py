"""4개 센터 강좌 CSV + 올림픽공원 공연 일정 HTML -> 화면용 olpark.json
사용: python3 -I scripts/build_data.py data_raw olpark.json
"""
import sys, re, json, html as H, datetime as dt
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

# ---- 공연 일정 (공원 홈페이지 일정안내 페이지) ----
s = open(f"{RAW}/ev.html", encoding="utf-8", errors="ignore").read()
t = re.sub(r"<script.*?</script>", "", s, flags=re.S)
L = [l.strip() for l in H.unescape(re.sub(r"<[^>]+>", "\n", t)).split("\n") if l.strip() and l.strip() != "-->"]
L = L[L.index("옥외/기타") + 1:]
VENUES = {"KSPO DOME", "올림픽홀", "티켓링크 라이브 아레나", "올림픽공원 우리금융아트홀", "뮤즈라이브", "K-아트홀", "핸드볼경기장"}
DAYMAP = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}
for i, k in enumerate(DAYS):
    DAYMAP[k] = i


def to_min(ampm, h, mm):
    h = int(h); mm = int(mm or 0)
    if ampm in ("오후", "PM") and h < 12:
        h += 12
    if ampm is None and h < 9:   # '7시' 처럼 오전/오후 없이 쓴 저녁 공연
        h += 12
    return h * 60 + mm


TIME = r"(오후|오전)?\s*(\d{1,2})(?:\s*시(?:\s*(\d{2})\s*분)?|:(\d{2})|\s*(PM|AM))"


def times_in(txt):
    out = []
    for g in re.finditer(TIME, txt):
        ap = g.group(1) or (("오후" if g.group(5) == "PM" else "오전") if g.group(5) else None)
        out.append((g.start(), to_min(ap, g.group(2), g.group(3) or g.group(4))))
    return out


events = []
i = 0
while i + 3 < len(L):
    if L[i] in VENUES and re.match(r"\d{4}-\d{2}-\d{2} ~ \d{4}-\d{2}-\d{2}", L[i + 2]):
        venue, title, period, ttxt = L[i], L[i + 1], L[i + 2], L[i + 3]
        a, b = [dt.date.fromisoformat(x) for x in period.split(" ~ ")]
        allt = times_in(ttxt)
        day = a
        while day <= b:
            st = None
            # 1) "11월 27일 ... 오후 7시" 처럼 날짜별
            mm = re.search(rf"{day.month}월\s*{day.day}일", ttxt) or \
                re.search(rf"{day.year}\.{day.month}\.{day.day}\.", ttxt)
            if mm:
                after = [x for x in allt if x[0] >= mm.end()]
                st = after[0][1] if after else None
            # 2) "금 오후 7시 / 토 오후 6시" 처럼 요일별
            if st is None:
                wd = day.weekday()
                for g in re.finditer(r"(?<![0-9가-힣])(?:MON|TUE|WED|THU|FRI|SAT|SUN|[월화수목금토일])+(?![가-힣])", ttxt):
                    if any(DAYMAP[x] == wd for x in re.findall(r"MON|TUE|WED|THU|FRI|SAT|SUN|[월화수목금토일]", g.group(0))):
                        after = [x for x in allt if g.end() <= x[0] <= g.end() + 4]
                        if after:
                            st = after[0][1]; break
                mentions = "".join(re.findall(r"(?<![0-9가-힣])[월화수목금토일]+(?![가-힣])", ttxt))
                if st is None and mentions and DAYS[wd] not in mentions and not re.search(r"\d{1,2}월\s*\d{1,2}일", ttxt):
                    day += dt.timedelta(1); continue  # 공연 없는 요일
            # 3) 시각이 하나뿐이면 매일 같은 시각
            if st is None and allt:
                st = allt[0][1]
            events.append(dict(date=day.isoformat(), v=venue, title=title, s=st))
            day += dt.timedelta(1)
        i += 4
    else:
        i += 1

# 화면용 압축 형식: rows = [센터번호, 공원내(0/1), 종목, 강좌명, 시작분, 종료분, 요일비트(월=1), 대상, 월수강료, 정원]
centers = [c for _, c, _, _ in SPEC]
rows = [[centers.index(x["c"]), int(x["park"]), x["sp"], x["n"], x["s"], x["e"],
         sum(1 << i for i in x["d"]), x["t"], x["p"], x["cap"]] for x in courses]
evs = [[e["date"], e["v"], e["title"], e["s"]] for e in events]
json.dump(dict(centers=centers, stats=stats, events=evs, rows=rows,
               built=dt.datetime.now().strftime("%Y-%m-%d %H:%M")),
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(json.dumps(stats, ensure_ascii=False, indent=1))
print("courses", len(courses), "events", len(events))


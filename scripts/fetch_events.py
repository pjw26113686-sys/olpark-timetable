"""올림픽공원 공연·행사 일정(일정안내 페이지의 목록 API)을 받아 data_raw/events.json 으로 저장.
사용: python3 -I scripts/fetch_events.py data_raw/events.json [개월 수, 기본 3]
이번 달부터 N개월 치를 받는다. 받은 공연이 하나도 없거나 오류면 파일을 바꾸지 않고 실패로 끝낸다.
"""
import sys, json, datetime as dt, urllib.request

URL = "https://www.ksponco.or.kr/olympicpark/eventInfo/eventInfoListAjax.es"
KEEP = ("evtSeq", "title", "beginDt", "endDt", "tm", "plc", "plcCd")


def month_list(n):
    t = dt.datetime.utcnow() + dt.timedelta(hours=9)  # 한국 시간
    y, m = t.year, t.month
    for _ in range(n):
        yield f"{y}{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fetch(ym):
    req = urllib.request.Request(URL, data=json.dumps({"nowYM": ym, "plcCd": ""}).encode(),
                                 headers={"Content-Type": "application/json;charset=UTF-8",
                                          "User-Agent": "olpark-timetable (public data contest prototype)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    rows = data[0] if data and isinstance(data[0], list) else data
    return [{k: (e.get(k) or "").strip() if isinstance(e.get(k), str) else e.get(k) for k in KEEP} for e in rows]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "data_raw/events.json"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    res = {ym: fetch(ym) for ym in month_list(n)}
    total = len({e["evtSeq"] for v in res.values() for e in v})
    if total == 0:
        sys.exit("받은 공연이 없습니다. 기존 파일을 그대로 둡니다.")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("months", list(res), "events", total)


if __name__ == "__main__":
    main()

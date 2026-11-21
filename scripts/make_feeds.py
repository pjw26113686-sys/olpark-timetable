"""공연일 알림 구독 캘린더 만들기.
올림픽공원 안 두 센터(올림픽수영장·올림픽공원스포츠센터)의 강좌마다 feeds/c_<강좌번호>.ics 를 만든다.
강좌 시간이 대형 공연(KSPO DOME·올림픽홀·티켓링크 라이브 아레나) 시작 2시간 전~3시간 후와 겹치는 날에
'공연일 주의' 일정이 들어가고, 전날 같은 시각과 수업 2시간 전에 알림이 울린다.
휴대폰 캘린더에서 이 주소를 '구독'하면 공연 일정이 바뀔 때 알림도 저절로 바뀐다. 개인정보는 모으지 않는다.
사용: python3 -I scripts/make_feeds.py olpark.json feeds
"""
import sys, os, json, datetime as dt

BIG = {"KSPO DOME", "올림픽홀", "티켓링크 라이브 아레나"}
KST = dt.timezone(dt.timedelta(hours=9))
STAMP = "20261121T000000Z"  # 내용이 같으면 파일도 같게(매일 커밋이 생기지 않도록) 고정값을 쓴다


def esc(s):
    return str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold(line):  # 한 줄 75바이트 제한
    b = line.encode("utf-8")
    if len(b) <= 75:
        return line
    out, cur = [], b""
    for ch in line:
        e = ch.encode("utf-8")
        if len(cur) + len(e) > (75 if not out else 74):
            out.append(cur.decode("utf-8")); cur = b""
        cur += e
    out.append(cur.decode("utf-8"))
    return "\r\n ".join(out)


def utc(date, minute):
    t = dt.datetime.fromisoformat(date).replace(hour=minute // 60, minute=minute % 60, tzinfo=KST)
    return t.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "olpark.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "feeds"
    d = json.load(open(src, encoding="utf-8"))
    ev = {}
    for e in d["events"]:
        if e[1] in BIG and e[3] is not None:
            ev.setdefault(e[0], []).append(e)
    os.makedirs(out, exist_ok=True)
    keep, n_events = set(), 0
    for r in d["rows"]:
        if not r[1]:
            continue  # 공원 밖 센터
        center, name, s, e, mask, cid = d["centers"][r[0]], r[3], r[4], r[5], r[6], r[10]
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//olpark-timetable//KO", "CALSCALE:GREGORIAN",
                 "METHOD:PUBLISH", f"X-WR-CALNAME:{esc('올팍 공연일 알림 · ' + name)}", "X-WR-TIMEZONE:Asia/Seoul",
                 "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H"]
        for date in sorted(ev):
            wd = dt.date.fromisoformat(date).weekday()
            if not (mask >> wd & 1):
                continue
            hit = [x for x in ev[date] if s < x[3] + 180 and e > x[3] - 120]
            if not hit:
                continue
            x = hit[0]
            desc = (f"{x[1]} {hm(x[3])} 공연 「{x[2]}」이(가) 있는 날입니다. "
                    f"공연 시작 2시간 전부터 3시간 후까지 올림픽공원 주차장과 출입구가 붐빌 수 있어요. "
                    f"평소보다 일찍 출발하거나 대중교통을 이용하세요.")
            lines += ["BEGIN:VEVENT", f"UID:{cid}-{date}@olpark-timetable", f"DTSTAMP:{STAMP}",
                      f"DTSTART:{utc(date, s)}", f"DTEND:{utc(date, e)}",
                      f"SUMMARY:{esc('공연일 주의 · ' + name)}", f"LOCATION:{esc(center)}",
                      f"DESCRIPTION:{esc(desc)}", "TRANSP:TRANSPARENT",
                      "BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{esc('내일 공연일 · ' + name)}", "TRIGGER:-P1D", "END:VALARM",
                      "BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{esc('2시간 뒤 수업 · 공연일 혼잡')}", "TRIGGER:-PT2H", "END:VALARM",
                      "END:VEVENT"]
            n_events += 1
        lines.append("END:VCALENDAR")
        fn = f"c_{cid}.ics"
        keep.add(fn)
        body = "\r\n".join(fold(l) for l in lines) + "\r\n"
        path = os.path.join(out, fn)
        if not os.path.exists(path) or open(path, encoding="utf-8", newline="").read() != body:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(body)
    for fn in os.listdir(out):  # 더 이상 없는 강좌의 파일은 지움
        if fn.endswith(".ics") and fn not in keep:
            os.remove(os.path.join(out, fn))
    print("feeds", len(keep), "events", n_events)


if __name__ == "__main__":
    main()

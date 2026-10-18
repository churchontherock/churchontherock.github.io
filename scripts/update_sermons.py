"""
유튜브 채널의 영상 목록을 읽어 data/sermons.json 을 갱신한다.

- GitHub Actions 가 매일 자동 실행한다(.github/workflows/update-sermons.yml).
- 관리자가 이 파일을 고칠 일은 없다. 분류 규칙은 data/church.json 의 "sermons.categories" 에서 바꾼다.
- 영상 목록은 두 경로로 읽는다.
    1) yt-dlp: 채널의 '라이브'·'동영상' 탭 전체 (지난 영상까지 전부)
    2) 유튜브 RSS: 최근 15개 + 정확한 게시일
  둘 다 실패하면 기존 sermons.json 을 그대로 둔다(사이트가 비는 일이 없도록).
"""

import json
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHURCH_JSON = ROOT / "data" / "church.json"
SERMONS_JSON = ROOT / "data" / "sermons.json"

# 날짜를 제목에서 못 찾은 새 영상은 영상 페이지를 하나씩 열어 게시일을 확인한다.
# 한 번 실행에 너무 많이 열면 느려지므로 상한을 둔다(남은 건 다음 날 실행에서 처리).
MAX_DATE_LOOKUPS = 40


# ---- 1. 영상 목록 읽기 ----

def list_with_ytdlp(channel_id):
    """yt-dlp 로 채널의 라이브·동영상 탭 전체 목록을 읽는다. 실패하면 None."""
    found = {}
    ok_tabs = 0
    for tab in ("streams", "videos"):
        url = f"https://www.youtube.com/channel/{channel_id}/{tab}"
        try:
            res = subprocess.run(
                [sys.executable, "-m", "yt_dlp", "--flat-playlist", "-J", "--no-warnings", url],
                capture_output=True, text=True, encoding="utf-8", timeout=600,
            )
        except Exception as e:  # yt-dlp 미설치·시간초과
            print(f"[yt-dlp] {tab} 탭 실패: {e}")
            continue
        if res.returncode != 0 or not res.stdout.strip():
            print(f"[yt-dlp] {tab} 탭 실패: {res.stderr.strip()[:300]}")
            continue
        ok_tabs += 1
        for e in json.loads(res.stdout).get("entries") or []:
            if not e.get("id") or e.get("live_status") == "is_upcoming":
                continue  # 예약만 된 라이브는 아직 영상이 아니므로 제외
            found[e["id"]] = {
                "id": e["id"],
                "title": (e.get("title") or "").strip(),
                "duration": int(e["duration"]) if e.get("duration") else None,
                "live": e.get("live_status") == "is_live",
            }
    # 탭 둘 다 성공해야 '전체 목록'으로 믿고 삭제 판단에 쓸 수 있다
    return (found or None), ok_tabs == 2


def list_with_rss(channel_id):
    """유튜브 RSS(최근 15개)를 읽는다. 게시일이 정확하다. 실패하면 빈 dict."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
    except Exception as e:
        print(f"[RSS] 실패: {e}")
        return {}
    out = {}
    for entry in root.findall("a:entry", ns):
        vid = entry.findtext("yt:videoId", namespaces=ns)
        if not vid:
            continue
        published = entry.findtext("a:published", namespaces=ns) or ""
        out[vid] = {
            "id": vid,
            "title": (entry.findtext("a:title", namespaces=ns) or "").strip(),
            "published": published[:10],  # 2026-10-18T02:00:00+00:00 → 2026-10-18
        }
    return out


def lookup_upload_date(video_id):
    """영상 한 개의 게시일(YYYY-MM-DD)을 yt-dlp 로 확인한다. 실패하면 빈 문자열."""
    try:
        res = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--skip-download", "--no-warnings",
             "--print", "%(upload_date)s", f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
        d = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else ""
        if re.fullmatch(r"\d{8}", d):
            return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    except Exception:
        pass
    return ""


# ---- 2. 제목 정리 ----

def valid_date(y, m, d):
    try:
        return datetime(int(y), int(m), int(d)).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def date_from_title(title):
    """제목에 적힌 날짜를 찾는다. (20261018) · 20230212 · 2022 10 23 · 2026.10.18 · 21/11/24 형식."""
    m = re.search(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)", title)
    if m:
        return valid_date(*m.groups())
    m = re.search(r"(?<!\d)(20\d{2})[./\-\s](\d{1,2})[./\-\s](\d{1,2})(?!\d)", title)
    if m:
        return valid_date(*m.groups())
    m = re.search(r"(?<!\d)(\d{2})/(\d{2})/(\d{2})(?!\d)", title)
    if m:
        return valid_date("20" + m.group(1), m.group(2), m.group(3))
    return ""


def clean_title(title, church_name):
    """화면에 보일 짧은 제목: 교회 이름과 날짜를 빼고, 따옴표 속 설교 제목·설교자를 따로 뽑는다."""
    sermon_title = ""
    m = re.search(r"[\"“”'‘’]([^\"“”'‘’]{2,})[\"“”'‘’]", title)
    if m:
        sermon_title = m.group(1).strip()
    preacher = ""
    m = re.search(r"([가-힣]{2,4})\s*(목사|전도사)", title)
    if m:
        preacher = m.group(1) + " " + m.group(2)

    t = title.replace(church_name, " ")
    t = re.sub(r"\(?\s*(20\d{2})(\d{2})(\d{2})\s*\)?", " ", t)           # (20261018)
    t = re.sub(r"(20\d{2})[./\-\s](\d{1,2})[./\-\s](\d{1,2})", " ", t)    # 2022 10 23
    t = re.sub(r"(?<!\d)\d{2}/\d{2}/\d{2}(?!\d)", " ", t)                 # 21/11/24
    if sermon_title:
        t = t.split("|")[0]  # '주일예배 설교 | 서대일 목사 - "..."' → '주일예배 설교'
    t = re.sub(r"\(\s*\)", " ", t)                                       # 날짜를 지우고 남은 빈 괄호
    t = re.sub(r"\s+", " ", t).strip(" -|·_")
    return t or title, sermon_title, preacher


def categorize(title, categories, other):
    """church.json 의 키워드 순서대로 처음 맞는 분류를 고른다."""
    for c in categories:
        if any(k in title for k in c.get("keywords", [])):
            return c["name"]
    return other


# ---- 3. 합치기 ----

def main():
    church = json.loads(CHURCH_JSON.read_text(encoding="utf-8"))
    channel_id = church["youtube"]["channelId"]
    church_name = church["name"]
    cfg = church.get("sermons", {})
    categories = cfg.get("categories", [])
    other = cfg.get("otherCategory", "기타")

    old = {}
    if SERMONS_JSON.exists():
        old_doc = json.loads(SERMONS_JSON.read_text(encoding="utf-8"))
        old = {v["id"]: v for v in old_doc.get("items", [])}

    listed, complete = list_with_ytdlp(channel_id)
    rss = list_with_rss(channel_id)
    if not listed and not rss:
        print("영상 목록을 하나도 못 읽었습니다. 기존 sermons.json 을 유지합니다.")
        return

    # 어떤 영상을 남길지: 전체 목록을 확실히 읽었고 기존의 80% 이상이 보이면 그 목록이 기준(삭제·비공개 반영).
    # 그렇지 않으면 기존 목록을 지우지 않고 새 영상만 더한다.
    ids = set(old)
    if listed and complete and len(listed) >= 0.8 * len(old):
        ids = set(listed)
    ids |= set(listed or {}) | set(rss)

    items = []
    lookups = 0
    for vid in ids:
        prev = old.get(vid, {})
        src = (listed or {}).get(vid) or {}
        title = src.get("title") or rss.get(vid, {}).get("title") or prev.get("title", "")
        date = date_from_title(title) or rss.get(vid, {}).get("published") or prev.get("date", "")
        if not date and lookups < MAX_DATE_LOOKUPS:
            lookups += 1
            date = lookup_upload_date(vid)
        display, sermon_title, preacher = clean_title(title, church_name)
        items.append({
            "id": vid,
            "title": title,
            "display": display,
            "sermonTitle": sermon_title,
            "preacher": preacher,
            "date": date,
            "category": categorize(title, categories, other),
            "duration": src.get("duration") or prev.get("duration"),
            "live": bool(src.get("live")),
        })

    # 최신순 정렬(날짜 없는 영상은 맨 뒤)
    items.sort(key=lambda v: (v["date"] or "0000", v["id"]), reverse=True)

    if [json.dumps(v, sort_keys=True) for v in items] == \
       [json.dumps(old[v["id"]], sort_keys=True) if v["id"] in old else "" for v in items] \
       and len(items) == len(old):
        print(f"변경 없음 ({len(items)}개)")
        return

    doc = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "channelId": channel_id,
        "count": len(items),
        "items": items,
    }
    SERMONS_JSON.parent.mkdir(parents=True, exist_ok=True)
    SERMONS_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    added = len(set(v["id"] for v in items) - set(old))
    print(f"갱신 완료: 총 {len(items)}개 (새 영상 {added}개, 날짜 조회 {lookups}회)")


if __name__ == "__main__":
    main()

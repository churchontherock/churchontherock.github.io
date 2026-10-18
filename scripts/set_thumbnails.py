"""
새 주일예배 영상의 유튜브 썸네일을 '목사님 설교 장면'으로 자동 교체한다.

- GitHub Actions 가 설교 목록 갱신 직후 실행한다(.github/workflows/update-sermons.yml).
- 설정은 data/church.json 의 "thumbnail" 항목에서 바꾼다.
    "minutes": 설교 중일 가능성이 높은 시점(분). 여러 개를 뽑아 그중 '가장 평범한' 장면을 고른다.
               (가사 화면·특수 자막처럼 혼자 튀는 장면을 피하기 위해)
    "since":   이 날짜 이후 영상만 바꾼다(예전 영상 썸네일은 건드리지 않음).
- 유튜브에 올리려면 GitHub 저장소 Secrets 에 아래 3개가 있어야 한다(README '썸네일 자동 교체' 참고).
    YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
  없으면 아무것도 하지 않고 끝난다.
- 처리한 영상은 data/thumbnails_done.json 에 기록해 같은 영상을 두 번 바꾸지 않는다.

시험 실행(유튜브에 올리지 않고 고른 장면만 저장):
    python scripts/set_thumbnails.py --dry-run 출력폴더 [영상ID ...]
"""

import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parent.parent
CHURCH_JSON = ROOT / "data" / "church.json"
SERMONS_JSON = ROOT / "data" / "sermons.json"
DONE_JSON = ROOT / "data" / "thumbnails_done.json"
MAX_PER_RUN = 3  # 한 번 실행에 바꾸는 영상 수 상한


# ---- 1. 영상에서 장면 뽑기 ----

def video_info(video_id):
    res = subprocess.run([sys.executable, "-m", "yt_dlp", "-J", "--no-warnings",
                          f"https://www.youtube.com/watch?v={video_id}"],
                         capture_output=True, text=True, encoding="utf-8", timeout=180)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip()[:300])
    return json.loads(res.stdout)


def pick_format(info):
    """1080p 이하에서 가장 큰 화질의 영상 스트림.
    라이브 직후엔 1초 조각형, 변환이 끝난 뒤엔 HLS(m3u8)를 쓴다 — 일반 mp4 주소는 원하는 시점으로 건너뛰는 데 1분 이상 걸린다."""
    vids = [f for f in info["formats"] if f.get("vcodec") not in (None, "none") and 0 < (f.get("height") or 0) <= 1080]
    frag = [f for f in vids if f.get("fragments")]
    hls = [f for f in vids if str(f.get("protocol", "")).startswith("m3u8")]
    pool = frag or hls or vids
    if not pool:
        raise RuntimeError("영상 스트림 없음")
    return max(pool, key=lambda f: f.get("height") or 0)


def grab_frame(info, fmt, seconds, out_jpg):
    """seconds 지점 한 장면을 out_jpg 로 저장. 성공하면 True."""
    headers = fmt.get("http_headers") or {}
    if fmt.get("fragments"):
        # 라이브 직후 녹화본: 약 1초짜리 조각(sq=N)으로 나뉘어 있어 해당 조각 하나만 받는다
        frags = fmt["fragments"]
        per = (info.get("duration") or len(frags)) / len(frags)
        i = min(int(seconds / per), len(frags) - 1)
        fr = frags[i]
        url = fr.get("url") or fmt["fragment_base_url"] + fr["path"]
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60).read())
            seg = tmp.name
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", seg, "-frames:v", "1", "-q:v", "2", out_jpg]
    else:
        # 일반 영상으로 변환이 끝난 경우: 주소에서 바로 해당 시점으로 이동
        seg = None
        hdr = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-headers", hdr, "-ss", str(seconds),
               "-i", fmt["url"], "-frames:v", "1", "-q:v", "2", out_jpg]
    try:
        subprocess.run(cmd, timeout=180)
    finally:
        if seg:
            os.unlink(seg)
    return os.path.exists(out_jpg) and os.path.getsize(out_jpg) > 0


def caption_ratio(path):
    """화면 왼쪽 아래(성경 구절 자막이 뜨는 자리)에 검은 자막 상자가 차지하는 비율."""
    im = Image.open(path).convert("L")
    w, h = im.size
    box = im.crop((int(w * 0.02), int(h * 0.74), int(w * 0.55), int(h * 0.97))).resize((120, 40))
    px = list(box.getdata())
    return sum(1 for v in px if v < 45) / len(px)


def most_typical(paths):
    """자막이 덮이지 않은 장면 중에서, 나머지와 가장 비슷한 장면(메도이드)을 고른다.
    가사 화면·삽입 사진처럼 혼자 튀는 화면을 피하기 위해서다."""
    clean = [p for p in paths if caption_ratio(p) < 0.35] or paths
    small = {p: Image.open(p).convert("L").resize((96, 54)) for p in paths}
    def dist(a, b):
        return ImageStat.Stat(ImageChops.difference(small[a], small[b])).mean[0]
    return min(clean, key=lambda a: sum(dist(a, b) for b in paths))


def frame_to_thumb(src, out, zoom=1.0, center=(0.5, 0.5)):
    """zoom>1 이면 center(가로·세로 비율 위치)를 중심으로 확대해 목사님이 크게 보이게 한다."""
    im = Image.open(src).convert("RGB")
    if zoom > 1:
        w, h = im.size
        cw, ch = w / zoom, h / zoom
        x = min(max(center[0] * w - cw / 2, 0), w - cw)
        y = min(max(center[1] * h - ch / 2, 0), h - ch)
        im = im.crop((int(x), int(y), int(x + cw), int(y + ch)))
    im.resize((1280, 720), Image.LANCZOS).save(out, quality=88)  # 유튜브 권장 1280x720, 2MB 이하


def make_thumbnail(video_id, minutes, work_dir, zoom=1.0, center=(0.5, 0.5)):
    info = video_info(video_id)
    fmt = pick_format(info)
    duration = info.get("duration") or 0
    shots = []
    for m in minutes:
        s = m * 60
        if duration and s >= duration - 30:
            continue
        p = os.path.join(work_dir, f"{video_id}_{m:02d}.jpg")
        try:
            if grab_frame(info, fmt, s, p):
                shots.append(p)
        except Exception as e:
            print(f"  {m}분 장면 실패: {e}")
    if not shots:
        raise RuntimeError("장면을 하나도 못 뽑음")
    best = most_typical(shots) if len(shots) > 2 else shots[0]
    out = os.path.join(work_dir, f"{video_id}_thumb.jpg")
    frame_to_thumb(best, out, zoom, center)
    return out, os.path.basename(best)


# ---- 2. 유튜브에 올리기 ----

def access_token():
    data = urllib.parse.urlencode({
        "client_id": os.environ["YT_CLIENT_ID"],
        "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    res = urllib.request.urlopen("https://oauth2.googleapis.com/token", data=data, timeout=30)
    return json.loads(res.read())["access_token"]


def upload_thumbnail(token, video_id, jpg):
    url = ("https://www.googleapis.com/upload/youtube/v3/thumbnails/set?"
           + urllib.parse.urlencode({"videoId": video_id, "uploadType": "media"}))
    req = urllib.request.Request(url, data=Path(jpg).read_bytes(), method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"})
    urllib.request.urlopen(req, timeout=60).read()


# ---- 3. 실행 ----

def main():
    church = json.loads(CHURCH_JSON.read_text(encoding="utf-8"))
    cfg = church.get("thumbnail") or {}
    minutes = cfg.get("minutes") or [42, 46, 50, 54, 58]
    zoom = float(cfg.get("zoom", 1.0))                      # 1.0 = 원본 화면, 1.3 = 30% 확대
    center = tuple(cfg.get("center", [0.5, 0.5]))            # 확대 중심(가로, 세로 비율)

    if "--dry-run" in sys.argv:
        args = [a for a in sys.argv[1:] if a != "--dry-run"]
        out_dir, ids = args[0], args[1:]
        os.makedirs(out_dir, exist_ok=True)
        for vid in ids:
            jpg, chosen = make_thumbnail(vid, minutes, out_dir, zoom, center)
            print(f"{vid}: {chosen} 선택 → {jpg}")
        return

    if not cfg.get("enabled"):
        print("썸네일 자동 교체가 꺼져 있습니다(church.json thumbnail.enabled).")
        return
    if not all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")):
        print("유튜브 API 비밀값이 없어 건너뜁니다(README '썸네일 자동 교체' 참고).")
        return

    done = json.loads(DONE_JSON.read_text(encoding="utf-8")) if DONE_JSON.exists() else {}
    items = json.loads(SERMONS_JSON.read_text(encoding="utf-8")).get("items", [])
    todo = [v for v in items
            if v["category"] == cfg.get("category", "주일예배")
            and v.get("date", "") >= cfg.get("since", "9999")
            and v["id"] not in done and not v.get("live")]
    todo = sorted(todo, key=lambda v: v["date"])[:MAX_PER_RUN]
    if not todo:
        print("바꿀 새 영상이 없습니다.")
        return

    token = access_token()
    with tempfile.TemporaryDirectory() as work:
        for v in todo:
            print(f"{v['date']} {v['title']}")
            try:
                jpg, chosen = make_thumbnail(v["id"], minutes, work, zoom, center)
                upload_thumbnail(token, v["id"], jpg)
            except Exception as e:  # 실패한 영상은 기록하지 않아 다음 실행에서 다시 시도
                print(f"  실패: {e}")
                continue
            done[v["id"]] = {"frame": chosen, "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
            print(f"  완료 ({chosen})")

    DONE_JSON.write_text(json.dumps(done, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

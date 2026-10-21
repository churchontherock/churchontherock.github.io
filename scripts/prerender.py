"""
완성된 페이지를 미리 만들어 둔다(prerender).

왜: 이 사이트는 브라우저가 JS 로 church.json·sermons.json 을 읽어 화면을 채운다.
    네이버 검색 로봇처럼 JS 를 실행하지 않는 방문자는 '불러오는 중…' 만 보게 된다.
어떻게: GitHub Actions 에서 배포 직전에 실제 브라우저(헤드리스 Chrome)로 각 페이지를 열어
    JS 가 다 채운 화면을 그대로 HTML 로 저장한다. 화면 그리는 규칙은 site.js 하나뿐이라
    여기서 따로 흉내 낼 필요가 없다. 원본 HTML 은 건드리지 않고 출력 폴더(_site)에만 쓴다.
덤: church.json 으로 검색엔진용 교회 정보(JSON-LD, 다른 이름 포함)를 head 에 넣는다.

사용법: python scripts/prerender.py [출력폴더=_site]
"""

import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "_site"
PAGES = ["index.html", "about.html", "sermons.html", "worship.html"]
SKIP = {".git", ".github", "scripts", "_site", "__pycache__"}  # 배포에 필요 없는 것


def find_chrome():
    """헤드리스 Chrome 실행 파일. GitHub(우분투)엔 google-chrome 이 깔려 있다."""
    env = os.environ.get("CHROME")
    cands = [env] if env else []
    cands += ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]
    for c in cands:
        if c and (shutil.which(c) or os.path.exists(c)):
            return shutil.which(c) or c
    raise SystemExit("Chrome 을 찾지 못했습니다(CHROME 환경변수로 지정 가능).")


def serve(port):
    """사이트 폴더를 잠깐 로컬 서버로 연다(페이지가 data/*.json 을 fetch 하므로 file:// 로는 안 됨)."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def json_ld(church):
    """구글 등에 '이 사이트는 이 교회다'를 알려 주는 구조화 데이터. 띄어 쓴 이름도 함께."""
    c = church.get("contact", {})
    data = {
        "@context": "https://schema.org",
        "@type": "Church",
        "name": church["name"],
        "alternateName": church.get("alternateNames", []),
        "url": church.get("siteUrl", ""),
        "telephone": c.get("phone", ""),
        "address": {"@type": "PostalAddress", "streetAddress": c.get("address", ""), "addressCountry": "KR"},
        "sameAs": [church.get("youtube", {}).get("channelUrl", "")],
    }
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>"


def main():
    church = json.loads((ROOT / "data" / "church.json").read_text(encoding="utf-8"))
    chrome = find_chrome()

    # 1) 사이트 파일을 출력 폴더로 복사 — ★git 에 올라간 파일만(내부 메모·복구코드 같은 로컬 파일이 섞이지 않게)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                             encoding="utf-8", check=True).stdout.splitlines()
    for rel in tracked:
        if rel.split("/")[0] in SKIP or rel.startswith(".git"):
            continue
        dst = OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)

    # 2) 각 페이지를 실제 브라우저로 열어 완성된 화면을 저장
    port = 8799
    srv = serve(port)
    ld = json_ld(church)
    try:
        for page in PAGES:
            res = subprocess.run(
                [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                 "--virtual-time-budget=15000", f"--user-data-dir={OUT.parent / '.chrome-prerender'}",
                 "--dump-dom", f"http://127.0.0.1:{port}/{page}"],
                capture_output=True, text=True, encoding="utf-8", timeout=120)
            html = res.stdout.strip()
            # 내용이 실제로 채워졌는지 확인(실패하면 원본을 그대로 둔다 — 사이트가 깨지지 않게)
            if "불러오는 중" in html or 'class="site-footer"' not in html:
                print(f"[경고] {page}: 화면이 다 채워지지 않아 원본을 그대로 씁니다")
                continue
            if page == "index.html":
                html = html.replace("</head>", ld + "\n</head>", 1)
            (OUT / page).write_text("<!doctype html>\n" + html + "\n", encoding="utf-8")
            print(f"{page}: 완성본 저장 ({len(html):,}자)")
    finally:
        srv.shutdown()
        shutil.rmtree(OUT.parent / ".chrome-prerender", ignore_errors=True)

    # 3) 캐시 무효화: CSS·JS 주소에 이번 배포 버전(git 커밋)을 붙인다.
    #    휴대폰 브라우저가 예전 디자인 파일을 붙잡고 있어도, 새 페이지는 새 주소로 받아 간다.
    ver = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                         text=True).stdout.strip() or "dev"
    for page in PAGES:
        f = OUT / page
        h = f.read_text(encoding="utf-8")
        for asset in ("assets/css/style.css", "assets/js/site.js"):
            h = h.replace(f'"{asset}"', f'"{asset}?v={ver}"')
        f.write_text(h, encoding="utf-8")
    print(f"캐시 버전 표시: v={ver}")



if __name__ == "__main__":
    main()

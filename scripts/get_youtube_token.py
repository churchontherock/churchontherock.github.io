"""
유튜브 썸네일 자동 교체용 '허락 열쇠(refresh token)'를 한 번만 받는 도구.

사용법 (파이썬이 있는 컴퓨터에서, README '썸네일 자동 교체' 순서대로):
    python scripts/get_youtube_token.py 클라이언트ID 클라이언트보안비밀

1) 브라우저가 열리면 교회 유튜브 채널을 관리하는 구글 계정으로 로그인한다.
   채널 선택 화면이 나오면 '반석위에세우신교회' 채널을 고른다.
2) "확인되지 않은 앱" 경고가 나오면 '고급' → '(앱 이름)(으)로 이동' 을 누른다. 우리가 만든 앱이라 괜찮다.
3) 끝나면 화면에 refresh token 이 나온다. 이 값을 GitHub 저장소 Secrets 의 YT_REFRESH_TOKEN 에 넣는다.

이 열쇠는 비밀번호와 같다. 다른 사람에게 보내거나 파일로 저장하지 말 것.
"""

import http.server
import json
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser

SCOPE = "https://www.googleapis.com/auth/youtube.upload"  # 썸네일 변경에 필요한 가장 좁은 권한
PORT = 8790


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    client_id, client_secret = sys.argv[1], sys.argv[2]
    redirect = f"http://127.0.0.1:{PORT}/"
    state = secrets.token_urlsafe(16)
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })

    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state and "code" in q:
                result["code"] = q["code"][0]
                msg = "완료되었습니다. 이 창을 닫고 터미널을 확인하세요."
            else:
                msg = "허락이 취소되었거나 잘못된 요청입니다."
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<p style='font-size:20px'>{msg}</p>".encode("utf-8"))

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    print("브라우저에서 구글 로그인 창이 열립니다. 안 열리면 아래 주소를 복사해 여세요.\n")
    print(url + "\n")
    webbrowser.open(url)
    while "code" not in result:
        server.handle_request()

    data = urllib.parse.urlencode({
        "code": result["code"],
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect,
        "grant_type": "authorization_code",
    }).encode()
    tokens = json.loads(urllib.request.urlopen("https://oauth2.googleapis.com/token", data=data, timeout=30).read())
    if "refresh_token" not in tokens:
        print("refresh token 을 받지 못했습니다. 구글 계정 '보안 → 타사 앱 액세스'에서 이 앱을 지우고 다시 실행하세요.")
        sys.exit(1)
    print("아래 값을 GitHub 저장소 Settings → Secrets and variables → Actions 의 YT_REFRESH_TOKEN 에 넣으세요.\n")
    print(tokens["refresh_token"])


if __name__ == "__main__":
    main()

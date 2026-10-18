# 반석위에세우신교회 홈페이지

교회 소개와 설교 영상을 보여 주는 홈페이지입니다. GitHub Pages로 무료 호스팅하며, 비용은 도메인을 사면 그 값(연 2~3만 원)만 듭니다.

**관리자가 평소에 하는 일은 유튜브에 영상을 올리는 것뿐입니다.** 홈페이지가 매일 밤 12시와 주일 오후 1시 30분에 유튜브 채널을 확인해서, 새 영상을 설교 목록에 자동으로 추가합니다.

---

## 1. 폴더 구성

| 파일 | 하는 일 | 고칠 일 |
|---|---|---|
| `data/church.json` | 교회 이름, 주소, 예배 시간, 소개 글, 섬기는 사람들 | **여기만 고치면 됩니다** |
| `data/sermons.json` | 설교 영상 목록 | 자동으로 갱신되니 고치지 마세요 |
| `assets/img/` | 로고, 사진 | 사진을 바꿀 때만 |
| `index.html` 등 HTML 4개 | 홈, 교회 소개, 설교, 예배 안내 페이지의 틀 | 고칠 필요 없음 |
| `assets/css/style.css` | 색과 모양 | 색을 바꿀 때만 (맨 위 `:root`) |
| `assets/js/site.js` | 화면을 그리는 코드 | 고칠 필요 없음 |
| `scripts/update_sermons.py` | 유튜브에서 영상 목록을 읽는 코드 | 고칠 필요 없음 |
| `.github/workflows/update-sermons.yml` | 매일 자동 실행 설정 | 고칠 필요 없음 |

## 2. 교회 정보 고치기 (`data/church.json`)

GitHub 저장소 화면에서 `data/church.json`을 열고 연필 아이콘(Edit)을 누르면 웹에서 바로 고칠 수 있습니다. 고친 뒤 **Commit changes**를 누르면 1~2분 뒤 홈페이지에 반영됩니다.

자주 고치는 곳:

- **예배 시간:** `"worship"` 안의 `"time"` 값
- **홈의 점심·소그룹 안내:** `"highlight"`. 잠시 숨기려면 `"show": true`를 `false`로 바꿉니다
- **담임목사 인사말:** `"greeting"`에 문단을 하나씩 넣습니다
  ```json
  "greeting": [
    "첫째 문단입니다.",
    "둘째 문단입니다."
  ]
  ```
- **연혁:** `"history"`에 연도와 내용을 넣습니다. 비워 두면 연혁 칸이 화면에 나오지 않습니다
  ```json
  "history": [
    { "year": "2010", "text": "교회 설립" },
    { "year": "2022", "text": "장로·안수집사·권사 임직" }
  ]
  ```
- **목사님 사진:** `assets/img/`에 사진을 올리고(예: `pastor.jpg`) `"photo": "assets/img/pastor.jpg"`처럼 적습니다

주의할 점:

- 따옴표(`"`)와 쉼표(`,`)를 지우지 않도록 조심하세요. 하나라도 빠지면 페이지가 "교회 정보를 불러오지 못했습니다"라고 나옵니다. 그럴 땐 저장소의 **History**에서 바로 전 버전으로 되돌리면 됩니다.
- 항목 사이에는 쉼표가 있고, 마지막 항목 뒤에는 쉼표가 없습니다.

## 3. 설교 영상 분류

영상 제목에 들어 있는 낱말로 자동 분류합니다 (`church.json`의 `"sermons"` → `"categories"`).

| 분류 | 제목에 이 낱말이 있으면 |
|---|---|
| 주일예배 | 주일, 1부예배, 2부예배, 부활, 성탄, 추수감사, 대림절 … |
| 금요기도회 | 금요기도회 |
| 새벽기도회 | 새벽 |
| 성경공부 | 성경공부, 역사 지리, 강해 |
| 기타 | 위에 해당하지 않는 영상 |

**날짜는 제목에서 읽습니다.** 지금처럼 `반석위에세우신교회 주일2부예배 (20261018)` 형식을 계속 써 주세요.

**설교 제목도 보이게 하려면** 유튜브 제목 끝에 큰따옴표로 설교 제목을 넣어 주세요. 홈페이지 카드에 설교 제목이 크게 나옵니다.

```
반석위에세우신교회 주일2부예배 (20261018) "하나님의 일을 나타내시다"
```

## 4. 처음 한 번만 하는 설정

### 4-1. GitHub 계정 만들기

1. https://github.com/signup 에서 **교회 공용 이메일**로 가입합니다. 개인 메일로 만들면 담당자가 바뀔 때 넘겨주기 어렵습니다.
2. 아이디(Username)는 홈페이지 주소가 됩니다. 예: 아이디가 `bansukchurch`이면 주소는 `https://bansukchurch.github.io`
3. 가입 후 **Settings → Password and authentication**에서 2단계 인증을 켜 두세요.

### 4-2. 파일 올리기 (저장소 만들기)

**GitHub Desktop** 프로그램(https://desktop.github.com)을 쓰면 클릭만으로 올릴 수 있습니다.

1. GitHub Desktop 설치 후 교회 계정으로 로그인
2. **File → Add local repository** → 이 폴더(`9_church_homepage`) 선택
3. "This directory does not appear to be a Git repository" 가 나오면 **create a repository** → **Create repository**
4. 위쪽 **Publish repository** 버튼
   - Name: **`<아이디>.github.io`** 로 정확히 (예: `bansukchurch.github.io`)
   - **Keep this code private 체크 해제** (공개 저장소여야 무료 Pages 사용 가능)
5. 이후 파일을 고치면 GitHub Desktop 왼쪽 아래에 요약을 적고 **Commit to main** → **Push origin**

웹 화면의 "Upload files" 끌어다 놓기는 `.github` 폴더가 빠질 수 있어 권하지 않습니다.

### 4-3. Actions 권한 설정 (`contents: write`)

자동 갱신이 `sermons.json`을 저장소에 저장하려면 쓰기 권한이 필요합니다.

1. 저장소 → **Settings → Actions → General**
2. 맨 아래 **Workflow permissions**에서 **Read and write permissions** 선택 → **Save**

### 4-4. GitHub Pages 켜기

1. 저장소 → **Settings → Pages**
2. **Build and deployment → Source**를 **GitHub Actions**로 선택합니다 (Deploy from a branch 가 아닙니다)
3. 저장소 → **Actions** 탭 → 왼쪽 **설교 목록 갱신 및 배포** → **Run workflow**
4. 초록 체크가 뜨면 `https://<아이디>.github.io` 에서 홈페이지가 열립니다 (처음엔 몇 분 걸릴 수 있습니다)

## 5. 도메인 연결 (도메인을 산 뒤)

가비아·후이즈·Cloudflare 등에서 도메인을 산 뒤:

1. 저장소 → **Settings → Pages → Custom domain**에 도메인을 적고 **Save** (예: `www.<구매한도메인>`)
2. 도메인 회사의 **DNS 설정**에 아래를 추가합니다

   | 종류 | 이름(호스트) | 값 |
   |---|---|---|
   | CNAME | `www` | `<아이디>.github.io` |
   | A | `@` | `185.199.108.153` |
   | A | `@` | `185.199.109.153` |
   | A | `@` | `185.199.110.153` |
   | A | `@` | `185.199.111.153` |

3. 몇 시간 안에 연결됩니다. 연결 후 **Enforce HTTPS**에 체크합니다.
4. (권장) GitHub 계정 **Settings → Pages**에서 도메인을 **Verify** 해 두면 다른 사람이 도메인을 가로챌 수 없습니다.

## 6. 썸네일 모양 바꾸기

`church.json`의 `"cardStyle"` 값으로 고릅니다.

- `"youtube"` : 유튜브 썸네일을 그대로 씁니다 (지금 설정)
- `"poster"` : 교회 주황색 카드에 날짜와 제목을 크게 씁니다. `"pastor"`의 `"photo"`에 목사님 사진(배경을 지운 PNG 권장)을 넣으면 카드 오른쪽에 얼굴이 들어갑니다

바꾸기 전에 주소 끝에 `?card=poster` 를 붙여 미리 볼 수 있습니다. 예: `https://<아이디>.github.io/sermons.html?card=poster`

유튜브에 올라가는 썸네일 자체를 바꾸려면 유튜브 스튜디오 → 콘텐츠 → 영상 → **썸네일 업로드**에서 바꿉니다. 바꾸면 홈페이지(`"youtube"` 설정)에도 그대로 반영됩니다.

## 7. 문제가 생겼을 때

| 증상 | 확인할 곳 |
|---|---|
| 새 설교가 안 올라와요 | **Actions** 탭에서 최근 실행이 빨간 X인지 확인 → 눌러서 오류 확인. **Run workflow**로 다시 실행 |
| 자동 실행이 멈췄어요 | 저장소에 60일 동안 아무 변화가 없으면 GitHub가 자동 실행을 끕니다. Actions 탭에서 **Enable workflow** 를 누르세요. 매주 설교가 올라오면 보통 꺼지지 않습니다 |
| 페이지가 "교회 정보를 불러오지 못했습니다" | `church.json`의 따옴표·쉼표 실수. **History**에서 이전 버전으로 되돌리기 |
| 날짜가 이상해요 | 유튜브 제목에 `(20261018)` 형식의 날짜가 있는지 확인 |

## 8. 내 컴퓨터에서 미리 보기 (선택)

파이썬이 있는 컴퓨터에서 이 폴더를 열고:

```
python -m http.server 8000
```

브라우저에서 `http://localhost:8000` 을 엽니다. HTML 파일을 더블클릭해서 열면 데이터를 못 읽어 빈 화면이 나옵니다.

## 9. 주일예배 썸네일 자동 교체 (목사님 설교 장면)

> **현재 꺼져 있습니다** (`"enabled": false`). 교회 확인을 받은 뒤 `true` 로 바꾸면 그다음 실행부터 동작합니다.

켜 두면, 주일예배 영상이 올라올 때 GitHub가 영상의 **42·46·50·54·58분** 장면을 뽑아, 그중 성경 구절 자막이 덮이지 않은 가장 평범한 장면으로 유튜브 썸네일을 바꿉니다. 홈페이지도 유튜브 썸네일을 쓰니 자동으로 같이 바뀝니다.

설정은 `church.json`의 `"thumbnail"`에서 바꿉니다.

| 항목 | 뜻 |
|---|---|
| `"enabled"` | `false`면 끕니다 |
| `"minutes"` | 장면을 뽑을 시점(분). 설교가 대략 40~65분 사이라 이렇게 정했습니다 |
| `"zoom"` | `1.0`이면 원래 화면(강대상의 설교 제목까지 보임), `1.4`면 목사님을 크게 확대 |
| `"since"` | 이 날짜 이후 영상만 바꿉니다. 예전 영상 썸네일은 건드리지 않습니다 |

### 처음 한 번만: 유튜브 API 허락 받기

교회 유튜브 채널을 관리하는 구글 계정으로 진행합니다. 약 15분 걸립니다.

1. https://console.cloud.google.com 접속 → 위쪽 프로젝트 선택 → **새 프로젝트** → 이름 `church-homepage` → 만들기
2. 왼쪽 메뉴 **API 및 서비스 → 라이브러리** → `YouTube Data API v3` 검색 → **사용**
3. **API 및 서비스 → OAuth 동의 화면** (또는 Google Auth Platform)
   - 사용자 유형 **외부** → 앱 이름 `반석 홈페이지`, 지원 이메일·개발자 이메일 = 본인 메일 → 저장
   - **대상(Audience)** 에서 **앱 게시(Publish app)** → 프로덕션으로 전환
     (테스트 상태로 두면 7일마다 허락이 끊깁니다. 검증 신청은 하지 않아도 됩니다)
4. **API 및 서비스 → 사용자 인증 정보 → 사용자 인증 정보 만들기 → OAuth 클라이언트 ID**
   - 애플리케이션 유형 **데스크톱 앱** → 만들기
   - 나오는 **클라이언트 ID**와 **클라이언트 보안 비밀번호**를 복사해 둡니다
5. 파이썬이 있는 컴퓨터에서 이 폴더를 열고 실행합니다

   ```
   python scripts/get_youtube_token.py 클라이언트ID 클라이언트보안비밀번호
   ```

   - 브라우저가 열리면 로그인하고, 채널 선택 화면에서 **반석위에세우신교회** 채널을 고릅니다
   - "확인되지 않은 앱" 경고가 나오면 **고급 → 반석 홈페이지(으)로 이동**을 누릅니다 (직접 만든 앱이라 괜찮습니다)
   - 끝나면 터미널에 긴 문자열(refresh token)이 나옵니다
6. GitHub 저장소 → **Settings → Secrets and variables → Actions → New repository secret** 으로 3개를 넣습니다

   | Name | Secret |
   |---|---|
   | `YT_CLIENT_ID` | 4번의 클라이언트 ID |
   | `YT_CLIENT_SECRET` | 4번의 클라이언트 보안 비밀번호 |
   | `YT_REFRESH_TOKEN` | 5번의 긴 문자열 |

7. Actions 탭에서 **Run workflow** 를 눌러 시험합니다. 로그의 "새 주일예배 썸네일을 설교 장면으로 교체" 단계에 `완료`가 보이면 성공입니다

**주의:** 위 세 값은 비밀번호와 같습니다. 카톡·메일로 보내거나 파일로 저장하지 마세요. 유출되었다고 생각되면 구글 계정 → 보안 → 타사 앱 액세스에서 `반석 홈페이지`를 삭제하고 5번부터 다시 하면 됩니다.

**안 될 때:** 유튜브가 GitHub 서버에서의 영상 접근을 막는 경우가 있습니다. Actions 로그에 `Sign in to confirm you're not a bot` 이 보이면 이 방식은 쓸 수 없으니, 관리자가 집 컴퓨터에서 주 1회 `python scripts/set_thumbnails.py` 를 실행하는 방식으로 바꿔야 합니다.

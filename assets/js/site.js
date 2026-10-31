/* 반석위에세우신교회 홈페이지 공통 스크립트
   - 교회 정보는 data/church.json, 설교 목록은 data/sermons.json 에서 읽습니다.
   - 이 파일은 고칠 필요가 없습니다. 내용은 위 두 JSON 파일에서 바꿉니다. */

const PAGES = [
  { href: "about.html", label: "교회 소개" },
  { href: "sermons.html", label: "설교" },
  { href: "worship.html", label: "예배 안내" },
];

const $ = (sel, root = document) => root.querySelector(sel);

// HTML 특수문자 처리 (제목에 < > & 가 있어도 깨지지 않도록)
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function loadJSON(path) {
  const res = await fetch(path, { cache: "no-cache" });
  if (!res.ok) throw new Error(path + " " + res.status);
  return res.json();
}

// 2026-10-18 → 2026. 10. 18 (주일)
function fmtDate(iso, withDay = true) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-").map(Number);
  const day = "일월화수목금토"[new Date(y, m - 1, d).getDay()];
  return `${y}. ${m}. ${d}` + (withDay ? ` (${day})` : "");
}

function fmtDuration(sec) {
  if (!sec) return "";
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  const pad = (n) => String(n).padStart(2, "0");
  return h ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

// 교단 이름 앞에 총회 공식 심볼(assets/img/pck.png)을 붙인다
function denomHTML(church) {
  if (!church.denomination) return "";
  return `<span class="denom"><img src="assets/img/pck.png" alt="" class="denom-mark">${esc(church.denomination)}</span>`;
}

const ytUrl = (id) => `https://www.youtube.com/watch?v=${id}`;

// ---- 머리글·바닥글 ----
function renderChrome(church) {
  const here = location.pathname.split("/").pop() || "index.html";
  const header = $("#site-header");
  if (header) {
    header.className = "site-header";
    header.innerHTML = `
      <div class="wrap">
        <a class="brand" href="index.html"><img src="assets/img/logo.svg" alt=""><span>${esc(church.nameShort || church.name)}</span></a>
        <button class="menu-btn" aria-label="메뉴 열기" aria-expanded="false">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
        </button>
        <nav class="nav">${PAGES.map((p) => `<a href="${p.href}"${p.href === here ? ' aria-current="page"' : ""}>${p.label}</a>`).join("")}</nav>
      </div>`;
    const btn = $(".menu-btn", header), nav = $(".nav", header);
    btn.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      btn.setAttribute("aria-expanded", open);
    });
  }
  const footer = $("#site-footer");
  if (footer) {
    const c = church.contact || {};
    footer.className = "site-footer";
    footer.innerHTML = `
      <div class="wrap">
        <div class="f-name"><img src="assets/img/logo.svg" alt="">${esc(church.name)}</div>
        ${(church.alternateNames || []).length ? `<p>${esc(church.alternateNames.join(" · "))}</p>` : ""}
        <p>${denomHTML(church)}</p>
        <p>${esc(c.address || "")}</p>
        <p>${c.phone ? `전화 <a href="tel:${esc(c.phone.replace(/[^0-9+]/g, ""))}">${esc(c.phone)}</a>` : ""}
           ${c.email ? ` · <a href="mailto:${esc(c.email)}">${esc(c.email)}</a>` : ""}
           ${church.youtube?.channelUrl ? ` · <a href="${esc(church.youtube.channelUrl)}" target="_blank" rel="noopener">유튜브 채널</a>` : ""}</p>
        <p>© ${new Date().getFullYear()} ${esc(church.name)}</p>
      </div>`;
  }
}

// ---- 설교 카드 ----
// cardStyle 이 "youtube" 면 유튜브 썸네일, "poster" 면 교회 색으로 만든 카드(목사님 사진을 넣을 수 있음)
function thumbHTML(v, church, big = false) {
  // 주소 끝에 ?card=poster 또는 ?card=youtube 를 붙이면 미리보기로 바꿔 볼 수 있다
  const style = new URLSearchParams(location.search).get("card") || church.sermons?.cardStyle || "youtube";
  const live = v.live ? '<span class="badge live">LIVE</span>' : "";
  const dur = v.duration ? `<span class="badge">${fmtDuration(v.duration)}</span>` : "";
  if (style === "poster") {
    const face = church.about?.pastor?.photo;
    const [y, m, d] = (v.date || "").split("-");
    return `<div class="thumb"><div class="poster">
        <div class="p-cat">${esc(v.category)}</div>
        <div class="p-date">${m ? `${Number(m)}.${Number(d)}` : ""}</div>
        <div class="p-title">${esc(v.sermonTitle || v.display)}</div>
        ${face ? `<img class="p-face" src="${esc(face)}" alt="">` : '<img class="p-logo" src="assets/img/logo.svg" alt="">'}
      </div>${live}${big ? '<span class="play"></span>' : ""}${dur}</div>`;
  }
  // 큰 카드는 고화질(maxres)을 먼저 시도하고, 없으면(회색 120px 대체 이미지) hq 로 바꾼다
  const hq = `https://i.ytimg.com/vi/${v.id}/hqdefault.jpg`;
  const src = big ? `https://i.ytimg.com/vi/${v.id}/maxresdefault.jpg` : hq;
  const fallback = big ? ` onload="if(this.naturalWidth<=120)this.src='${hq}'" onerror="this.src='${hq}'"` : "";
  return `<div class="thumb"><img src="${src}" alt="" loading="${big ? "eager" : "lazy"}"${fallback}>${live}<span class="play"${big ? "" : ' style="width:46px;height:46px"'}></span>${dur}</div>`;
}

// 설교 제목 줄: "믿으면 보리라 (요11:30-44)" — 설교 제목이 없으면 영상 종류(주일2부예배 등)
function heading(v) {
  if (!v.sermonTitle) return v.display;
  return v.scripture ? `${v.sermonTitle} (${v.scripture})` : v.sermonTitle;
}

function cardHTML(v, church) {
  const title = heading(v);
  const sub = [fmtDate(v.date), v.sermonTitle ? v.display : "", v.preacher].filter(Boolean).join(" · ");
  return `<a class="card s-card" href="${ytUrl(v.id)}" target="_blank" rel="noopener" title="${esc(v.title)}">
      ${thumbHTML(v, church)}
      <div class="meta"><div class="cat">${esc(v.category)}</div><h3>${esc(title)}</h3><div class="sub">${esc(sub)}</div></div>
    </a>`;
}

// ---- 홈 ----
function renderHome(church, sermons) {
  $("#church-name").textContent = church.name;
  $("#denomination").innerHTML = denomHTML(church);
  if (church.motto?.text) {
    $("#motto").innerHTML = `“${esc(church.motto.text)}”<cite>${esc(church.motto.ref || "")}</cite>`;
  }

  // 이번 주 설교: homeCategories(주일설교·금요설교) 중 가장 최근 영상 → 주일 뒤엔 주일설교, 금요일 뒤엔 금요설교가 번갈아 올라온다
  const items = sermons.items || [];
  const homeCats = church.sermons?.homeCategories || [church.sermons?.homeCategory];
  const latest = items.find((v) => homeCats.includes(v.category)) || items[0];
  if (latest) {
    const f = $("#feature");
    f.href = ytUrl(latest.id);
    f.innerHTML = `${thumbHTML(latest, church, true)}
      <div class="meta"><div class="eyebrow">이번 주 ${esc(latest.category)}</div>
        <h2>${esc(heading(latest))}</h2>
        <p>${esc([latest.preacher, fmtDate(latest.date)].filter(Boolean).join(" · "))} · 누르면 유튜브에서 열립니다</p></div>`;
  }

  // 예배 시간 요약: 모든 예배를 한 줄씩
  const rows = (church.worship || []).flatMap((g) => g.items);
  $("#times").innerHTML = `<h3>예배 시간</h3>${rows.map((r) => `<div class="time-row"><b>${esc(r.name)}</b><span>${esc(r.time)}</span></div>`).join("")}
    <a class="more" href="worship.html">예배 안내 · 오시는 길 →</a>`;

  // 점심·소그룹 안내
  const h = church.highlight;
  const hl = $("#highlight");
  if (h?.show) {
    hl.innerHTML = `<div class="eyebrow">${esc(h.label)}</div><h3>${esc(h.title)}</h3>
      ${(h.lines || []).map((l) => `<p>${esc(l)}</p>`).join("")}
      ${h.tag ? `<span class="tag">${esc(h.tag)}</span>` : ""}`;
  } else hl.remove();

  // 최근 영상 4개 (이번 주 설교 제외)
  const recent = items.filter((v) => v !== latest).slice(0, 4);
  $("#recent").innerHTML = recent.map((v) => cardHTML(v, church)).join("");

  // 오시는 길 요약
  const c = church.contact || {};
  $("#visit-short").innerHTML = `
    <div><div class="eyebrow">오시는 길</div><h3 style="font-size:20px;margin:4px 0 6px">${esc(c.address)}</h3>
    <p style="margin:0;color:var(--muted)">${esc(c.transit || "")}</p>
    ${c.parking ? `<p style="margin:4px 0 0;color:var(--muted)">주차: ${esc(c.parking)}</p>` : ""}
    <div class="btn-row" style="margin-top:14px">
      ${c.naverMap ? `<a class="btn" href="${esc(c.naverMap)}" target="_blank" rel="noopener">네이버 지도</a>` : ""}
      ${c.kakaoMap ? `<a class="btn" href="${esc(c.kakaoMap)}" target="_blank" rel="noopener">카카오맵</a>` : ""}
      ${c.phone ? `<a class="btn primary" href="tel:${esc(c.phone.replace(/[^0-9+]/g, ""))}">전화하기</a>` : ""}
    </div></div>
    ${entranceHTML(c)}`;
}

// 교회 입구 사진 + 안내문 (홈·예배 안내 공통). 문구는 church.json 의 contact.entranceNote
function entranceHTML(c) {
  if (!c.entrancePhoto) return "";
  return `<figure style="margin:0"><img src="${esc(c.entrancePhoto)}" alt="교회 입구" loading="lazy" data-zoom tabindex="0" role="button" aria-label="교회 입구 사진 크게 보기">
    ${c.entranceNote ? `<figcaption class="caption">${esc(c.entranceNote)}</figcaption>` : ""}</figure>`;
}

// ---- 설교 목록 ----
function renderSermons(church, sermons) {
  const all = sermons.items || [];
  const pageSize = church.sermons?.pageSize || 12;
  // 탭: 실제 영상이 있는 분류만
  // 탭 순서: tabOrder 가 있으면 그 순서(분류 판정 순서와 별개), 없으면 분류 순서
  const order = [...(church.sermons?.tabOrder || (church.sermons?.categories || []).map((c) => c.name)), church.sermons?.otherCategory || "기타"];
  const cats = ["전체", ...order.filter((n) => all.some((v) => v.category === n))];

  const params = new URLSearchParams(location.search);
  const state = { cat: cats.includes(params.get("cat")) ? params.get("cat") : "전체", q: params.get("q") || "", page: 1 };

  const tabs = $("#tabs"), search = $("#search"), list = $("#list"), info = $("#info"), pager = $("#pager");
  search.value = state.q;

  function filtered() {
    const q = state.q.trim().replace(/\s+/g, "").toLowerCase();
    return all.filter((v) => {
      if (state.cat !== "전체" && v.category !== state.cat) return false;
      if (!q) return true;
      // 제목·날짜(2026-10-18, 20261018, 2026.10.18 어느 형식이든) 검색
      const hay = [v.title, v.display, v.sermonTitle, v.scripture, v.preacher, v.date, (v.date || "").replace(/-/g, ""), (v.date || "").replace(/-/g, ".")]
        .join(" ").replace(/\s+/g, "").toLowerCase();
      return hay.includes(q);
    });
  }

  function draw() {
    tabs.innerHTML = cats.map((c) => `<button type="button" aria-pressed="${c === state.cat}" data-cat="${esc(c)}">${esc(c)}</button>`).join("");
    const rows = filtered();
    const pages = Math.max(1, Math.ceil(rows.length / pageSize));
    state.page = Math.min(state.page, pages);
    const slice = rows.slice((state.page - 1) * pageSize, state.page * pageSize);
    info.textContent = `${rows.length.toLocaleString()}개 영상` + (state.q ? ` · “${state.q}” 검색 결과` : "");
    list.innerHTML = slice.length ? slice.map((v) => cardHTML(v, church)).join("") : "";
    $("#empty").hidden = slice.length > 0;

    // 페이지 번호: 현재 앞뒤 2개 + 처음/끝
    const nums = [];
    for (let i = 1; i <= pages; i++) if (i === 1 || i === pages || Math.abs(i - state.page) <= 2) nums.push(i);
    let html = `<button type="button" data-p="${state.page - 1}" ${state.page === 1 ? "disabled" : ""} aria-label="이전">‹</button>`;
    nums.forEach((n, i) => {
      if (i && n - nums[i - 1] > 1) html += `<span>…</span>`;
      html += `<button type="button" data-p="${n}" ${n === state.page ? 'aria-current="page"' : ""}>${n}</button>`;
    });
    html += `<button type="button" data-p="${state.page + 1}" ${state.page === pages ? "disabled" : ""} aria-label="다음">›</button>`;
    pager.innerHTML = pages > 1 ? html : "";

    // 주소창에 상태 기록(뒤로가기·공유용)
    const p = new URLSearchParams();
    if (state.cat !== "전체") p.set("cat", state.cat);
    if (state.q) p.set("q", state.q);
    history.replaceState(null, "", location.pathname + (p.toString() ? "?" + p : ""));
  }

  tabs.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-cat]");
    if (!b) return;
    state.cat = b.dataset.cat; state.page = 1; draw();
  });
  let t;
  search.addEventListener("input", () => {
    clearTimeout(t);
    t = setTimeout(() => { state.q = search.value; state.page = 1; draw(); }, 200);
  });
  pager.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-p]");
    if (!b || b.disabled) return;
    state.page = Number(b.dataset.p); draw();
    $("#tabs").scrollIntoView({ behavior: "smooth", block: "center" });
  });
  draw();
}

// ---- 교회 소개 ----
function renderAbout(church) {
  const a = church.about || {};
  // 교회 소개 글: 머리말 + 비전 4가지 + 맺음말 (church.json about.welcome)
  const w = a.welcome || {};
  $("#about-lead").textContent = w.lead || "";
  // 머리말 옆에 담임목사 사진을 작게(글이 사진을 감싸며 흐름)
  const pp = a.pastor || {};
  if (pp.photo) $("#lead-face").innerHTML = `<img src="${esc(pp.photo)}" alt="${esc(pp.name)} ${esc(pp.title || "")}" data-zoom tabindex="0" role="button" aria-label="담임목사 사진 크게 보기"><figcaption>${esc(pp.title || "담임목사")} <b>${esc(pp.name || "")}</b></figcaption>`;
  else $("#lead-face").remove();
  $("#vision").innerHTML = (w.visions || []).map((v, i) =>
    `<li class="card"><span class="v-num">${i + 1}</span><div><h3>${esc(v.title)}</h3><p>${esc(v.text)}</p></div></li>`).join("");
  if (!(w.visions || []).length) $("#vision-section").remove();
  $("#about-closing").textContent = w.closing || "";
  $("#denom").innerHTML = church.denomination ? `${denomHTML(church)}에 속한 교회입니다.` : "";
  if (a.photo) $("#about-photo").innerHTML = `<img src="${esc(a.photo)}" alt="${esc(church.name)} 예배 모습" data-zoom tabindex="0" role="button" aria-label="예배 사진 크게 보기">`;
  else $("#about-photo").remove();

  const p = a.pastor || {};
  const greet = (p.greeting || []).filter(Boolean);
  const box = $("#pastor");
  if (p.name && greet.length) {  // 인사말이 생기면 보인다(사진은 머리말 옆에 이미 있음)
    box.classList.toggle("has-photo", !!p.photo);
    box.innerHTML = `${p.photo ? `<img src="${esc(p.photo)}" alt="${esc(p.name)} ${esc(p.title || "")}">` : ""}
      <div><div class="name">${esc(p.name)} ${esc(p.title || "")}</div>
      ${greet.length ? `<div class="greeting" style="margin-top:12px">${greet.map((g) => `<p>${esc(g)}</p>`).join("")}</div>` : ""}</div>`;
  } else $("#pastor-section").remove();

  // 섬기는 사람들 단체 사진(있으면 이름 카드 위에)
  if (a.staffPhoto) $("#staff-photo").innerHTML = `<img src="${esc(a.staffPhoto)}" alt="섬기는 사람들" loading="lazy" data-zoom tabindex="0" role="button" aria-label="섬기는 사람들 사진 크게 보기">`;
  else $("#staff-photo").remove();
  const staff = a.staff || [];
  // together: 한 칸에 나란히(담임목사·사모) — 가로로 넓은 카드
  const person = (s) => `<div class="person"><small>${esc(s.role)}</small><b>${esc(s.name)}</b></div>`;
  if (staff.length) $("#staff").innerHTML = staff.map((s) => s.together
    ? `<div class="card wide">${s.together.map(person).join('<span class="sep"></span>')}</div>`
    : `<div class="card">${person(s)}</div>`).join("");
  else $("#staff-section").remove();

  const hist = a.history || [];
  // 연혁: 연도별로 여러 줄 (items) — 예전 형식(text 한 줄)도 그대로 받는다
  if (hist.length) $("#timeline").innerHTML = hist.map((h) =>
    `<li><b class="t-year">${esc(h.year)}</b><ul>${(h.items || [h.text]).map((x) => `<li>${esc(x)}</li>`).join("")}</ul></li>`).join("");
  else $("#history-section").remove();
}

// ---- 예배 안내 ----
function renderWorship(church) {
  $("#worship").innerHTML = (church.worship || []).map((g) => `
    <div class="card w-table"><h2>${esc(g.group)}</h2>
      ${g.items.map((r) => `<div class="w-row"><div class="top"><b>${esc(r.name)}</b><span>${esc(r.time)}</span></div>
        ${[r.place, r.leader ? `인도 ${r.leader}` : ""].filter(Boolean).length ? `<div class="note">${esc([r.place, r.leader ? `인도 ${r.leader}` : ""].filter(Boolean).join(" · "))}</div>` : ""}
        ${r.note ? `<div class="note">${esc(r.note)}</div>` : ""}</div>`).join("")}
    </div>`).join("");

  const h = church.highlight;
  if (h?.show) {
    $("#w-highlight").innerHTML = `<div class="eyebrow">${esc(h.label)}</div><h3>${esc(h.title)}</h3>
      ${(h.lines || []).map((l) => `<p>${esc(l)}</p>`).join("")}${h.tag ? `<span class="tag">${esc(h.tag)}</span>` : ""}`;
  } else $("#w-highlight").remove();

  const c = church.contact || {};
  const tel = (c.phone || "").replace(/[^0-9+]/g, "");
  $("#visit").innerHTML = `
    <div>
      <dl>
        <dt>주소</dt><dd>${esc(c.address)}</dd>
        ${c.transit ? `<dt>교통</dt><dd>${esc(c.transit)}</dd>` : ""}
        ${c.parking ? `<dt>주차</dt><dd>${esc(c.parking)}</dd>` : ""}
        ${c.phone ? `<dt>전화</dt><dd><a href="tel:${esc(tel)}">${esc(c.phone)}</a></dd>` : ""}
        ${c.email ? `<dt>이메일</dt><dd><a href="mailto:${esc(c.email)}">${esc(c.email)}</a></dd>` : ""}
      </dl>
      <div class="btn-row">
        ${c.naverMap ? `<a class="btn" href="${esc(c.naverMap)}" target="_blank" rel="noopener">네이버 지도</a>` : ""}
        ${c.kakaoMap ? `<a class="btn" href="${esc(c.kakaoMap)}" target="_blank" rel="noopener">카카오맵</a>` : ""}
        ${c.phone ? `<a class="btn primary" href="tel:${esc(tel)}">전화하기</a>` : ""}
      </div>
    </div>
    ${entranceHTML(c)}`;
}

// ---- 사진 크게 보기 ----
// data-zoom 이 붙은 사진을 누르면 화면 가득 크게 보여준다. 바깥을 누르거나 Esc·뒤로가기로 닫는다.
function setupZoom() {
  let box = null;
  function close() {
    if (!box) return;
    box.remove(); box = null;
    document.body.style.overflow = "";
    if (history.state && history.state.zoom) history.back();
  }
  function open(img) {
    box = document.createElement("div");
    box.className = "lightbox";
    box.innerHTML = `<img src="${esc(img.currentSrc || img.src)}" alt="${esc(img.alt)}">
      <button type="button" class="lightbox-close" aria-label="닫기">×</button>`;
    box.addEventListener("click", (e) => { if (e.target.tagName !== "IMG") close(); });
    document.body.appendChild(box);
    document.body.style.overflow = "hidden";
    history.pushState({ zoom: true }, "");  // 휴대폰 뒤로가기 버튼으로 닫히게
  }
  document.addEventListener("click", (e) => {
    const img = e.target.closest("img[data-zoom]");
    if (img) open(img);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") close();
    if ((e.key === "Enter" || e.key === " ") && e.target.matches && e.target.matches("img[data-zoom]")) { e.preventDefault(); open(e.target); }
  });
  window.addEventListener("popstate", () => { if (box) { box.remove(); box = null; document.body.style.overflow = ""; } });
}

// ---- 시작 ----
(async function init() {
  const page = document.body.dataset.page;
  let church;
  try {
    church = await loadJSON("data/church.json");
  } catch (e) {
    document.body.insertAdjacentHTML("afterbegin", '<p style="padding:16px">교회 정보를 불러오지 못했습니다. data/church.json 을 확인해 주세요.</p>');
    return;
  }
  renderChrome(church);
  setupZoom();
  if (page === "about") return renderAbout(church);
  if (page === "worship") return renderWorship(church);

  let sermons = { items: [] };
  try { sermons = await loadJSON("data/sermons.json"); } catch (e) { console.warn(e); }
  if (page === "home") renderHome(church, sermons);
  if (page === "sermons") renderSermons(church, sermons);
})();

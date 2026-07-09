// ============================================================
// Boss OS - Sidebar "Lịch sử hội thoại" TRONG chat workspace (cột trái khi phóng to chat).
// chat-zoom.js tạo khung <aside id="chatSide"> và gọi window.BossChatSide.mount/refresh;
// module này render nội dung: + Hội thoại mới, tìm kiếm, danh sách nhóm theo thời gian,
// đổi tên/xoá, highlight phiên đang mở. Mở phiên qua window.BossSessions (app.js).
// (Thay panel trượt bên phải cũ - nút "Lịch sử" góc phải giờ mở thẳng workspace.)
// ============================================================
(function () {
  "use strict";

  function el(html) { var d = document.createElement("div"); d.innerHTML = html.trim(); return d.firstChild; }
  function esc(s) { return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
  function brain() { try { return (window.BossSessions && window.BossSessions.brain()) || "brain"; } catch (e) { return "brain"; } }
  function currentId() { try { return (window.BossSessions && window.BossSessions.current()) || null; } catch (e) { return null; } }

  function fmtT(ts) {
    try {
      var d = new Date(ts * 1000), now = new Date();
      if (d.toDateString() === now.toDateString())
        return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
      var dd = String(d.getDate()).padStart(2, "0") + "/" + String(d.getMonth() + 1).padStart(2, "0");
      return d.getFullYear() === now.getFullYear() ? dd : dd + "/" + String(d.getFullYear()).slice(2);
    } catch (e) { return ""; }
  }

  function groupOf(ts) {
    var d0 = new Date(); d0.setHours(0, 0, 0, 0);
    var start = d0.getTime() / 1000;
    if (ts >= start) return "Hôm nay";
    if (ts >= start - 86400) return "Hôm qua";
    if (ts >= start - 6 * 86400) return "7 ngày qua";
    return "Cũ hơn";
  }

  var side = null, listEl = null, searchEl = null, searchTimer = null, refreshTimer = null;

  function mount(container) {
    if (!container) return;
    side = container;
    side.innerHTML =
      '<button class="cside-new" type="button">＋ Hội thoại mới</button>' +
      '<input class="cside-search" placeholder="Tìm trong mọi hội thoại…">' +
      '<div class="cside-list"></div>';
    listEl = side.querySelector(".cside-list");
    searchEl = side.querySelector(".cside-search");
    side.querySelector(".cside-new").onclick = function () {
      if (window.BossSessions) window.BossSessions.new();
      closeDrawerIfNarrow();
    };
    searchEl.oninput = function () {
      clearTimeout(searchTimer);
      var q = searchEl.value.trim();
      searchTimer = setTimeout(function () { q ? doSearch(q) : loadList(); }, 280);
    };
    refresh();
  }

  function refresh() {
    if (!side) return;
    // debounce nhẹ: response + notifySessions có thể bắn sát nhau
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(function () {
      var q = searchEl && searchEl.value.trim();
      q ? doSearch(q) : loadList();
    }, 150);
  }

  function closeDrawerIfNarrow() {
    if (window.innerWidth >= 900) return;
    var st = document.querySelector(".chat-stage");
    if (st) st.classList.remove("side-on");
  }

  function openSession(id) {
    if (window.BossSessions) window.BossSessions.open(id);
    closeDrawerIfNarrow();
  }

  async function loadList() {
    if (!listEl) return;
    listEl.innerHTML = '<div class="cside-empty">Đang tải…</div>';
    try {
      var r = await fetch("/sessions?brain=" + encodeURIComponent(brain()) + "&limit=100");
      var data = await r.json();
      renderList(data.sessions || []);
    } catch (e) { listEl.innerHTML = '<div class="cside-empty">Lỗi tải danh sách.</div>'; }
  }

  function renderList(items) {
    if (!items.length) {
      listEl.innerHTML = '<div class="cside-empty">Chưa có hội thoại nào.<br>Bấm ＋ để bắt đầu.</div>';
      return;
    }
    listEl.innerHTML = "";
    var cur = currentId(), lastGroup = null;
    items.forEach(function (s) {
      var g = groupOf(s.updated_at || 0);
      if (g !== lastGroup) {
        listEl.appendChild(el('<div class="cside-group">' + g + '</div>'));
        lastGroup = g;
      }
      var eng = (s.engine || "").toString().slice(0, 10);
      var item = el('<div class="cside-item' + (s.id === cur ? " active" : "") + '">' +
        '<div class="ci-title">' + esc(s.title || s.preview || "(chưa đặt tên)") + '</div>' +
        '<div class="ci-meta"><span>' + fmtT(s.updated_at) + '</span>' +
        (eng ? '<span class="ci-badge">' + esc(eng) + '</span>' : '') +
        '<span>' + (s.msg_count || 0) + ' tin</span>' +
        '<span class="act"><span class="ren" title="Đổi tên">✎</span><span class="del" title="Xoá">🗑</span></span>' +
        '</div></div>');
      item.onclick = function (e) {
        if (e.target.classList.contains("del")) { e.stopPropagation(); delSession(s); return; }
        if (e.target.classList.contains("ren")) { e.stopPropagation(); renSession(s); return; }
        openSession(s.id);
      };
      listEl.appendChild(item);
    });
  }

  async function doSearch(q) {
    if (!listEl) return;
    listEl.innerHTML = '<div class="cside-empty">Đang tìm…</div>';
    try {
      var r = await fetch("/sessions/search?q=" + encodeURIComponent(q) + "&brain=" + encodeURIComponent(brain()) + "&limit=40");
      var data = await r.json();
      var hits = data.results || [];
      if (!hits.length) { listEl.innerHTML = '<div class="cside-empty">Không tìm thấy.</div>'; return; }
      listEl.innerHTML = "";
      hits.forEach(function (h) {
        var snip = esc(h.snippet || "").replace(/&gt;&gt;&gt;/g, "<b>").replace(/&lt;&lt;&lt;/g, "</b>");
        var item = el('<div class="cside-item">' +
          '<div class="ci-title">' + esc(h.title || "(chưa đặt tên)") + '</div>' +
          '<div class="ci-snip">' + snip + '</div>' +
          '<div class="ci-meta"><span>' + fmtT(h.ts) + '</span></div></div>');
        item.onclick = function () { openSession(h.session_id); };
        listEl.appendChild(item);
      });
    } catch (e) { listEl.innerHTML = '<div class="cside-empty">Lỗi tìm kiếm.</div>'; }
  }

  async function delSession(s) {
    if (!confirm('Xoá hội thoại "' + (s.title || s.preview || "(chưa đặt tên)") + '"?')) return;
    try { await fetch("/sessions/" + encodeURIComponent(s.id) + "/delete", { method: "POST" }); } catch (e) {}
    if (s.id === currentId() && window.BossSessions) window.BossSessions.new();
    refresh();
  }

  async function renSession(s) {
    var t = prompt("Tên mới cho hội thoại:", s.title || s.preview || "");
    if (t == null) return;
    try {
      var fd = new FormData(); fd.append("title", t);
      await fetch("/sessions/" + encodeURIComponent(s.id) + "/rename", { method: "POST", body: fd });
    } catch (e) {}
    refresh();
  }

  window.BossChatSide = { mount: mount, refresh: refresh };

  // Cập nhật khi có lượt chat mới / đổi phiên / đổi brain
  window.addEventListener("boss:sessions-changed", refresh);

  function bindGlobal() {
    var gs = document.getElementById("graphSource");
    if (gs) gs.addEventListener("change", refresh);
    // Nút "Lịch sử" cố định (góc trên phải) → mở thẳng workspace với sidebar
    var btn = el('<div id="jv-sess-btn" title="Lịch sử hội thoại">🕘 <span>Lịch sử</span></div>');
    btn.onclick = function () { if (window.BossChatStage) window.BossChatStage.showSide(); };
    document.body.appendChild(btn);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bindGlobal);
  else bindGlobal();
})();

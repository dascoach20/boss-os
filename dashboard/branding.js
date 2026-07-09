/* branding.js - đổi logo/avatar + cấu hình tên miền riêng (HTTPS).
   Tách riêng khỏi app.js (file đó có encoding hỗn hợp, sửa dễ hỏng). Vanilla DOM, không cần Alpine. */
(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }

  function setStatus(id, msg, isErr) {
    var el = $(id);
    if (!el) return;
    el.textContent = msg || "";
    el.style.color = isErr ? "#ff8a8a" : "";
  }

  function esc(s) { return (s || "").toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

  function _injectDomCss() {
    if (document.getElementById("domCss")) return;
    var s = document.createElement("style"); s.id = "domCss";
    s.textContent =
      ".dom-field{display:flex;gap:6px}.dom-field input{flex:1;min-width:0}" +
      ".dom-status{display:flex;gap:8px;flex-wrap:wrap;margin-top:9px}" +
      ".dom-badge{font-size:12.5px;padding:3px 10px;border-radius:20px;border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.05);color:#aebbd6;white-space:nowrap}" +
      ".dom-badge.ok{background:rgba(44,122,75,.16);border-color:#2c7a4b;color:#8fe3ad}" +
      ".dom-badge.warn{background:rgba(210,160,60,.14);border-color:rgba(210,160,60,.5);color:#f0cd94}" +
      ".dom-badge.bad{background:rgba(210,70,70,.14);border-color:rgba(210,70,70,.5);color:#ffb0b0}" +
      ".dom-ssl{display:flex;gap:6px;margin-top:9px}.dom-ssl .s-btn{flex:1}" +
      ".dom-guide{margin-top:9px;font-size:13px;line-height:1.55;color:#cdd8ee;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:8px;padding:9px 11px}" +
      ".dom-guide code{background:rgba(120,180,255,.13);padding:1px 6px;border-radius:5px;font-size:12.5px}";
    document.head.appendChild(s);
  }

  // Đổi src mọi ảnh logo (header, thanh bên, màn đăng nhập, preview) để thấy ảnh mới ngay.
  function bustLogos() {
    var v = "/brand-logo?v=" + Date.now();
    document.querySelectorAll('img[src^="/brand-logo"]').forEach(function (img) { img.src = v; });
  }

  // ---------- Logo / avatar ----------
  async function uploadLogo(file) {
    if (!file) return;
    setStatus("brandLogoStatus", "Đang tải lên…", false);
    try {
      var fd = new FormData();
      fd.append("file", file);
      var r = await fetch("/branding/logo", { method: "POST", body: fd });
      var j = await r.json().catch(function () { return {}; });
      if (!r.ok || !j.ok) { setStatus("brandLogoStatus", j.error || "Tải lên thất bại", true); return; }
      bustLogos();
      setStatus("brandLogoStatus", "Đã cập nhật ảnh ✓", false);
    } catch (e) {
      setStatus("brandLogoStatus", "Lỗi mạng khi tải lên", true);
    }
  }

  async function resetLogo() {
    setStatus("brandLogoStatus", "Đang khôi phục…", false);
    try {
      var r = await fetch("/branding/logo/reset", { method: "POST" });
      var j = await r.json().catch(function () { return {}; });
      if (!r.ok || !j.ok) { setStatus("brandLogoStatus", (j && j.error) || "Không khôi phục được", true); return; }
      bustLogos();
      setStatus("brandLogoStatus", "Đã về ảnh mặc định.", false);
    } catch (e) {
      setStatus("brandLogoStatus", "Lỗi mạng", true);
    }
  }

  // ---------- Tên miền & SSL ----------
  function _badge(id, text, cls) {
    var e = $(id); if (!e) return;
    e.textContent = text; e.className = "dom-badge " + (cls || "");
  }

  // Vẽ trạng thái tên miền + SSL từ dữ liệu /domain/status.
  function renderDomainStatus(j) {
    var row = $("domStatusRow"), sslRow = $("domSslRow"), guide = $("domainGuide");
    if (!j || !j.domain) {
      if (row) row.style.display = "none";
      if (sslRow) sslRow.style.display = "none";
      if (guide) guide.style.display = "none";
      setStatus("domainStatus", "Chưa đặt tên miền.", false);
      return;
    }
    if (row) row.style.display = "flex";
    if (sslRow) sslRow.style.display = "flex";
    if (j.dns_ok) _badge("dnsBadge", "DNS: đã trỏ đúng", "ok");
    else if (j.dns_ip) _badge("dnsBadge", "DNS: sai IP (" + j.dns_ip + ")", "bad");
    else _badge("dnsBadge", "DNS: chưa trỏ", "warn");
    if (j.ssl_active) _badge("sslBadge", "SSL: đang bật", "ok");
    else if (j.ssl_enabled) _badge("sslBadge", "SSL: đang chờ", "warn");
    else _badge("sslBadge", "SSL: tắt", "");
    var tog = $("sslToggle");
    if (tog) tog.textContent = j.ssl_active ? "Kích hoạt lại" : "Bật SSL";
    var ip = j.server_ip || "(IP máy chủ VPS)";
    var steps = "", n = 1;
    if (!j.dns_ok) {
      steps += '<div><b>Bước ' + (n++) + '.</b> Tạo bản ghi DNS tại nhà cung cấp tên miền:<br>' +
        '<code>A &nbsp;·&nbsp; ' + esc(j.domain) + ' &nbsp;·&nbsp; ' + esc(ip) + '</code></div>';
    }
    steps += '<div style="margin-top:6px"><b>Bước ' + (n++) + '.</b> Bấm <b>Bật SSL</b>, đợi vài giây cấp chứng chỉ, rồi mở <code>https://' + esc(j.domain) + '</code>.</div>';
    if (j.deploy_mode === "docker" && !j.ssl_active) {
      steps += '<div style="margin-top:7px;opacity:.85">Nếu SSL vẫn không bật: bản Docker cần chạy kèm Caddy - ' +
        '<code>docker compose -f docker-compose.yml -f docker-compose.https.yml up -d</code>. ' +
        '(Hostinger đã có SSL riêng, bỏ qua bước này.)</div>';
    }
    if (guide) { guide.innerHTML = steps; guide.style.display = "block"; }
    if (j.ssl_active) setStatus("domainStatus", "HTTPS đang chạy cho " + j.domain + ".", false);
    else setStatus("domainStatus", j.ssl_reason || "", !!(j.dns_ip && !j.dns_ok));
  }

  async function saveDomain() {
    var input = $("setDomain");
    var d = ((input && input.value) || "").trim();
    setStatus("domainStatus", "Đang lưu…", false);
    try {
      var fd = new FormData(); fd.append("domain", d);
      var r = await fetch("/domain", { method: "POST", body: fd });
      var j = await r.json().catch(function () { return {}; });
      if (!r.ok || !j.ok) { setStatus("domainStatus", j.error || "Lưu thất bại", true); return; }
      if (j.domain) { setStatus("domainStatus", "Đã lưu. Đang kiểm tra DNS/SSL…", false); checkDomain(); }
      else { renderDomainStatus({ domain: "" }); setStatus("domainStatus", "Đã xoá tên miền.", false); }
    } catch (e) { setStatus("domainStatus", "Lỗi mạng khi lưu", true); }
  }

  async function checkDomain() {
    setStatus("domainStatus", "Đang kiểm tra…", false);
    try {
      var r = await fetch("/domain/status");
      var j = await r.json().catch(function () { return {}; });
      renderDomainStatus(j);
    } catch (e) { setStatus("domainStatus", "Không kiểm tra được (lỗi mạng).", true); }
  }

  // Bật SSL: lưu ý định + chủ động xin chứng chỉ (server probe HTTPS), rồi làm mới trạng thái.
  async function toggleSsl() {
    var d = (($("setDomain") || {}).value || "").trim();
    if (!d) { setStatus("domainStatus", "Hãy nhập và lưu tên miền trước.", true); return; }
    var tog = $("sslToggle");
    if (tog) tog.disabled = true;
    setStatus("domainStatus", "Đang bật SSL và xin chứng chỉ… (có thể mất khoảng 10 giây)", false);
    try {
      var fd = new FormData(); fd.append("enabled", "1");
      var r = await fetch("/domain/ssl", { method: "POST", body: fd });
      var j = await r.json().catch(function () { return {}; });
      if (!r.ok || !j.ok) { setStatus("domainStatus", j.error || "Bật SSL thất bại", true); return; }
      await checkDomain();
      if (!j.ssl_active) {
        var extra = j.hint_cmd ? (" Chạy trên VPS: " + j.hint_cmd) : "";
        setStatus("domainStatus", (j.ssl_reason || "Chưa bật được SSL") + "." + extra, true);
      }
    } catch (e) { setStatus("domainStatus", "Lỗi mạng khi bật SSL", true); }
    finally { if (tog) tog.disabled = false; }
  }

  // Nạp giá trị hiện tại khi mở Cài đặt.
  async function loadExtras() {
    try {
      var r = await fetch("/settings");
      var j = await r.json();
      var dom = (j.domain || {}).custom || "";
      var di = $("setDomain"); if (di) di.value = dom;
      var b = j.branding || {};
      setStatus("brandLogoStatus", b.logo_ext ? "Đang dùng ảnh tùy chỉnh." : "Đang dùng ảnh mặc định.", false);
      if (dom) checkDomain(); else renderDomainStatus({ domain: "" });
    } catch (e) { /* im lặng */ }
  }

  function bind() {
    _injectDomCss();
    var sBtn = $("settingsBtn");
    if (sBtn) sBtn.addEventListener("click", function () { setTimeout(loadExtras, 50); });

    var li = $("brandLogoInput");
    if (li) li.addEventListener("change", function (e) {
      var f = e.target.files && e.target.files[0];
      if (f) uploadLogo(f);
      e.target.value = "";   // cho phép chọn lại cùng file
    });
    var lr = $("brandLogoReset");
    if (lr) lr.addEventListener("click", resetLogo);

    var sd = $("saveDomain");
    if (sd) sd.addEventListener("click", saveDomain);
    var cd = $("checkDomain");
    if (cd) cd.addEventListener("click", checkDomain);
    var stg = $("sslToggle");
    if (stg) stg.addEventListener("click", toggleSsl);

    // Controls giờ nằm trong sidebar (luôn hiển thị) → nạp giá trị hiện tại ngay khi tải trang.
    loadExtras();
  }

  // Cho trang Cài đặt (console.js) gọi nạp lại giá trị avatar/tên miền khi mở trang.
  window.__bossRefreshExtras = loadExtras;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();

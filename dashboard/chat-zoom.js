/* chat-zoom.js - phóng to khung chat thành CHAT WORKSPACE (kiểu Claude/Cowork):
   gần full màn hình, 2 cột = sidebar Lịch sử trái (sessions-ui.js render qua
   window.BossChatSide) + cột chat chính. Di chuyển CHÍNH các node #chatArea +
   #attachBar + #hudVoice vào lớp nổi (giữ nguyên mọi handler đã gắn), Esc hoặc
   nút ✕ để thu nhỏ. Tách riêng để không đụng app.js. */
(function () {
  "use strict";
  var stage = null, expanded = false, slots = [];
  var SIDE_KEY = "boss.chatside.v1";   // "on" | "off" (desktop nhớ lựa chọn)

  function sideDefaultOn() {
    var saved = "";
    try { saved = localStorage.getItem(SIDE_KEY) || ""; } catch (e) {}
    if (window.innerWidth < 900) return false;          // màn hẹp: mặc định ẩn (drawer)
    return saved !== "off";
  }

  function setSide(on, remember) {
    if (!stage) return;
    stage.classList.toggle("side-on", !!on);
    var t = stage.querySelector(".cs-side-toggle");
    if (t) t.classList.toggle("active", !!on);
    if (remember && window.innerWidth >= 900) {
      try { localStorage.setItem(SIDE_KEY, on ? "on" : "off"); } catch (e) {}
    }
    if (on && window.BossChatSide) window.BossChatSide.refresh();
  }

  function ensureStage() {
    if (stage) return stage;
    stage = document.createElement("div");
    stage.className = "chat-stage";
    stage.innerHTML =
      '<div class="chat-stage-head">' +
      '<span class="cs-actions">' +
      '<button class="cs-side-toggle" type="button" title="Ẩn/hiện lịch sử hội thoại">🕘 Lịch sử</button>' +
      '</span>' +
      '<span>HỘI THOẠI</span>' +
      '<button class="chat-stage-close" type="button">✕ Thu nhỏ (Esc)</button></div>' +
      '<div class="chat-stage-main">' +
      '<aside class="chat-side" id="chatSide"></aside>' +
      '<div class="chat-stage-body"></div>' +
      '</div>';
    document.body.appendChild(stage);
    stage.querySelector(".chat-stage-close").addEventListener("click", collapse);
    stage.querySelector(".cs-side-toggle").addEventListener("click", function () {
      setSide(!stage.classList.contains("side-on"), true);
    });
    // Màn hẹp: sidebar là drawer nổi → bấm ra vùng chat thì tự đóng
    stage.querySelector(".chat-stage-body").addEventListener("click", function () {
      if (window.innerWidth < 900 && stage.classList.contains("side-on")) setSide(false);
    });
    if (window.BossChatSide) window.BossChatSide.mount(stage.querySelector("#chatSide"));
    return stage;
  }

  function moveInto(node, container) {
    if (!node) return;
    slots.push({ node: node, parent: node.parentNode, next: node.nextSibling });
    container.appendChild(node);
  }

  function restore() {
    for (var i = slots.length - 1; i >= 0; i--) {
      var s = slots[i];
      if (!s.parent) continue;
      if (s.next && s.next.parentNode === s.parent) s.parent.insertBefore(s.node, s.next);
      else s.parent.appendChild(s.node);
    }
    slots = [];
  }

  function expand() {
    if (expanded) return;
    var body = ensureStage().querySelector(".chat-stage-body");
    moveInto(document.getElementById("chatArea"), body);
    moveInto(document.getElementById("attachBar"), body);   // chip file đính kèm hiện TRONG workspace
    moveInto(document.getElementById("hudVoice"), body);
    document.body.classList.add("chat-zoomed");
    expanded = true;
    setSide(sideDefaultOn());
    var ca = document.getElementById("chatArea");
    if (ca) ca.scrollTop = ca.scrollHeight;
    var ci = document.getElementById("chatInput");
    if (ci) { try { ci.focus(); } catch (e) {} }
  }

  function collapse() {
    if (!expanded) return;
    restore();
    document.body.classList.remove("chat-zoomed");
    expanded = false;
  }

  function toggle() { if (expanded) collapse(); else expand(); }

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape" || !expanded) return;
    // Màn hẹp đang mở drawer lịch sử → Esc đóng drawer trước, chưa thu nhỏ chat
    if (window.innerWidth < 900 && stage && stage.classList.contains("side-on")) { setSide(false); return; }
    collapse();
  });

  function bind() {
    var btn = document.getElementById("chatZoomBtn");
    if (btn) btn.addEventListener("click", toggle);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();

  // Cho module khác (nút Lịch sử cũ, sessions-ui) mở workspace
  window.BossChatStage = {
    expand: expand, collapse: collapse, toggle: toggle,
    isOpen: function () { return expanded; },
    showSide: function () { expand(); setSide(true); },
  };
})();

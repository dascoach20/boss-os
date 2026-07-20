// ============================================================
// BOSS OS - 3D Graph (GLOBE engine)
// Quả cầu lưới neon (lồng cầu + vành xích đạo + sao màu theo cụm + tia
// nan hoa), dựng bằng three.js THUẦN (window.THREE r159) - KHÔNG dùng
// ForceGraph3D. Thay cho engine "đám mây tự bung" cũ để khớp bản thiết kế
// dasbrainnebula. Dữ liệu là THẬT: fetch /graph (nodes/edges/categories),
// cập nhật realtime qua addOrUpdate(). Giữ NGUYÊN interface BossGraph3D
// (load/addOrUpdate/nodeStats/setThinking/setLevel/resize/pause/wake...).
// ============================================================

const _texCache = {};
function _glowTex(THREE) {
  if (_texCache.glow) return _texCache.glow;
  const s = 128;
  const cv = document.createElement("canvas");
  cv.width = cv.height = s;
  const g = cv.getContext("2d");
  const grd = g.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
  grd.addColorStop(0.0, "rgba(255,255,255,1)");
  grd.addColorStop(0.14, "rgba(255,255,255,.92)");
  grd.addColorStop(0.32, "rgba(255,255,255,.36)");
  grd.addColorStop(0.6, "rgba(255,255,255,.08)");
  grd.addColorStop(1.0, "rgba(255,255,255,0)");
  g.fillStyle = grd;
  g.fillRect(0, 0, s, s);
  _texCache.glow = new THREE.CanvasTexture(cv);
  return _texCache.glow;
}

// Bảng màu RỰC RỠ theo mẫu dasbrainnebula (mỗi cụm 1 màu riêng biệt) - gán theo
// thứ tự cụm để quả cầu nhiều màu như mẫu, thay cho màu thư mục đơn điệu của server.
const PALETTE = [0xff7a2f, 0x4dd0e1, 0xff5c8a, 0xffc24b, 0xa78bfa, 0xe8412f, 0x8ab4ff, 0x43e0a3, 0xff9d3d, 0xd98cff];

// rải đều i/n điểm trên mặt cầu bán kính radius (xoắn Fibonacci)
function _fib(THREE, i, n, radius) {
  const y = 1 - (i / Math.max(1, n - 1)) * 2;
  const r = Math.sqrt(Math.max(0, 1 - y * y));
  const th = Math.PI * (3 - Math.sqrt(5)) * i;
  return new THREE.Vector3(Math.cos(th) * r * radius, y * radius, Math.sin(th) * r * radius);
}

class BossGraph3D {
  constructor(container, tooltip) {
    this.container = container;
    this.tooltip = tooltip;
    this.level = 0;
    this._smooth = 0;
    this._raf = null;
    this._paused = false;
    this._ready = false;
    this._thinking = false;
    this.nodes = [];               // [{ id,label,path,links,color, pos, sprite, base, isHub }]
    this.nodeById = new Map();
    this._linkCount = 0;
    this._births = new Map();      // sprite -> frames còn lại (hiệu ứng nảy sinh)
    this._firing = new Map();      // idx -> frames (hiệu ứng suy nghĩ)
    this._adj = [];
    this.R = 145;                  // bán kính lồng cầu
    this.selected = null;
    // Cho Console gọi pause()/wake() khi chuyển trang mà không cần sửa app.js.
    window.__bossGraph = this;
    window.dispatchEvent(new Event("boss-graph-created"));
  }

  // -------------------------------------------------- NẠP DỮ LIỆU
  async load(query = "source=all") {
    const res = await fetch(`/graph?${query}`, { cache: "no-store" });
    const data = await res.json();
    const nfc = s => (typeof s === "string" ? s.normalize("NFC") : s);
    (data.nodes || []).forEach(n => { n.label = nfc(n.label); });
    (data.categories || []).forEach(c => { c.name = nfc(c.name); });
    if (!this._ready) this._initScene();
    this._setData(data);
    this.resize();
    return data;
  }

  // -------------------------------------------------- DỰNG CẢNH (1 lần)
  _initScene() {
    const THREE = window.THREE;
    if (!THREE) throw new Error("THREE chưa tải");
    const W = this.container.clientWidth || window.innerWidth;
    const H = this.container.clientHeight || window.innerHeight;

    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x05070e, 0.0016);
    this.camera = new THREE.PerspectiveCamera(52, W / H, 1, 4000);
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.setSize(W, H);
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.domElement.style.display = "block";
    this.container.appendChild(this.renderer.domElement);

    this.world = new THREE.Group();
    this.scene.add(this.world);
    this._glow = _glowTex(THREE);

    this._buildCage(THREE);
    this._buildRing(THREE);
    this._buildCore(THREE);
    this._buildPrism(THREE);
    this._buildBgStars(THREE);

    this._nodeGroup = new THREE.Group(); this.world.add(this._nodeGroup);
    this._linkObj = null;

    // trạng thái camera (quỹ đạo quanh tâm)
    this.theta = 0.62; this.phi = 1.14; this.radius = 430;
    this.tTheta = this.theta; this.tPhi = this.phi; this.tRadius = 430;
    this.target = new THREE.Vector3(); this.tTarget = new THREE.Vector3();
    this.autoSpin = true; this.dragging = false; this._moved = 0; this._px = 0; this._py = 0;

    this.ray = new THREE.Raycaster();
    this.ray.params.Sprite = { threshold: 0.1 };
    this._bindControls();

    // tự đo lại khi container đổi kích thước (tránh canvas 0x0 khi dựng lúc layout chưa xong)
    try {
      this._ro = new ResizeObserver(() => this.resize());
      this._ro.observe(this.container);
    } catch (_) {}

    this._ready = true;
    this._animate();
    // ép một nhịp đo lại ở frame kế (một số layout chưa xong ngay khi khởi tạo)
    requestAnimationFrame(() => this.resize());
  }

  _buildCage(THREE) {
    const R = this.R;
    const mat = new THREE.LineBasicMaterial({
      color: 0x8ba6e0, transparent: true, opacity: 0.12,
      blending: THREE.AdditiveBlending, depthWrite: false,
    });
    this._cage = [];
    for (let m = 0; m < 14; m++) {
      const pts = [], lon = (m / 14) * Math.PI * 2;
      for (let i = 0; i <= 64; i++) {
        const lat = -Math.PI / 2 + (i / 64) * Math.PI;
        pts.push(new THREE.Vector3(R * Math.cos(lat) * Math.cos(lon), R * Math.sin(lat), R * Math.cos(lat) * Math.sin(lon)));
      }
      const ln = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat);
      this.world.add(ln); this._cage.push(ln);
    }
    for (let p = 1; p < 9; p++) {
      const pts = [], lat = -Math.PI / 2 + (p / 9) * Math.PI, r = R * Math.cos(lat), y = R * Math.sin(lat);
      for (let i = 0; i <= 80; i++) {
        const a = (i / 80) * Math.PI * 2;
        pts.push(new THREE.Vector3(r * Math.cos(a), y, r * Math.sin(a)));
      }
      const ln = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat);
      this.world.add(ln); this._cage.push(ln);
    }
  }

  _buildRing(THREE) {
    const R = this.R;
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(R * 0.42, R * 1.06, 128),
      new THREE.MeshBasicMaterial({ color: 0x9fb4ff, transparent: true, opacity: 0.05, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false }),
    );
    ring.rotation.x = -Math.PI / 2;
    this.world.add(ring);
    const edge = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(
        Array.from({ length: 129 }, (_, i) => { const a = (i / 128) * Math.PI * 2; return new THREE.Vector3(R * 1.05 * Math.cos(a), 0, R * 1.05 * Math.sin(a)); }),
      ),
      new THREE.LineBasicMaterial({ color: 0xdfe8ff, transparent: true, opacity: 0.28, blending: THREE.AdditiveBlending, depthWrite: false }),
    );
    this.world.add(edge);
    const flare = new THREE.Sprite(new THREE.SpriteMaterial({ map: this._glow, color: 0xffc9a3, transparent: true, opacity: 0.3, blending: THREE.AdditiveBlending, depthWrite: false }));
    flare.scale.set(R * 2.9, 13, 1);
    this.world.add(flare);
    this._ringParts = [ring, edge, flare];
  }

  _buildCore(THREE) {
    this.core = new THREE.Sprite(new THREE.SpriteMaterial({ map: this._glow, color: 0xffd7a8, transparent: true, opacity: 0.95, blending: THREE.AdditiveBlending, depthWrite: false }));
    this.core.scale.set(46, 46, 1);
    this.world.add(this.core);
    this.coreSolid = new THREE.Mesh(new THREE.IcosahedronGeometry(6.5, 0), new THREE.MeshBasicMaterial({ color: 0xffe9d2 }));
    this.world.add(this.coreSolid);
  }

  _buildPrism(THREE) {
    this.prism = new THREE.Group();
    this.prism.visible = false;
    this.world.add(this.prism);
    this._shells = [];
    [[26, 0x46d6ff, 0.1], [19, 0xff9d3d, 0.13], [13, 0xffc9a3, 0.16]].forEach(([s, c, o]) => {
      const box = new THREE.Mesh(new THREE.BoxGeometry(s, s, s), new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: o, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
      const wire = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(s, s, s)), new THREE.LineBasicMaterial({ color: 0xffd7b0, transparent: true, opacity: 0.34, blending: THREE.AdditiveBlending, depthWrite: false }));
      box.add(wire); this.prism.add(box); this._shells.push(box);
    });
    this._prismHalo = new THREE.Sprite(new THREE.SpriteMaterial({ map: this._glow, color: 0xffb877, transparent: true, opacity: 0.7, blending: THREE.AdditiveBlending, depthWrite: false }));
    this._prismHalo.scale.set(64, 64, 1);
    this.prism.add(this._prismHalo);
  }

  _buildBgStars(THREE) {
    const g = new THREE.BufferGeometry();
    const sp = new Float32Array(1200 * 3);
    for (let i = 0; i < 1200; i++) {
      const v = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).normalize().multiplyScalar(430 + Math.random() * 900);
      sp.set([v.x, v.y, v.z], i * 3);
    }
    g.setAttribute("position", new THREE.BufferAttribute(sp, 3));
    this.scene.add(new THREE.Points(g, new THREE.PointsMaterial({ color: 0x9ab0d8, size: 1.5, transparent: true, opacity: 0.4, blending: THREE.AdditiveBlending, depthWrite: false })));
  }

  // -------------------------------------------------- ĐẶT DỮ LIỆU LÊN CẦU
  _setData(data) {
    const THREE = window.THREE;
    // dọn node + link cũ
    this._nodeGroup.clear();
    if (this._linkObj) { this.world.remove(this._linkObj); this._linkObj.geometry.dispose(); this._linkObj = null; }
    this.nodes = []; this.nodeById.clear();
    this.prism.visible = false; this.selected = null;

    const rawNodes = data.nodes || [];
    const rawEdges = data.edges || [];

    // gom cụm theo THƯ MỤC (folder) -> mỗi cụm 1 vùng trên mặt cầu + 1 màu rực rỡ.
    // Server trả màu đơn điệu (toàn tím) nên ta tự gán bảng màu mẫu theo thứ tự cụm.
    const clusterKeys = [];
    const byCluster = new Map();
    rawNodes.forEach(n => {
      const key = n.folder || n.color || "khac";
      if (!byCluster.has(key)) { byCluster.set(key, []); clusterKeys.push(key); }
      byCluster.get(key).push(n);
    });
    const C = Math.max(1, clusterKeys.length);
    this._colorMap = new Map();   // folder -> hex màu hiển thị (để realtime dùng lại)

    // đặt vị trí + màu từng node
    clusterKeys.forEach((key, ci) => {
      const dcolor = PALETTE[ci % PALETTE.length];
      this._colorMap.set(key, dcolor);
      const list = byCluster.get(key).slice().sort((a, b) => (b.links || 0) - (a.links || 0));
      const hubDir = _fib(THREE, ci * 2 + 1, C * 2, 1).normalize();
      const t1 = new THREE.Vector3().crossVectors(hubDir, new THREE.Vector3(0, 1, 0.3)).normalize();
      const t2 = new THREE.Vector3().crossVectors(hubDir, t1).normalize();
      list.forEach((n, k) => {
        let pos;
        if (k === 0) {
          pos = hubDir.clone().multiplyScalar(this.R * 0.8);
        } else {
          const spread = 0.4 + Math.random() * 0.36;
          const ang = (k / list.length) * Math.PI * 2 + Math.random() * 0.9;
          pos = hubDir.clone()
            .add(t1.clone().multiplyScalar(Math.cos(ang) * spread))
            .add(t2.clone().multiplyScalar(Math.sin(ang) * spread))
            .normalize()
            .multiplyScalar(this.R * (0.62 + Math.random() * 0.4));
        }
        this._addNodeSprite(THREE, n, pos, k === 0, dcolor, ci);
      });
    });

    // lưu danh sách cạnh gốc (dạng id-string) để realtime nối thêm mà không mất cạnh cũ
    this._allEdges = (rawEdges || []).map(e => ({
      source: typeof e.source === "object" ? e.source.id : e.source,
      target: typeof e.target === "object" ? e.target.id : e.target,
    }));
    this._rebuildLinks(THREE, this._allEdges);
    this._rebuildAdj();
    this._rebuildRel();
  }

  // Dựng danh sách "nối tới" cho mỗi node (để thẻ chi tiết liệt kê) từ cạnh hiện có.
  _rebuildRel() {
    this.nodes.forEach(n => { n.rel = []; });
    (this._allEdges || []).forEach(e => {
      const a = this.nodeById.get(typeof e.source === "object" ? e.source.id : e.source);
      const b = this.nodeById.get(typeof e.target === "object" ? e.target.id : e.target);
      if (!a || !b || a === b) return;
      if (!a.rel.includes(b)) a.rel.push(b);
      if (!b.rel.includes(a)) b.rel.push(a);
    });
  }

  _addNodeSprite(THREE, n, pos, isHub, dcolor, ci) {
    const dc = dcolor != null ? dcolor : 0x9d7aff;
    const color = new THREE.Color(dc);
    const mat = new THREE.SpriteMaterial({ map: this._glow, color, transparent: true, opacity: isHub ? 1 : 0.72 + Math.random() * 0.24, blending: THREE.AdditiveBlending, depthWrite: false });
    const base = isHub ? 20 : 4.5 + Math.min(9, (n.links || 0) * 0.7);
    const sp = new THREE.Sprite(mat);
    sp.scale.set(base, base, 1);
    sp.position.copy(pos);
    this._nodeGroup.add(sp);
    const node = { id: n.id, label: n.label, path: n.path, links: n.links || 0, color: n.color, dcolor: dc, ci: ci != null ? ci : -1, pos: pos.clone(), sprite: sp, base, isHub, baseOpacity: mat.opacity, rel: [] };
    sp.__node = node;
    this.nodes.push(node);
    this.nodeById.set(n.id, node);
    return node;
  }

  _rebuildLinks(THREE, edges) {
    if (this._linkObj) { this.world.remove(this._linkObj); this._linkObj.geometry.dispose(); this._linkObj = null; }
    const segs = [];
    this._linkCount = 0;
    (edges || []).forEach(e => {
      const a = this.nodeById.get(typeof e.source === "object" ? e.source.id : e.source);
      const b = this.nodeById.get(typeof e.target === "object" ? e.target.id : e.target);
      if (!a || !b) return;
      const c = new THREE.Color(a.dcolor != null ? a.dcolor : 0x9d7aff).multiplyScalar(0.5);
      segs.push([a.pos, b.pos, c]);
      this._linkCount++;
    });
    // tia từ tâm tới các "hub" cụm (điểm sáng lớn) - hình nan hoa như mẫu
    this.nodes.filter(n => n.isHub).forEach(h => {
      const c = new THREE.Color(h.dcolor != null ? h.dcolor : 0x9d7aff).multiplyScalar(0.32);
      segs.push([new THREE.Vector3(0, 0, 0), h.pos, c]);
    });
    if (!segs.length) return;
    const pos = new Float32Array(segs.length * 6);
    const col = new Float32Array(segs.length * 6);
    segs.forEach((s, i) => {
      pos.set([s[0].x, s[0].y, s[0].z, s[1].x, s[1].y, s[1].z], i * 6);
      col.set([s[2].r, s[2].g, s[2].b, s[2].r, s[2].g, s[2].b], i * 6);
    });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
    this._linkObj = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending, depthWrite: false }));
    this.world.add(this._linkObj);
  }

  _rebuildAdj() {
    const idToIdx = {};
    this.nodes.forEach((n, i) => { idToIdx[n.id] = i; });
    this._adj = this.nodes.map(() => []);
    // adjacency chỉ dùng cho hiệu ứng suy nghĩ; suy từ vị trí link đã dựng là đủ xấp xỉ
    this._sprites = this.nodes.map(n => n.sprite);
    this._idToIdx = idToIdx;
  }

  // -------------------------------------------------- ĐIỀU KHIỂN
  _bindControls() {
    const el = this.renderer.domElement;
    el.addEventListener("pointerdown", e => {
      this.dragging = true; this._moved = 0; this._px = e.clientX; this._py = e.clientY;
      try { el.setPointerCapture(e.pointerId); } catch (_) {}
    });
    el.addEventListener("pointermove", e => {
      if (this.dragging) {
        const dx = e.clientX - this._px, dy = e.clientY - this._py;
        this._moved += Math.abs(dx) + Math.abs(dy);
        this.tTheta -= dx * 0.0044;
        this.tPhi = Math.max(0.16, Math.min(Math.PI - 0.16, this.tPhi - dy * 0.0044));
        this._px = e.clientX; this._py = e.clientY;
      } else {
        this._hover(e);
      }
    });
    window.addEventListener("pointerup", e => {
      if (this.dragging && this._moved < 5) this._pick(e);
      this.dragging = false;
    });
    el.addEventListener("wheel", e => {
      e.preventDefault();
      this.tRadius = Math.max(60, Math.min(900, this.tRadius * (1 + Math.sign(e.deltaY) * 0.11)));
    }, { passive: false });
  }

  _mouseNDC(e) {
    const r = this.container.getBoundingClientRect();
    return {
      x: ((e.clientX - r.left) / r.width) * 2 - 1,
      y: -((e.clientY - r.top) / r.height) * 2 + 1,
    };
  }

  _hover(e) {
    if (!this._ready || !this.tooltip) return;
    const m = this._mouseNDC(e);
    this.ray.setFromCamera(new window.THREE.Vector2(m.x, m.y), this.camera);
    const hits = this.ray.intersectObjects(this._sprites || []);
    if (hits.length) {
      const n = hits[0].object.__node;
      this.container.style.cursor = "pointer";
      this.tooltip.style.display = "block";
      this.tooltip.innerHTML = `<strong>${n.label}</strong><br><span class="tt-path">${n.path || ""}</span><br><span class="tt-links">${n.links} kết nối · click để mở</span>`;
    } else {
      this.container.style.cursor = "grab";
      this.tooltip.style.display = "none";
    }
  }

  _pick(e) {
    if (!this._ready) return;
    const m = this._mouseNDC(e);
    this.ray.setFromCamera(new window.THREE.Vector2(m.x, m.y), this.camera);
    const hits = this.ray.intersectObjects(this._sprites || []);
    if (hits.length) this._select(hits[0].object.__node);
    else this._deselect();
  }

  _select(node) {
    this.selected = node;
    this.autoSpin = false;
    this.tTarget.copy(node.pos);
    this.tRadius = node.isHub ? 120 : 74;
    this.prism.position.copy(node.pos);
    this.prism.visible = true;
    if (this._shells[0]) this._shells[0].material.color.set(node.dcolor != null ? node.dcolor : 0x9d7aff);
    if (window.onGraphNodeClick) window.onGraphNodeClick(node);
  }

  _deselect() {
    this.selected = null;
    this.prism.visible = false;
    this.tTarget.set(0, 0, 0);
    this.tRadius = 430;
    this.autoSpin = !this._locked;
  }

  // -------------------------------------------------- REALTIME
  addOrUpdate(node, linkTargets, isNew) {
    if (!this._ready || !node || !node.id) return { created: false };
    const THREE = window.THREE;
    let target = this.nodeById.get(node.id);
    let created = false;

    if (!target) {
      // mọc cạnh 1 hàng xóm đã có (nếu link tới) -> trông như nảy từ mạng
      let pos = null;
      const nb = (linkTargets || []).map(s => this.nodeById.get(s)).find(Boolean);
      if (nb) {
        pos = nb.pos.clone().add(new THREE.Vector3((Math.random() - 0.5) * 18, (Math.random() - 0.5) * 18, (Math.random() - 0.5) * 18));
      } else {
        pos = _fib(THREE, this.nodes.length, this.nodes.length + 1, this.R * (0.66 + Math.random() * 0.3));
      }
      const dcol = (this._colorMap && this._colorMap.get(node.folder || node.color)) != null
        ? this._colorMap.get(node.folder || node.color) : 0x43e0a3;
      target = this._addNodeSprite(THREE, { id: node.id, label: node.label, path: node.path, links: node.links || 0, color: node.color }, pos, false, dcol, nb ? nb.ci : -1);
      created = true;
      this._births.set(target.sprite, 36);
    } else {
      if (node.color) { target.color = node.color; try { target.sprite.material.color.set(node.color); } catch (_) {} }
      if (node.path) target.path = node.path;
      if (node.label) target.label = node.label;
    }

    // thêm cạnh mới tới các link target đã tồn tại
    const newEdges = [];
    (linkTargets || []).forEach(stem => {
      const tgt = this.nodeById.get(stem);
      if (!tgt || tgt.id === target.id) return;
      newEdges.push({ source: target.id, target: tgt.id });
      target.links++; tgt.links++;
    });
    if (newEdges.length) {
      // gom lại toàn bộ cạnh hiện có + cạnh mới rồi dựng lại (đơn giản, chắc chắn đúng)
      this._allEdges = (this._allEdges || []).concat(newEdges);
      this._rebuildLinks(THREE, this._allEdges);
    } else if (created) {
      this._allEdges = this._allEdges || [];
    }
    this._rebuildAdj();
    this._rebuildRel();
    return { created };
  }

  nodeStats() { return { nodes: this.nodes.length, links: this._linkCount }; }

  // ---- ĐIỀU KHIỂN HIỆU ỨNG (nút trên thanh nav) ----
  // Bật/tắt lồng cầu + vành xích đạo ("Hành tinh")
  setPlanet(on) {
    if (!this._ready) return;
    (this._cage || []).forEach(l => { l.visible = on; });
    (this._ringParts || []).forEach(o => { o.visible = on; });
    this._planetOff = !on;
  }
  // Khóa/mở xoay tự động
  setLock(on) { this._locked = on; this.autoSpin = !on && !this.selected; }
  // Tiêu điểm 1 cụm: làm mờ các cụm khác (ci = -1 để bỏ tiêu điểm)
  setFocus(ci) {
    this._focusCi = (ci == null ? -1 : ci);
    const active = this._focusCi;
    this.nodes.forEach(n => {
      const on = active < 0 || n.ci === active;
      if (n.sprite && n.sprite.material) n.sprite.material.opacity = on ? (n.baseOpacity || 0.9) : 0.06;
    });
    if (this._linkObj) this._linkObj.material.opacity = active < 0 ? 0.8 : 0.14;
  }
  // Chiếu 1 node ra toạ độ pixel trong container (để đặt thẻ chi tiết cho khéo)
  projectNode(node) {
    if (!this._ready || !node) return null;
    const v = node.pos.clone().project(this.camera);
    const r = this.container.getBoundingClientRect();
    return {
      x: (v.x * 0.5 + 0.5) * r.width,
      y: (-v.y * 0.5 + 0.5) * r.height,
      onScreen: v.z < 1 && Math.abs(v.x) <= 1.2 && Math.abs(v.y) <= 1.2,
    };
  }
  // Bỏ chọn (đóng thẻ chi tiết): tắt prism, về xoay tự do (nếu không khoá)
  clearSelection() { this._deselect(); if (this._locked) this.autoSpin = false; }
  // Danh sách cụm (để dựng chú giải / nút tiêu điểm)
  clusters() {
    const seen = new Map();
    this.nodes.forEach(n => { if (!seen.has(n.ci)) seen.set(n.ci, { ci: n.ci, color: n.dcolor, count: 0 }); seen.get(n.ci).count++; });
    return [...seen.values()].filter(c => c.ci >= 0).sort((a, b) => a.ci - b.ci);
  }
  setLevel(l) { this.level = l || 0; }

  setThinking(active) {
    this._thinking = active;
    if (!active) this._firing.clear();
  }

  // -------------------------------------------------- VÒNG LẶP
  _animate() {
    const THREE = window.THREE;
    const tick = () => {
      if (this._paused) { this._raf = null; return; }
      this._raf = requestAnimationFrame(tick);
      if (!this._ready || document.hidden) return;
      const now = performance.now();
      const t = now * 0.001;

      // mượt hoá mức âm thanh -> nhịp thở
      const lv = this.level || 0;
      if (lv > this._smooth) this._smooth += (lv - this._smooth) * 0.5;
      else this._smooth += (lv - this._smooth) * 0.12;
      const lvl = this._smooth;

      // quỹ đạo camera
      if (this.autoSpin && !this.dragging) this.tTheta += 0.00072;
      this.theta += (this.tTheta - this.theta) * 0.075;
      this.phi += (this.tPhi - this.phi) * 0.075;
      this.radius += (this.tRadius - this.radius) * 0.062;
      this.target.lerp(this.tTarget, 0.075);
      this.camera.position.set(
        this.target.x + this.radius * Math.sin(this.phi) * Math.cos(this.theta),
        this.target.y + this.radius * Math.cos(this.phi),
        this.target.z + this.radius * Math.sin(this.phi) * Math.sin(this.theta),
      );
      this.camera.lookAt(this.target);

      // nhân trung tâm thở + xoay
      const b = 1 + Math.sin(t * 1.5) * (0.1 + lvl * 0.4);
      this.core.scale.set(46 * b, 46 * b, 1);
      this.coreSolid.rotation.y = t * 0.28;
      this.coreSolid.rotation.x = t * 0.17;

      // sao nhấp nháy nhẹ + phồng theo giọng nói
      const pulse = 1 + lvl * 1.1;
      for (let i = 0; i < this.nodes.length; i++) {
        const n = this.nodes[i];
        const tw = 1 + Math.sin(t * 1.9 + i * 0.7) * 0.06;
        const s = n.base * tw * pulse * (this.selected === n ? 1.7 : 1);
        n.sprite.scale.set(s, s, 1);
      }

      // hiệu ứng nảy sinh (node realtime vừa xuất hiện)
      if (this._births.size) {
        for (const [sp, fr] of this._births) {
          if (!sp) { this._births.delete(sp); continue; }
          const k = fr / 36;
          const grow = 1 + k * 3.2;
          const bs = (sp.__node ? sp.__node.base : 5);
          sp.scale.set(bs * grow, bs * grow, 1);
          if (sp.material) sp.material.opacity = Math.min(1, 0.5 + (1 - k) * 0.6 + k * 0.4);
          const next = fr - 1;
          if (next <= 0) this._births.delete(sp); else this._births.set(sp, next);
        }
      }

      // hiệu ứng "suy nghĩ": vài sao loé sáng rải rác
      if (this._thinking && this.nodes.length) {
        this._frame = (this._frame || 0) + 1;
        if (this._frame % 20 === 0) {
          const seeds = Math.max(1, Math.floor(this.nodes.length * 0.02));
          for (let i = 0; i < seeds; i++) this._firing.set(Math.floor(Math.random() * this.nodes.length), 14);
        }
        for (const [idx, fr] of this._firing) {
          const n = this.nodes[idx];
          if (n) {
            const k = Math.min(1, fr / 14);
            const s = n.base * (pulse + k * 2.0);
            n.sprite.scale.set(s, s, 1);
            if (n.sprite.material) n.sprite.material.opacity = Math.min(1, 0.6 + k * 0.4);
          }
          const next = fr - 1;
          if (next <= 0) this._firing.delete(idx); else this._firing.set(idx, next);
        }
      }

      // prism xoay khi đang chọn 1 node
      if (this.prism.visible) {
        this._shells[0].rotation.set(t * 0.2, t * 0.15, 0);
        this._shells[1].rotation.set(-t * 0.26, t * 0.31, t * 0.11);
        this._shells[2].rotation.set(t * 0.41, -t * 0.22, -t * 0.17);
        const hb = 1 + Math.sin(t * 2.4) * 0.14;
        this._prismHalo.scale.set(64 * hb, 64 * hb, 1);
      }

      this.renderer.render(this.scene, this.camera);
    };
    tick();
  }

  // -------------------------------------------------- TIỆN ÍCH
  resize() {
    if (!this._ready) return;
    const W = this.container.clientWidth || window.innerWidth;
    const H = this.container.clientHeight || window.innerHeight;
    this.camera.aspect = W / H;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(W, H);
  }

  stop() { if (this._raf) cancelAnimationFrame(this._raf); this._raf = null; }
  resume() { if (!this._raf && this._ready) this._animate(); }

  pause() {
    if (this._paused) return;
    this._paused = true;
    this.stop();
  }
  wake() {
    if (!this._paused) return;
    this._paused = false;
    this.resize();
    this.resume();
  }
  isPaused() { return !!this._paused; }
}

window.BossGraph3D = BossGraph3D;
window.dispatchEvent(new Event("boss-graph3d-ready"));

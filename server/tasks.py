"""
tasks.py - Kanban Task Backlog + Dispatcher (Loop Engineering) cho Boss OS.

Biến "Tự cải thiện" từ 1 loop monolithic thành BỘ NÃO điều phối: giữ 1 backlog task,
mỗi nhịp chọn task ưu tiên cao nhất rồi ĐIỀU PHỐI xuống bộ máy workflow/agent (ĐÔI TAY)
để thực thi. Đây là sợi dây "lịch → workflow" còn thiếu.

Học state-machine từ Hermes Kanban (VALID_STATUSES, typed block, atomic claim, dispatcher
pass "reclaim stale → promote ready → run") nhưng bản Boss OS:
  - Đơn người dùng, 1 board/brain, lưu JSON trong vault (Boss/kanban.json) → portable + git-backed.
  - Tái dùng execute_workflow() headless (không dựng orchestrator mới).
  - AN TOÀN MẶC ĐỊNH: dispatch chạy nền = tool FILE-ONLY (execute_workflow(tools=SAFE)) → agent
    KHÔNG đụng MCP tiền/đơn. Task cần hành động ra ngoài → dừng ở 'review' cho người duyệt.
  - orchestration mặc định 'off' (chỉ housekeeping, không tự chạy) → bật 'auto' khi yên tâm.

State: todo → ready → running → (review | done) ; lỗi/cần người → blocked ; archived.
  - todo    : có trong backlog nhưng chưa sẵn (còn phụ thuộc chưa xong).
  - ready   : deps xong → chờ dispatch.
  - running : đang chạy (1 task/lần, v1).
  - review  : chạy xong, chờ NGƯỜI duyệt (mặc định mọi task tự chạy dừng ở đây).
  - done    : hoàn tất.
  - blocked : lỗi hoặc agent cần người quyết (block_reason).
  - archived: cất đi (không xoá thật, hồi được).

Module KHÔNG import main (tránh vòng): helper tiêm qua TasksDeps.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, List, Optional

from fastapi import APIRouter, Form, Query

from claude_cli import ClaudeCLI, cancel_all, _empty_mcp_file

VALID_STATUS = {"todo", "ready", "running", "review", "done", "blocked", "archived"}
_DONE_ISH = {"done", "archived"}
RUNNING_STALE_S = 1800   # running > 30' coi là kẹt → thu hồi về ready


def _now() -> float:
    return time.time()


def _vn() -> str:
    return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M")


def _norm_title(text: str) -> str:
    """Chuẩn hoá tên task để dedup (bỏ dấu tiếng Việt + lower + gọn khoảng trắng)."""
    t = unicodedata.normalize("NFD", (text or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t)).strip()


@dataclass
class TasksDeps:
    brain_root: Callable[[str], str]
    atomic_write_text: Callable[[Any, str], None]
    execute_workflow: Callable                     # async gen: execute_workflow(brain, slug, input, tools)
    workflows_dir: Callable[[str], Path]
    build_system_prompt: Callable[[str], str]
    aux_model: Callable[[], Optional[str]]
    safe_tools: List[str]


class TasksFeature:
    def __init__(self, deps: TasksDeps):
        self.deps = deps
        self.lock = asyncio.Lock()          # serialize dispatch (1 worker/lần v1)
        self._io = asyncio.Lock()           # serialize ghi board
        self.router = self._make_router()

    # ── store (JSON trong brain) ──
    def _path(self, brain: str) -> Path:
        return Path(self.deps.brain_root(brain)) / "Boss" / "kanban.json"

    def _load(self, brain: str) -> dict:
        p = self._path(brain)
        board = {"orchestration": "off", "tasks": [], "updated": 0.0}
        try:
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    board.update(data)
                    if not isinstance(board.get("tasks"), list):
                        board["tasks"] = []
        except Exception:
            pass
        return board

    def _save(self, brain: str, board: dict) -> None:
        board["updated"] = _now()
        self.deps.atomic_write_text(self._path(brain), json.dumps(board, ensure_ascii=False, indent=2))

    def _by_id(self, board: dict) -> dict:
        return {t["id"]: t for t in board.get("tasks", [])}

    def _log(self, task: dict, msg: str) -> None:
        task.setdefault("log", []).append({"ts": _vn(), "msg": msg})
        task["log"] = task["log"][-20:]
        task["updated_at"] = _now()

    # ── generator API (learn/loop/user gọi để enqueue) ──
    def enqueue(self, brain: str, title: str, intent: str, route: str = "auto",
                priority: int = 2, deps: Optional[List[str]] = None,
                needs_approval: bool = True, created_by: str = "user") -> str:
        board = self._load(brain)
        # Dedup theo tên chuẩn hoá: đã có task CHƯA XONG trùng tên → trả id cũ, không tạo mới
        # (chống learn đề xuất lại mỗi batch; done/archived không tính → việc định kỳ lặp được).
        norm = _norm_title(title or intent)
        if norm:
            for t in board.get("tasks", []):
                if t.get("status") not in _DONE_ISH and _norm_title(t.get("title", "")) == norm:
                    return t["id"]
        tid = "t_" + uuid.uuid4().hex[:10]
        task = {
            "id": tid, "title": (title or intent or "Task")[:120], "intent": intent or title or "",
            "route": (route or "auto"), "priority": max(1, min(3, int(priority or 2))),
            "status": "todo", "deps": list(deps or []), "needs_approval": bool(needs_approval),
            "block_reason": "", "created_by": created_by, "created_at": _now(), "updated_at": _now(),
            "result": "", "log": [],
        }
        self._log(task, f"tạo bởi {created_by}")
        board["tasks"].append(task)
        self._recompute_ready(board)
        self._save(brain, board)
        return tid

    # ── housekeeping ──
    def _recompute_ready(self, board: dict) -> int:
        """todo có đủ deps done/archived → ready. Trả số task vừa promote."""
        by = self._by_id(board)
        n = 0
        for t in board["tasks"]:
            if t.get("status") != "todo":
                continue
            deps = t.get("deps") or []
            if all((by.get(d, {}).get("status") in _DONE_ISH) for d in deps):
                t["status"] = "ready"; self._log(t, "đủ điều kiện → ready"); n += 1
        return n

    def _reclaim_stale(self, board: dict) -> int:
        n = 0
        for t in board["tasks"]:
            if t.get("status") == "running" and _now() - float(t.get("updated_at", 0)) > RUNNING_STALE_S:
                t["status"] = "ready"; t["block_reason"] = ""
                self._log(t, "thu hồi (chạy quá lâu) → ready"); n += 1
        return n

    def _pick(self, board: dict) -> Optional[dict]:
        ready = [t for t in board["tasks"] if t.get("status") == "ready"]
        if not ready:
            return None
        ready.sort(key=lambda t: (int(t.get("priority", 2)), float(t.get("created_at", 0))))
        return ready[0]

    # ── DISPATCH (1 pass) ──
    async def dispatch_pass(self, brain: str, force: bool = False) -> dict:
        """1 nhịp điều phối: thu hồi kẹt → promote ready → (auto hoặc force) chạy 1 task.
        force=True: nút 'Nudge dispatcher' - chạy 1 task dù orchestration != auto (trừ 'off' vẫn chạy khi nudge)."""
        # housekeeping luôn chạy (kể cả off)
        async with self._io:
            board = self._load(brain)
            self._reclaim_stale(board)
            self._recompute_ready(board)
            self._save(brain, board)
            mode = board.get("orchestration", "off")

        if not (force or mode == "auto"):
            return {"ok": True, "ran": None, "note": f"orchestration={mode} (không tự chạy)"}
        if self.lock.locked():
            return {"ok": True, "ran": None, "note": "đang có task chạy"}

        async with self.lock:
            async with self._io:
                board = self._load(brain)
                task = self._pick(board)
                if not task:
                    return {"ok": True, "ran": None, "note": "không có task ready"}
                task["status"] = "running"; task["block_reason"] = ""
                self._log(task, "dispatcher claim → running")
                self._save(brain, board)
                tid = task["id"]

            result, err, needs_input = await self._execute(brain, task)

            async with self._io:
                board = self._load(brain)
                t = self._by_id(board).get(tid)
                if t:
                    t["result"] = (result or "")[:4000]
                    if err:
                        t["status"] = "blocked"; t["block_reason"] = "error"
                        self._log(t, "lỗi khi chạy → blocked: " + err[:160])
                    elif needs_input:
                        t["status"] = "blocked"; t["block_reason"] = "needs_input"
                        self._log(t, "agent cần người quyết → blocked")
                    elif t.get("needs_approval", True):
                        t["status"] = "review"; self._log(t, "xong → chờ duyệt (review)")
                    else:
                        t["status"] = "done"; self._log(t, "xong → done")
                    self._recompute_ready(board)
                    self._save(brain, board)
            return {"ok": True, "ran": tid, "status": (t or {}).get("status")}

    async def _execute(self, brain: str, task: dict):
        """Thực thi task nền = FILE-ONLY (an toàn). Route:
          - 'wf:<slug>' → chạy workflow qua execute_workflow (tools=SAFE).
          - còn lại (auto/agent/trực tiếp) → spawn 1 claude file-only với intent.
        Trả (result, error, needs_input)."""
        route = (task.get("route") or "auto").strip()
        intent = task.get("intent") or task.get("title") or ""
        safe = self.deps.safe_tools

        if route.startswith("wf:"):
            slug = route[3:].strip()
            result, err = "", ""
            try:
                async for ev in self.deps.execute_workflow(brain, slug, intent, safe):
                    et = ev.get("type")
                    if et == "done":
                        result = ev.get("result", "") or result
                    elif et == "error":
                        err = ev.get("content", "") or err
                    elif et == "step_error":
                        err = ev.get("content", "") or err
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
            ni = "[[NEEDS_INPUT]]" in (result or "")
            return result, (err or None), ni

        # direct: 1 claude file-only
        cli = ClaudeCLI(system_prompt=self.deps.build_system_prompt(brain),
                        cwd=self.deps.brain_root(brain), tag="dispatch", allowed_tools=safe)
        mcpf = _empty_mcp_file()
        if mcpf:
            cli.mcp_config = mcpf; cli.mcp_strict = True
        cli.disallowed_tools = ["Bash", "WebFetch", "WebSearch", "Task"]
        cli.model = self.deps.aux_model() or None
        cli.max_wall_s = 300
        if not cli.is_available():
            return "", "Claude CLI chưa cài", False
        prompt = (
            "NHIỆM VỤ NỀN (chỉ thao tác FILE trong vault, KHÔNG gọi MCP tiền/đơn, KHÔNG đăng bài):\n"
            + intent + "\n\n"
            "Tạo/cập nhật file NHÁP kết quả trong vault (vd '05 - Projects' hoặc Boss/). "
            "Nếu việc BẮT BUỘC cần người quyết (thiếu thông tin/quyền/hành động ra ngoài) → ghi rõ '[[NEEDS_INPUT]]' + lý do. "
            "Cuối cùng báo cáo NGẮN: đã làm gì, ghi file nào."
        )
        out, err = "", ""
        try:
            async for ev in cli.query(prompt):
                if ev["type"] == "final":
                    out = ev.get("content", "") or out
                elif ev["type"] == "error":
                    err = ev.get("content", "") or err
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
        return out, (err or None), ("[[NEEDS_INPUT]]" in out)

    # scheduler gọi
    async def tick(self, brains: List[str]) -> None:
        for brain in brains:
            try:
                await self.dispatch_pass(brain, force=False)
            except Exception as e:
                print(f"[kanban tick] {type(e).__name__}: {e}", file=__import__('sys').stderr)

    # ── router ──
    def _make_router(self) -> APIRouter:
        router = APIRouter()

        @router.get("/kanban")
        async def kanban_get(brain: str = Query("brain")):
            board = self._load(brain)
            cols = {s: [] for s in ("todo", "ready", "running", "review", "blocked", "done")}
            for t in board.get("tasks", []):
                s = t.get("status", "todo")
                if s == "archived":
                    continue
                cols.setdefault(s, []).append(t)
            for s in cols:
                cols[s].sort(key=lambda t: (int(t.get("priority", 2)), float(t.get("created_at", 0))))
            return {"orchestration": board.get("orchestration", "off"),
                    "columns": cols, "running": self.lock.locked(),
                    "counts": {s: len(v) for s, v in cols.items()}}

        @router.post("/kanban/task")
        async def kanban_add(
            title: str = Form(...), intent: str = Form(""), route: str = Form("auto"),
            priority: str = Form("2"), deps: str = Form(""), needs_approval: str = Form("1"),
            brain: str = Form("brain"),
        ):
            dl = [d.strip() for d in (deps or "").split(",") if d.strip()]
            try:
                pr = int(priority)
            except ValueError:
                pr = 2
            tid = self.enqueue(brain, title, intent or title, route or "auto", pr, dl,
                               needs_approval in ("1", "true", "True", "on"), "user")
            return {"ok": True, "id": tid}

        @router.post("/kanban/task/move")
        async def kanban_move(id: str = Form(...), status: str = Form(...), brain: str = Form("brain")):
            if status not in VALID_STATUS:
                return {"ok": False, "error": "status không hợp lệ"}
            async with self._io:
                board = self._load(brain)
                t = self._by_id(board).get(id)
                if not t:
                    return {"ok": False, "error": "not found"}
                t["status"] = status; self._log(t, f"người dùng chuyển → {status}")
                if status != "blocked":
                    t["block_reason"] = ""
                self._recompute_ready(board)
                self._save(brain, board)
            return {"ok": True, "status": status}

        @router.post("/kanban/task/delete")
        async def kanban_delete(id: str = Form(...), brain: str = Form("brain")):
            """Archive (không xoá thật). Xoá hẳn chỉ khi đã archived."""
            async with self._io:
                board = self._load(brain)
                t = self._by_id(board).get(id)
                if not t:
                    return {"ok": False, "error": "not found"}
                if t.get("status") == "archived":
                    board["tasks"] = [x for x in board["tasks"] if x["id"] != id]
                    self._save(brain, board)
                    return {"ok": True, "deleted": True}
                t["status"] = "archived"; self._log(t, "archived")
                self._save(brain, board)
            return {"ok": True, "archived": True}

        @router.post("/kanban/orchestration")
        async def kanban_orch(mode: str = Form(...), brain: str = Form("brain")):
            if mode not in ("off", "manual", "auto"):
                return {"ok": False, "error": "mode không hợp lệ"}
            async with self._io:
                board = self._load(brain)
                board["orchestration"] = mode
                self._save(brain, board)
            return {"ok": True, "orchestration": mode}

        @router.post("/kanban/nudge")
        async def kanban_nudge(brain: str = Form("brain")):
            """Chạy 1 task ready ngay (kể cả orchestration=off/manual)."""
            asyncio.create_task(self.dispatch_pass(brain, force=True))
            return {"ok": True, "started": True}

        @router.post("/kanban/run")
        async def kanban_run_one(id: str = Form(...), brain: str = Form("brain")):
            """Ép chạy 1 task cụ thể ngay: đưa về ready rồi nudge."""
            async with self._io:
                board = self._load(brain)
                t = self._by_id(board).get(id)
                if not t:
                    return {"ok": False, "error": "not found"}
                t["status"] = "ready"; t["block_reason"] = ""
                self._log(t, "người dùng ép chạy → ready")
                self._save(brain, board)
            asyncio.create_task(self.dispatch_pass(brain, force=True))
            return {"ok": True, "started": True}

        @router.post("/kanban/stop")
        async def kanban_stop():
            return {"ok": True, "cancelled": cancel_all("dispatch") + cancel_all("workflow")}

        return router


def register(app, deps: TasksDeps) -> TasksFeature:
    feat = TasksFeature(deps)
    app.include_router(feat.router)
    return feat

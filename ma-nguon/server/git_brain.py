"""
git_brain.py - Lớp an toàn dữ liệu cho engine tự học (learn.py / self_improve.py).

Vì sao tồn tại: mọi cơ chế rollback của việc học (snapshot / undo / diff-scope) dựa trên
brain là 1 git repo. NHƯNG mặc định Docker mount `boss-brains:/brains` là named volume
KHÔNG có git (backup git chỉ là bước thủ công comment trong docker-compose). Do đó:

  - Fail-closed: write-mode học CHỈ chạy khi brain là git checkout (is_git_checkout).
    ensure_git_repo() được gọi lúc BẬT học để git-init + commit nền.
  - KHÔNG `git add -A` (tránh commit state bẩn / secret lọt redaction) → chỉ add đúng path
    engine vừa ghi (commit_paths).
  - undo = git revert commit học cuối (revert_last_learn).
  - BrainLock: khoá cấp file (cross-platform) mà MỌI đường ghi (learn worker, curator,
    /reflect, và script backup ngoài nếu hợp tác) phải giành → serialize snapshot→ghi→commit,
    chống đua với tiến trình backup ngoài (asyncio.Lock không bảo vệ được tiến trình khác).

Stdlib-only. Không thêm dependency.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional

# Commit ĐÁNG coi là "học" (hiện ở review + undo được). Baseline dùng "chore:" nên KHÔNG
# lọt vào đây → bấm undo khi chưa học gì sẽ báo "không có commit học" thay vì lỡ revert baseline.
# /reflect ghi qua engine nên commit là "learn:" (không phải "reflect:").
LEARN_COMMIT_PREFIXES = ("learn:", "curator:")


def _no_window():
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def has_git() -> bool:
    return shutil.which("git") is not None


def _git(root: str, *args, timeout: int = 30) -> subprocess.CompletedProcess:
    """Chạy git trong <root>. KHÔNG raise; caller đọc returncode/stdout."""
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout, creationflags=_no_window(),
    )


def is_git_checkout(root: str) -> bool:
    """root có phải git repo (có .git)?"""
    try:
        if not (Path(root) / ".git").exists():
            return False
        r = _git(root, "rev-parse", "--is-inside-work-tree")
        return r.returncode == 0 and "true" in (r.stdout or "").lower()
    except Exception:
        return False


_GITIGNORE = (
    "# Boss OS brain - KHÔNG commit: khoá, log thô (có thể chứa secret), nhật ký nền.\n"
    "# Git chỉ version TRI THỨC ĐÃ CHƯNG CẤT (facts/wiki/skills/MEMORY.md) → undo sạch, an toàn.\n"
    ".boss-learn.lock\n"
    "Boss/learn-staging/\n"
    "Boss/learn-log/\n"
    "Boss/loop-log/\n"
    "memory/conversations/\n"
    "Memory/conversations/\n"
    "*.tmp\n"
)


def ensure_git_repo(root: str) -> dict:
    """Biến brain thành git repo nếu chưa (gọi khi BẬT học). Idempotent.
    Trả {ok, created, error}. KHÔNG push (backup là việc user chủ động)."""
    root = str(root)
    if not has_git():
        return {"ok": False, "created": False, "error": "Máy chưa cài git"}
    if is_git_checkout(root):
        return {"ok": True, "created": False}
    try:
        Path(root).mkdir(parents=True, exist_ok=True)
        r = _git(root, "init")
        if r.returncode != 0:
            return {"ok": False, "created": False, "error": (r.stderr or "git init lỗi")[:200]}
        # Cấu hình identity cục bộ (repo có thể chạy trong container không có global config)
        _git(root, "config", "user.email", "boss@localhost")
        _git(root, "config", "user.name", "Boss Learn")
        gi = Path(root) / ".gitignore"
        if not gi.exists():
            gi.write_text(_GITIGNORE, encoding="utf-8")
        _git(root, "add", ".gitignore")
        _git(root, "add", "-A")   # commit NỀN duy nhất được phép add -A (baseline, chưa có state học)
        c = _git(root, "commit", "-m", "chore: baseline brain snapshot (bật tự học)")
        return {"ok": True, "created": True, "commit": (c.stdout or "")[:120]}
    except Exception as e:
        return {"ok": False, "created": False, "error": f"{type(e).__name__}: {e}"}


def working_tree_dirty(root: str) -> bool:
    try:
        r = _git(root, "status", "--porcelain")
        return bool((r.stdout or "").strip())
    except Exception:
        return False


def changed_paths(root: str) -> List[str]:
    """Danh sách path đang thay đổi (chưa commit) - dùng cho diff-scope guard."""
    try:
        r = _git(root, "status", "--porcelain")
        out = []
        for line in (r.stdout or "").splitlines():
            # format: 'XY <path>' hoặc 'XY <old> -> <new>'
            p = line[3:].strip() if len(line) > 3 else ""
            if " -> " in p:
                p = p.split(" -> ", 1)[1]
            if p:
                out.append(p.strip('"'))
        return out
    except Exception:
        return []


def paths_within(paths: List[str], allowed_prefixes: List[str]) -> List[str]:
    """Trả path NGOÀI allowed_prefixes (rỗng = hợp lệ). Prefix so theo dạng posix."""
    bad = []
    norm_allowed = [a.replace("\\", "/").rstrip("/") + "/" for a in allowed_prefixes]
    for p in paths:
        pp = p.replace("\\", "/")
        if not any(pp.startswith(a) or (pp + "/").startswith(a) for a in norm_allowed):
            bad.append(p)
    return bad


def commit_paths(root: str, paths: List[str], msg: str) -> Optional[str]:
    """git add ĐÚNG các path (KHÔNG add -A) rồi commit. Trả commit hash ngắn hoặc None.
    An toàn: chỉ đưa vào index những gì engine chủ động ghi."""
    try:
        if not paths:
            return None
        add = _git(root, "add", "--", *paths)
        if add.returncode != 0:
            return None
        c = _git(root, "commit", "-m", msg)
        if c.returncode != 0:
            return None
        h = _git(root, "rev-parse", "--short", "HEAD")
        return (h.stdout or "").strip() or "committed"
    except Exception:
        return None


def hard_reset_paths(root: str, paths: List[str]) -> None:
    """Khôi phục các path về HEAD (dùng khi verify/secret-scan fail sau khi lỡ ghi).
    Chỉ checkout đúng path, không đụng phần còn lại."""
    try:
        if paths:
            _git(root, "checkout", "HEAD", "--", *paths)
            _git(root, "clean", "-fd", "--", *paths)
    except Exception:
        pass


def list_learn_commits(root: str, n: int = 20) -> List[dict]:
    """Liệt kê commit học gần nhất (prefix learn:/curator:/reflect:) + file đổi - cho Review UI."""
    if not is_git_checkout(root):
        return []
    try:
        r = _git(root, "log", "-n", str(n * 3), "--pretty=format:%h\x1f%ct\x1f%s", "--name-only")
        out: List[dict] = []
        blocks = (r.stdout or "").split("\n\n")
        for blk in blocks:
            lines = [l for l in blk.splitlines() if l.strip()]
            if not lines:
                continue
            head = lines[0].split("\x1f")
            if len(head) < 3:
                continue
            h, ct, subj = head[0], head[1], head[2]
            if not any(subj.startswith(p) for p in LEARN_COMMIT_PREFIXES):
                continue
            files = lines[1:]
            out.append({"hash": h, "ts": float(ct or 0), "subject": subj, "files": files})
            if len(out) >= n:
                break
        return out
    except Exception:
        return []


def revert_last_learn(root: str) -> dict:
    """git revert commit HỌC gần nhất (undo 1-click). Trả {ok, reverted, subject, error}."""
    if not is_git_checkout(root):
        return {"ok": False, "error": "Brain chưa phải git repo"}
    try:
        commits = list_learn_commits(root, 1)
        if not commits:
            return {"ok": False, "error": "Không có commit học nào để undo"}
        h = commits[0]["hash"]
        # Chỉ từ chối nếu CHÍNH file trong commit học đó đang bị sửa dở (tránh mất chỉnh tay).
        # File dirty KHÔNG liên quan (conversations/log/note khác) KHÔNG chặn undo.
        target = set(commits[0].get("files") or [])
        overlap = [p for p in changed_paths(root) if p in target]
        if overlap:
            return {"ok": False, "error": f"Các file học đang bị sửa dở, hãy tự xử lý trước: {overlap[:3]}"}
        r = _git(root, "revert", "--no-edit", h)
        if r.returncode != 0:
            _git(root, "revert", "--abort")   # dọn trạng thái revert dở nếu conflict
            return {"ok": False, "error": (r.stderr or "revert lỗi")[:200]}
        return {"ok": True, "reverted": h, "subject": commits[0]["subject"]}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ============================================================
# BACKUP lên GitHub (đồng bộ brain lên repo riêng, khôi phục khi mất máy/VPS)
# ============================================================
def _redact(text: str, *secrets: str) -> str:
    """Xoá token khỏi text trước khi trả ra UI/log (git stderr có thể chứa URL kèm token)."""
    out = text or ""
    for s in secrets:
        if s and len(s) >= 6:
            out = out.replace(s, "***")
    return out


def _auth_url(repo_url: str, token: str) -> str:
    """Chèn token vào URL https cho 1 lần push (KHÔNG lưu remote → token không nằm trong .git/config).
    URL scheme khác http(s) (ssh://, git@, file://) để NGUYÊN - dùng key/local, không cần token."""
    u = (repo_url or "").strip()
    if u.startswith(("ssh://", "git@", "file://")):
        return u
    if u.startswith("http://"):
        u = "https://" + u[len("http://"):]
    if not u.startswith("https://"):
        u = "https://" + u
    rest = u[len("https://"):]
    host_part = rest.split("/", 1)[0]
    if "@" in host_part:                       # bỏ cred cũ nếu user dán sẵn
        rest = rest.split("@", 1)[1]
    return f"https://x-access-token:{token}@{rest}"


def remote_reachable(repo_url: str, token: str, timeout: int = 30) -> dict:
    """Kiểm tra token + repo hợp lệ (git ls-remote). Trả {ok, error}. Redact token khỏi lỗi."""
    if not has_git():
        return {"ok": False, "error": "Máy chưa cài git"}
    if not repo_url or not token:
        return {"ok": False, "error": "Thiếu repo URL hoặc token"}
    try:
        r = subprocess.run(["git", "ls-remote", _auth_url(repo_url, token), "HEAD"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, creationflags=_no_window())
        if r.returncode != 0:
            return {"ok": False, "error": _redact((r.stderr or "không kết nối được").strip()[:250], token)}
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": _redact(f"{type(e).__name__}: {e}", token)}


# Path (dạng posix, tương đối) KHÔNG đưa vào backup: git thô của brain (tránh nested-repo),
# hội thoại gốc/log/khoá (có thể chứa secret), file tạm.
_BACKUP_SKIP_DIRS = {".git"}
_BACKUP_SKIP_SUBSTR = ("/memory/conversations/", "/Memory/conversations/",
                       "/Boss/loop-log/", "/Boss/learn-log/", "/Boss/learn-staging/")


def _backup_skip(rel: str) -> bool:
    r = "/" + rel.replace("\\", "/") + "/"
    if any(s in r for s in _BACKUP_SKIP_SUBSTR):
        return True
    name = rel.replace("\\", "/").rsplit("/", 1)[-1]
    return name == ".boss-learn.lock" or name.endswith(".tmp")


def _sync_mirror(src: str, mirror: str) -> None:
    """Đồng bộ src -> mirror: chép file mới/đổi (bỏ .git nested + file nhạy cảm/tạm), xoá file
    thừa trong mirror. Mirror KHÔNG có .git nested nào -> git add -A ở mirror chạy sạch."""
    src, mirror = Path(src), Path(mirror)
    keep = set()
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in _BACKUP_SKIP_DIRS]
        for fn in filenames:
            full = Path(dirpath) / fn
            rel = str(full.relative_to(src))
            if _backup_skip(rel):
                continue
            keep.add(rel.replace("\\", "/"))
            dst = mirror / rel
            try:
                if dst.exists() and dst.stat().st_size == full.stat().st_size and \
                        int(dst.stat().st_mtime) >= int(full.stat().st_mtime):
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(full, dst)
            except Exception as e:
                print(f"[backup sync copy] {rel}: {e}", file=__import__('sys').stderr)
    # prune: xoá file trong mirror (trừ .git của mirror) mà src không còn
    for dirpath, dirnames, filenames in os.walk(mirror):
        if ".git" in Path(dirpath).parts:
            continue
        for fn in filenames:
            full = Path(dirpath) / fn
            rel = str(full.relative_to(mirror)).replace("\\", "/")
            if rel not in keep:
                try:
                    full.unlink()
                except Exception:
                    pass


# ============================================================
# ĐỒNG BỘ 2 CHIỀU với GitHub (máy A ⇄ repo ⇄ máy B/VPS)
#
# Thay cơ chế force-push một chiều cũ (2 máy cùng backup sẽ lặng lẽ đè nhau).
# Mỗi lượt sync_brains():
#   1. chụp brains -> mirror (repo git riêng, bỏ .git nested + file nhạy cảm) + commit
#   2. fetch remote; hoà nhập: fast-forward khi được, lệch nhau thì merge
#      - conflict cùng file: BẢN SỬA MỚI HƠN THẮNG (so commit time), bản thua lưu thành
#        <tên>.conflict-<local|remote>-<timestamp> ngay cạnh để người dùng tự quyết
#      - một bên sửa một bên xoá: bản sửa thắng (không mất dữ liệu)
#   3. áp KẾT QUẢ merge ngược về thư mục brains (chỉ đúng các file merge làm đổi,
#      guard mtime: file vừa sinh/sửa trong lúc sync thì không đè/không xoá)
#   4. push THƯỜNG (không force). Bị máy khác chen ngang -> tự fetch/merge/áp lại 1 lần.
# Bất biến an toàn: KHÔNG BAO GIỜ push khi chưa áp xong về máy (áp lỗi -> rollback mirror
# về trước merge rồi báo lỗi) -> mirror không bao giờ chứa dữ liệu remote mà máy chưa có,
# nên bước prune của lần chụp sau không thể biến dữ liệu remote thành "đã xoá".
# ============================================================
import platform
import threading

_SYNC_LOCK = threading.Lock()   # 1 phiên sync mỗi process (nút bấm + scheduler không giẫm nhau)


def _host_tag() -> str:
    """Tên máy ngắn gọn cho commit message / tên file conflict (biết bản nào từ đâu)."""
    try:
        h = (platform.node() or "").strip().lower()
        h = "".join(c if c.isalnum() or c == "-" else "-" for c in h).strip("-")
        return h[:24] or "may"
    except Exception:
        return "may"


def _git_bytes(root: str, *args, timeout: int = 30) -> subprocess.CompletedProcess:
    """git trả stdout BYTES (cho `git show` nội dung file - an toàn với file nhị phân/ảnh)."""
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, timeout=timeout, creationflags=_no_window(),
    )


def _git_lines_z(root: str, *args, timeout: int = 60) -> List[str]:
    """Chạy git với -z (NUL-separated) + quotepath=false → path tiếng Việt trả về NGUYÊN VĂN."""
    r = _git_bytes(root, "-c", "core.quotepath=false", *args, timeout=timeout)
    if r.returncode != 0:
        return []
    return [p.decode("utf-8", "replace") for p in (r.stdout or b"").split(b"\0") if p]


def _last_commit_ts(root: str, ref: str, path: str) -> int:
    try:
        r = _git(root, "log", "-1", "--format=%ct", ref, "--", path)
        return int((r.stdout or "0").strip() or 0)
    except Exception:
        return 0


def _merge_with_policy(root: str) -> dict:
    """Merge FETCH_HEAD vào HEAD của mirror. Conflict xử lý theo chính sách:
    bản có commit MỚI HƠN thắng, bản thua lưu thành file .conflict-* cạnh đó (không mất gì);
    sửa thắng xoá. Trả {merged, conflicts:[{path, winner, saved?}]} hoặc {error}."""
    m = _git(root, "merge", "--no-edit", "FETCH_HEAD", timeout=120)
    if m.returncode != 0 and "unrelated histories" in ((m.stderr or "") + (m.stdout or "")):
        # 2 máy khởi tạo mirror độc lập → lịch sử không chung gốc; merge chéo lần đầu là hợp lệ
        m = _git(root, "merge", "--no-edit", "--allow-unrelated-histories", "FETCH_HEAD", timeout=120)
    if m.returncode == 0:
        return {"merged": True, "conflicts": []}
    # Không phải trạng thái conflict (lỗi khác) → dọn và báo
    if _git(root, "rev-parse", "-q", "--verify", "MERGE_HEAD").returncode != 0:
        _git(root, "merge", "--abort")
        return {"error": "merge lỗi: " + ((m.stderr or m.stdout or "?").strip())[:250]}
    conflicts = []
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for p in _git_lines_z(root, "diff", "--name-only", "--diff-filter=U", "-z"):
        ours = _git_bytes(root, "show", f":2:{p}")     # stage 2 = bản local
        theirs = _git_bytes(root, "show", f":3:{p}")   # stage 3 = bản remote
        has_o, has_t = ours.returncode == 0, theirs.returncode == 0
        fp = Path(root) / p
        try:
            if has_o and has_t:
                remote_wins = _last_commit_ts(root, "MERGE_HEAD", p) > _last_commit_ts(root, "HEAD", p)
                winner = theirs.stdout if remote_wins else ours.stdout
                loser = ours.stdout if remote_wins else theirs.stdout
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(winner)
                if loser != winner:
                    base, ext = os.path.splitext(p)
                    cpath = f"{base}.conflict-{'local' if remote_wins else 'remote'}-{stamp}{ext or '.md'}"
                    (Path(root) / cpath).write_bytes(loser)
                    _git(root, "add", "--", p, cpath)
                    conflicts.append({"path": p, "winner": "remote" if remote_wins else "local", "saved": cpath})
                else:
                    _git(root, "add", "--", p)
            elif has_o or has_t:
                # một bên xoá, một bên sửa → GIỮ bản sửa (không để sync âm thầm mất dữ liệu)
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes((ours if has_o else theirs).stdout)
                _git(root, "add", "--", p)
                conflicts.append({"path": p, "winner": "local" if has_o else "remote",
                                  "note": "một bên xoá - giữ bản sửa"})
            else:
                _git(root, "rm", "-f", "--", p)
        except Exception as e:
            _git(root, "merge", "--abort")
            return {"error": f"xử lý conflict {p}: {type(e).__name__}: {e}"}
    c = _git(root, "commit", "--no-edit")
    if c.returncode != 0:
        _git(root, "merge", "--abort")
        return {"error": "commit merge lỗi: " + ((c.stderr or "?").strip())[:200]}
    return {"merged": True, "conflicts": conflicts}


def _integrate_remote(root: str, pre_head: Optional[str]) -> dict:
    """Hoà FETCH_HEAD vào mirror: chưa có commit local → nhận nguyên bản remote (khôi phục);
    remote đã nằm trong local → thôi; local nằm trong remote → fast-forward; lệch → merge policy."""
    if pre_head is None:
        r = _git(root, "reset", "--hard", "FETCH_HEAD")
        if r.returncode != 0:   # nhánh chưa sinh (repo rỗng) trên vài bản git → fallback checkout
            r = _git(root, "checkout", "-f", "-B", "boss-sync", "FETCH_HEAD")
            if r.returncode != 0:
                return {"error": "nhận bản remote lỗi: " + ((r.stderr or "?").strip())[:200]}
        return {"merged": True, "conflicts": []}
    head = (_git(root, "rev-parse", "HEAD").stdout or "").strip()
    fh = (_git(root, "rev-parse", "FETCH_HEAD").stdout or "").strip()
    if head == fh or _git(root, "merge-base", "--is-ancestor", "FETCH_HEAD", "HEAD").returncode == 0:
        return {"merged": False, "conflicts": []}
    if _git(root, "merge-base", "--is-ancestor", "HEAD", "FETCH_HEAD").returncode == 0:
        r = _git(root, "merge", "--ff-only", "FETCH_HEAD")
        if r.returncode != 0:
            return {"error": "fast-forward lỗi: " + ((r.stderr or "?").strip())[:200]}
        return {"merged": True, "conflicts": []}
    return _merge_with_policy(root)


def _changed_by_integration(root: str, pre_head: Optional[str]) -> set:
    """Các path mà bước hoà-nhập remote LÀM ĐỔI trong mirror (so pre_head..HEAD).
    Đây chính là danh sách cần áp ngược về brains - không đoán mò bằng mtime."""
    if _git(root, "rev-parse", "-q", "--verify", "HEAD").returncode != 0:
        return set()
    if pre_head is None:
        return set(_git_lines_z(root, "ls-tree", "-r", "--name-only", "-z", "HEAD"))
    return set(_git_lines_z(root, "diff", "--name-only", "-z", pre_head, "HEAD"))


def _apply_back(mirror: str, brains_dir: str, changed: set, sync_start: float) -> dict:
    """Áp các path `changed` (kết quả hoà nhập remote) từ mirror về brains_dir.
    - Copy nguyên tử (tmp + os.replace). File local vừa đổi TRONG lúc sync (mtime >= sync_start)
      thì không đè/không xoá - local thắng, vòng sau tự hoà tiếp.
    - Giữ BrainLock từng brain trong lúc áp để không giẫm engine học; không lấy được lock
      trong 30s vẫn áp (lock học chỉ giữ vài giây - kẹt lâu nghĩa là tiến trình chết)."""
    mirror, brains = Path(mirror), Path(brains_dir)
    rep = {"applied": 0, "deleted": 0, "failed": [], "applied_sample": [], "deleted_sample": []}
    todo = [p for p in sorted(changed) if p and not _backup_skip(p)]
    if not todo:
        return rep
    locks = []
    for top in sorted({p.split("/", 1)[0] for p in todo if "/" in p}):
        d = brains / top
        if d.is_dir():
            lk = BrainLock(str(d), timeout=30)
            if lk.acquire():
                locks.append(lk)
            else:
                print(f"[sync apply] không lấy được lock {top} sau 30s - vẫn áp tiếp",
                      file=__import__('sys').stderr)
    try:
        for rel in todo:
            src, dst = mirror / rel, brains / rel
            try:
                if src.is_file():
                    if dst.exists() and dst.stat().st_mtime >= sync_start:
                        continue   # local vừa sửa trong lúc sync → local thắng vòng này
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    # đuôi .tmp → nằm trong _backup_skip: crash giữa chừng không sinh rác vào backup
                    tmp = dst.parent / (dst.name + ".boss-sync.tmp")
                    shutil.copy2(src, tmp)
                    os.replace(tmp, dst)
                    rep["applied"] += 1
                    if len(rep["applied_sample"]) < 20:
                        rep["applied_sample"].append(rel)
                elif dst.is_file():
                    if dst.stat().st_mtime >= sync_start:
                        continue   # file vừa sinh/sửa local → không xoá
                    dst.unlink()
                    rep["deleted"] += 1
                    if len(rep["deleted_sample"]) < 20:
                        rep["deleted_sample"].append(rel)
            except Exception as e:
                rep["failed"].append(rel)
                print(f"[sync apply] {rel}: {type(e).__name__}: {e}", file=__import__('sys').stderr)
    finally:
        for lk in locks:
            lk.release()
    return rep


def _rollback_mirror(root: str, pre_head: Optional[str]) -> None:
    """Đưa mirror về trạng thái TRƯỚC khi hoà remote (dùng khi áp về máy thất bại) →
    không push, remote còn nguyên dữ liệu, vòng sau fetch/merge/áp lại từ đầu."""
    try:
        if pre_head:
            _git(root, "reset", "--hard", pre_head)
        else:
            br = (_git(root, "symbolic-ref", "--short", "HEAD").stdout or "").strip()
            if br:
                _git(root, "update-ref", "-d", f"refs/heads/{br}")
    except Exception:
        pass


def _brains_has_content(brains_dir: str) -> bool:
    """brains có file NÀO đáng backup không. Trống (máy mới/volume mới) → chế độ KHÔI PHỤC:
    không chụp snapshot (tránh ghi nhận 'xoá sạch' rồi đẩy lên đè mất backup)."""
    for dirpath, dirnames, filenames in os.walk(brains_dir):
        dirnames[:] = [d for d in dirnames if d not in _BACKUP_SKIP_DIRS]
        for fn in filenames:
            rel = str((Path(dirpath) / fn).relative_to(brains_dir))
            if not _backup_skip(rel):
                return True
    return False


def sync_brains(brains_dir: str, mirror_dir: str, repo_url: str, token: str, branch: str = "main") -> dict:
    """Đồng bộ 2 CHIỀU toàn bộ thư mục brains với repo GitHub. Trả
    {ok, pushed, committed, merged, restored, conflicts, applied, deleted, error?}."""
    if not has_git():
        return {"ok": False, "error": "Máy chưa cài git (cần cài git để đồng bộ)"}
    if not repo_url or not token:
        return {"ok": False, "error": "Chưa cấu hình repo URL hoặc token"}
    if not Path(brains_dir).is_dir():
        return {"ok": False, "error": f"Thư mục brains không tồn tại: {brains_dir}"}
    if not _SYNC_LOCK.acquire(blocking=False):
        return {"ok": False, "error": "Đang có phiên đồng bộ khác chạy - thử lại sau"}
    try:
        return _sync_brains_locked(str(brains_dir), str(mirror_dir), repo_url, token, branch)
    except Exception as e:
        return {"ok": False, "error": _redact(f"{type(e).__name__}: {e}", token)}
    finally:
        _SYNC_LOCK.release()


def _sync_brains_locked(brains_dir: str, mirror_dir: str, repo_url: str, token: str, branch: str) -> dict:
    rep = {"ok": False, "pushed": False, "committed": False, "merged": False,
           "restored": False, "conflicts": [], "applied": 0, "deleted": 0,
           "applied_sample": [], "deleted_sample": []}
    Path(mirror_dir).mkdir(parents=True, exist_ok=True)
    if not is_git_checkout(mirror_dir):
        r = _git(mirror_dir, "init")
        if r.returncode != 0:
            return {**rep, "error": (r.stderr or "git init lỗi")[:200]}
    _git(mirror_dir, "config", "user.email", "boss@localhost")
    _git(mirror_dir, "config", "user.name", f"Boss Sync ({_host_tag()})")
    # Sync truyền BYTE NGUYÊN VĂN giữa các máy: tắt autocrlf để git Windows không tự đổi
    # LF↔CRLF lúc add/checkout (nếu không, cùng 1 file sẽ lệch byte giữa local và VPS mãi mãi).
    _git(mirror_dir, "config", "core.autocrlf", "false")

    sync_start = time.time()
    if _brains_has_content(brains_dir):
        _sync_mirror(brains_dir, mirror_dir)
        _git(mirror_dir, "add", "-A")
        c = _git(mirror_dir, "commit", "-m",
                 f"backup: {time.strftime('%Y-%m-%d %H:%M:%S')} ({_host_tag()})")
        rep["committed"] = c.returncode == 0
    else:
        rep["restored"] = True   # brains trống → chỉ nhận từ remote, không ghi nhận xoá

    hv = _git(mirror_dir, "rev-parse", "-q", "--verify", "HEAD")
    pre_head = (hv.stdout or "").strip() if hv.returncode == 0 else None
    au = _auth_url(repo_url, token)

    for attempt in (1, 2):
        f = _git(mirror_dir, "fetch", au, branch, timeout=180)
        remote_missing = f.returncode != 0 and \
            "couldn't find remote ref" in ((f.stderr or "") + (f.stdout or "")).lower()
        if f.returncode != 0 and not remote_missing:
            return {**rep, "error": _redact("fetch: " + ((f.stderr or "lỗi").strip())[:250], token)}
        changed = set()
        if not remote_missing:
            m = _integrate_remote(mirror_dir, pre_head)
            if m.get("error"):
                return {**rep, "error": _redact(m["error"], token)}
            rep["merged"] = rep["merged"] or bool(m.get("merged"))
            rep["conflicts"].extend(m.get("conflicts", []))
            changed = _changed_by_integration(mirror_dir, pre_head)
        # Tự vá: file có trong HEAD mirror nhưng THIẾU trong brains → luôn áp về. Bao trường hợp
        # khôi phục khi mirror đã up-to-date (diff rỗng) + brains bị wipe/volume mới. Chỉ THÊM
        # file thiếu, không bao giờ xoá (xoá chỉ đi qua diff của bước hoà nhập).
        if _git(mirror_dir, "rev-parse", "-q", "--verify", "HEAD").returncode == 0:
            for rel in _git_lines_z(mirror_dir, "ls-tree", "-r", "--name-only", "-z", "HEAD"):
                if not _backup_skip(rel) and not (Path(brains_dir) / rel).exists():
                    changed.add(rel)
        if changed:
            ab = _apply_back(mirror_dir, brains_dir, changed, sync_start)
            rep["applied"] += ab["applied"]
            rep["deleted"] += ab["deleted"]
            rep["applied_sample"] = (rep["applied_sample"] + ab["applied_sample"])[:20]
            rep["deleted_sample"] = (rep["deleted_sample"] + ab["deleted_sample"])[:20]
            if ab["failed"]:
                # BẤT BIẾN AN TOÀN: áp không trọn → rollback mirror + KHÔNG push.
                _rollback_mirror(mirror_dir, pre_head)
                return {**rep, "error": f"Áp bản đồng bộ về máy lỗi {len(ab['failed'])} file "
                        f"(vd {ab['failed'][:2]}) - đã hoãn push, lần sau tự thử lại"}
        hv2 = _git(mirror_dir, "rev-parse", "-q", "--verify", "HEAD")
        if hv2.returncode != 0:
            rep["ok"] = True   # cả local lẫn remote đều trống → không có gì để đồng bộ
            return rep
        p = _git(mirror_dir, "push", au, f"HEAD:refs/heads/{branch}", timeout=180)
        if p.returncode == 0:
            rep["ok"] = True
            rep["pushed"] = True
            return rep
        err = (p.stderr or "").strip()
        if attempt == 1 and any(s in err for s in ("fetch first", "non-fast-forward", "rejected")):
            pre_head = (hv2.stdout or "").strip()   # máy khác vừa đẩy chen → vòng 2 hoà tiếp
            continue
        return {**rep, "error": _redact(("push: " + (err or "lỗi"))[:300], token)}
    return {**rep, "error": "push liên tục bị vượt - thử lại sau"}


# ============================================================
# BrainLock - khoá cấp file cross-platform (serialize ghi giữa CÁC tiến trình)
# ============================================================
class BrainLock:
    """Khoá độc quyền theo brain, dựa trên file <root>/.boss-learn.lock.
    POSIX: fcntl.flock; Windows: msvcrt.locking. Non-blocking + retry tới timeout.
    Dùng như context manager (chạy trong worker THREAD, không block event loop)."""

    def __init__(self, root: str, timeout: float = 30.0):
        self.path = Path(root) / ".boss-learn.lock"
        self.timeout = timeout
        self._fh = None
        self._locked = False

    def acquire(self) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(self.path, "a+")
        except Exception:
            return False
        deadline = time.time() + self.timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    self._fh.seek(0)
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._locked = True
                return True
            except OSError:
                if time.time() >= deadline:
                    try:
                        self._fh.close()
                    except Exception:
                        pass
                    self._fh = None
                    return False
                time.sleep(0.25)

    def release(self) -> None:
        if not self._fh:
            return
        try:
            if self._locked:
                if os.name == "nt":
                    import msvcrt
                    self._fh.seek(0)
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        finally:
            try:
                self._fh.close()
            except Exception:
                pass
            self._fh = None
            self._locked = False

    def __enter__(self):
        self.acquired = self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()
        return False

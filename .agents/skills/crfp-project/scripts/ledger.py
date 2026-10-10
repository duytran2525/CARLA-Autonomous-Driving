"""Read, check and keep in sync the CRFP Main ledger without loading the whole file.

    python -I -X utf8 ledger.py where                 where the ledger and the principles file are
    python -I -X utf8 ledger.py brief                 sections 1-3: conventions, task table, SOTA conditions
    python -I -X utf8 ledger.py row M21 M30           full rows, one field per line
    python -I -X utf8 ledger.py list --status "Mở" --pha 0 [--type Task] [--text benchmark]
    python -I -X utf8 ledger.py log [N] [--full]      last N entries of the operations log (default 8)
    python -I -X utf8 ledger.py next-id               next free M-number
    python -I -X utf8 ledger.py check                 structure, references, view drift, size
    python -I -X utf8 ledger.py sync-views            copy Pha / Bước / Trạng thái from the Main table into section 2

Standard library only. The ledger path can be forced with the CRFP_LEDGER environment variable.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REL = Path("docs/crfp/crfp-main-ledger.md")
PRINCIPLES = Path("docs/crfp/crfp-8-nguyen-tac-5-idea.md")
DEFAULT_REPO = Path("D:/AI/CARLA-Funny-Moments")
STATUSES = ("Mở", "Đang làm", "Bị chặn", "Đã trả lời chờ kiểm chứng", "Đóng", "Hoãn", "Bỏ")
COLS = ("ID", "Câu hỏi", "Nguồn", "Trạng thái", "Trả lời", "Bằng chứng & ngày", "Phụ thuộc", "Pha", "Bước",
        "Quyết / Phụ trách", "Hạn", "Loại")
FAMILY = {"M22", "M22b", "M31", "M35"}  # names of split rows that appear in prose, not rows themselves
PIPE = re.compile(r"(?<!\\)\|")
ROW = re.compile(r"^\| (M\d+[abc]?) \|")
ID = re.compile(r"(?<![\w-])M(\d+)([abc]?)\b")


def worktrees() -> list[Path]:
    for cwd in (Path.cwd(), DEFAULT_REPO):
        try:
            out = subprocess.run(["git", "-C", str(cwd), "worktree", "list", "--porcelain"],
                                 capture_output=True, text=True, encoding="utf-8", check=True).stdout
            return [Path(line[9:]) for line in out.splitlines() if line.startswith("worktree ")]
        except (OSError, subprocess.CalledProcessError):
            continue
    return [DEFAULT_REPO]


def locate() -> tuple[Path, list[Path]]:
    """The main checkout wins; otherwise the most recently modified copy. Returns (chosen, all copies)."""
    if os.environ.get("CRFP_LEDGER"):
        return Path(os.environ["CRFP_LEDGER"]), []
    trees = worktrees()
    copies = [t / REL for t in trees if (t / REL).is_file()]
    if not copies:
        sys.exit(f"No ledger found. Looked for {REL} in: " + ", ".join(map(str, trees)))
    main = trees[0] / REL
    return (main if main in copies else max(copies, key=lambda p: p.stat().st_mtime)), copies


def rogue_copies(path: Path, copies: list[Path]) -> list[Path]:
    """Copies that hold edits the source does not have. A worktree that merely has an older committed
    version checked out is a harmless snapshot; a copy whose content never existed on main is not."""
    others = [c for c in copies if c != path and c.read_bytes() != path.read_bytes()]
    if not others:
        return []
    def git(cwd: Path, *args: str) -> str:
        return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, encoding="utf-8").stdout
    root = path.parents[len(REL.parts) - 1]
    known = set(re.findall(r"\b[0-9a-f]{40}\b", git(root, "log", "--format=", "--raw", "--no-abbrev", "--", REL.as_posix())))
    if not known:  # the source is not committed yet: every differing copy is suspect
        return others
    return [c for c in others
            if git(c.parents[len(REL.parts) - 1], "hash-object", "--", REL.as_posix()).strip() not in known]


def split(line: str) -> list[str]:
    return [c.strip() for c in PIPE.split(line.strip())[1:-1]]


def idkey(rid: str) -> tuple[int, str]:
    m = re.match(r"M(\d+)([abc]?)", rid)
    return int(m.group(1)), m.group(2)


def short(status: str) -> str:
    return re.split(r" \(| — ", status)[0].strip()


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        self.text = path.read_text(encoding="utf-8")
        self.lines = self.text.split("\n")
        self.heads = {int(m.group(1)): i for i, l in enumerate(self.lines) if (m := re.match(r"^## (\d)\. ", l))}
        missing = [n for n in range(1, 7) if n not in self.heads]
        if missing:
            sys.exit(f"{path}: section heading(s) {missing} not found; expected '## 1.' … '## 6.'")
        self.rows = {m.group(1): split(l) for l in self.section(4) if (m := ROW.match(l))}

    def span(self, n: int) -> tuple[int, int]:
        return self.heads[n], self.heads.get(n + 1, len(self.lines))

    def section(self, n: int) -> list[str]:
        a, b = self.span(n)
        return self.lines[a:b]

    def log_entries(self) -> list[str]:
        entries: list[str] = []
        for line in self.section(6)[1:]:
            if line.startswith("- "):
                entries.append(line)
            elif line.strip() and entries:
                entries[-1] += "\n" + line
        return entries


def cmd_where(_: list[str]) -> int:
    path, copies = locate()
    print("ledger:    ", path)
    principles = path.parent / PRINCIPLES.name
    print("principles:", principles if principles.is_file() else f"{principles} (MISSING)")
    others = rogue_copies(path, copies)
    for c in others:
        print("WARNING: this copy holds edits that the source does not have:", c)
    if others:
        print("There must be one source. Reconcile the copies before editing.")
    return 1 if others else 0


def cmd_brief(_: list[str]) -> int:
    led = Ledger(locate()[0])
    print("\n".join(led.lines[: led.heads[4]]))
    print(f"[sections 1-3 of {led.path}; use `row <ID>` for a full row and `log` for recent history]")
    return 0


def cmd_row(args: list[str]) -> int:
    led = Ledger(locate()[0])
    rc = 0
    for rid in args:
        cells = led.rows.get(rid)
        if not cells:
            print(f"{rid}: no such row")
            rc = 1
            continue
        print(f"=== {rid} ===")
        for name, cell in zip(COLS[1:], cells[1:]):
            print(f"{name}: {cell.replace(chr(92) + '|', '|') or '(trống)'}")
        print()
    return rc


def cmd_list(args: list[str]) -> int:
    opts = dict(zip(args[::2], args[1::2]))
    led = Ledger(locate()[0])
    n = 0
    for rid in sorted(led.rows, key=idkey):
        c = led.rows[rid]
        if "--status" in opts and short(c[3]) != opts["--status"]:
            continue
        if "--pha" in opts and c[7] != opts["--pha"]:
            continue
        if "--type" in opts and c[11] != opts["--type"]:
            continue
        if "--text" in opts and opts["--text"].lower() not in " ".join(c).lower():
            continue
        q = c[1] if len(c[1]) <= 90 else c[1][:87] + "…"
        print(f"{rid:5s} | {short(c[3]):26s} | pha {c[7]:1s} | bước {c[8]:2s} | {q}")
        n += 1
    print(f"[{n} hàng]")
    return 0


def cmd_log(args: list[str]) -> int:
    full = "--full" in args
    nums = [a for a in args if a.isdigit()]
    entries = Ledger(locate()[0]).log_entries()
    for e in entries[-(int(nums[0]) if nums else 8):]:
        print(e if full or len(e) <= 500 else e[:500] + " … [--full để xem hết]")
        print()
    print(f"[{len(entries)} mục trong sổ vận hành]")
    return 0


def cmd_next_id(_: list[str]) -> int:
    print("M" + str(max(idkey(r)[0] for r in Ledger(locate()[0]).rows) + 1))
    return 0


def task_rows(led: Ledger) -> list[tuple[int, list[str]]]:
    a, b = led.span(2)
    return [(i, split(led.lines[i])) for i in range(a, b) if ROW.match(led.lines[i])]


def cmd_check(_: list[str]) -> int:
    path, copies = locate()
    led = Ledger(path)
    errors: list[str] = []
    warns: list[str] = []
    for c in rogue_copies(path, copies):
        errors.append(f"a second copy holds edits that the source does not have: {c}")
    width = None
    for n, line in enumerate(led.lines, 1):  # every table keeps one column count
        if line.startswith("|"):
            k = len(PIPE.split(line.strip())) - 2
            width = width or k
            if k != width:
                errors.append(f"line {n}: {k} columns in a {width}-column table (unescaped '|' in a cell?)")
        else:
            width = None
    main_ids = [m.group(1) for l in led.section(4) if (m := ROW.match(l))]
    if len(main_ids) != len(set(main_ids)):
        errors.append("duplicate IDs in the Main table: " + ", ".join(sorted({i for i in main_ids if main_ids.count(i) > 1})))
    if main_ids != sorted(main_ids, key=idkey):
        warns.append("Main table is not sorted by ID")
    for rid, c in led.rows.items():
        if len(c) != len(COLS):
            errors.append(f"{rid}: {len(c)} cells, expected {len(COLS)}")
        elif short(c[3]) not in STATUSES:
            errors.append(f"{rid}: status must start with one of {STATUSES}; got '{c[3][:40]}'")
    top = max(idkey(r)[0] for r in led.rows)
    ghosts = sorted({f"M{n}{s}" for n, s in ID.findall(led.text)
                     if f"M{n}{s}" not in led.rows and f"M{n}{s}" not in FAMILY and 0 < int(n) <= top}, key=idkey)
    if ghosts:
        errors.append("IDs mentioned but not defined as rows: " + ", ".join(ghosts))
    seen: dict[str, int] = {}
    for _, c in task_rows(led):
        seen[c[0]] = seen.get(c[0], 0) + 1
        r = led.rows.get(c[0])
        if r and (c[2], c[3], c[4]) != (r[7], r[8], short(r[3])):
            errors.append(f"task table {c[0]}: shows pha/bước/trạng thái = {c[2]}/{c[3]}/{c[4]}, Main says "
                          f"{r[7]}/{r[8]}/{short(r[3])}  (run sync-views)")
    for rid in led.rows:
        if seen.get(rid, 0) != 1:
            errors.append(f"task table lists {rid} {seen.get(rid, 0)} times; every row must appear exactly once")
    size = len(led.text.encode("utf-8"))
    parts = {n: len("\n".join(led.section(n)).encode("utf-8")) for n in range(1, 7)}
    print(f"{path}\n{len(led.rows)} hàng | {size / 1024:.0f} KB | " +
          " | ".join(f"phần {n}: {b / 1024:.0f} KB" for n, b in parts.items()))
    print("brief (phần 1-3):", f"{sum(parts[n] for n in (1, 2, 3)) / 1024:.0f} KB")
    longest = sorted(((len(c[4]), rid) for rid, c in led.rows.items()), reverse=True)[:5]
    print("ô Trả lời dài nhất:", ", ".join(f"{rid} ({n} ký tự)" for n, rid in longest))
    if parts[6] > 0.5 * size:
        warns.append("the operations log is more than half of the file: propose archiving old entries to the project lead")
    if sum(parts[n] for n in (1, 2, 3)) > 60_000:
        warns.append("sections 1-3 exceed 60 KB: the brief is no longer cheap; shorten notes in the task table")
    for w in warns:
        print("WARN:", w)
    for e in errors:
        print("ERROR:", e)
    print("OK" if not errors else f"{len(errors)} lỗi")
    return 1 if errors else 0


def cmd_sync_views(_: list[str]) -> int:
    led = Ledger(locate()[0])
    changed = 0
    for i, c in task_rows(led):
        r = led.rows.get(c[0])
        if r and (c[2], c[3], c[4]) != (r[7], r[8], short(r[3])):
            c[2], c[3], c[4] = r[7], r[8], short(r[3])
            led.lines[i] = "| " + " | ".join(c) + " |"
            changed += 1
    counts: dict[str, int] = {}
    for c in led.rows.values():
        counts[short(c[3])] = counts.get(short(c[3]), 0) + 1
    tally = (f"Số hàng theo trạng thái ({len(led.rows)} hàng): " +
             ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])) + ".")
    a, b = led.span(2)
    for i in range(a, b):
        if led.lines[i].startswith("Số hàng theo trạng thái") and led.lines[i] != tally:
            led.lines[i] = tally
            changed += 1
    if changed:
        led.path.write_text("\n".join(led.lines), encoding="utf-8", newline="\n")
    listed = {c[0] for _, c in task_rows(led)}
    missing = sorted(set(led.rows) - listed, key=idkey)
    print(f"{changed} dòng đã sửa trong phần 2.")
    if missing:
        print("Chưa có trong bảng nhiệm vụ, phải đặt tay vào đúng khối:", ", ".join(missing))
    print("Ghi chú, thứ tự, ngày của view và phần 3 / phụ lục A vẫn phải xem lại bằng tay.")
    return 0


COMMANDS = {"where": cmd_where, "brief": cmd_brief, "row": cmd_row, "list": cmd_list, "log": cmd_log,
            "next-id": cmd_next_id, "check": cmd_check, "sync-views": cmd_sync_views}

if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    sys.exit(COMMANDS[sys.argv[1]](sys.argv[2:]))

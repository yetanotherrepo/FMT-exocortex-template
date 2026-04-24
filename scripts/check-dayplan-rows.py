#!/usr/bin/env python3
"""
check-dayplan-rows.py — DayPlan row-level status validator.

Parses a DayPlan markdown file, locates the main task table under
"План на сегодня" (or variant), classifies each row's Status column,
and emits a report. Exits with code 2 if any row is non-terminal
(raw "pending" without explicit resolution).

Used in day-close protocol (Step 0 preflight) and in
protocol-artifact-validate.sh hook (pre-commit gate).

Usage:
  check-dayplan-rows.py <path-to-DayPlan.md> [--json]

Output (text, default):
  DayPlan rows: 12 total
    ✅ done: 7
    ↗️ delegated: 1
    ⏸ blocked: 1
    📦 carry: 2
    🔴 pending (UNRESOLVED): 1
      Row: WP-27 ZF4 — carry pending (no terminal status)

Exit codes:
  0 — all rows terminal
  2 — at least one row non-terminal (pending without resolution)
  3 — parse error (no table found, etc.)
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Status keywords (lowercase, normalized) → category
TERMINAL_KEYWORDS = {
    # done variants
    "done": "done",
    "completed": "done",
    "resolved": "done",
    # delegated
    "delegated": "delegated",
    # blocked (terminal only with explicit rationale elsewhere)
    "blocked": "blocked",
    # carry to next period
    "carry": "carry",
    "paused": "carry",  # treat paused as carry form
    # dropped
    "dropped": "dropped",
    "cancelled": "dropped",
    "канцель": "dropped",
    # near_done variants (acceptable terminal for last-day reports)
    "near done": "near_done",
}

# Emoji → category hint (used if keyword absent)
EMOJI_TERMINAL = {
    "✅": "done",
    "↗️": "delegated",
    "⏸": "blocked",
    "📦": "carry",
    "🔄": "carry",
    "❌": "dropped",
}

# Emoji that alone = non-terminal (must have keyword or other signal)
EMOJI_NON_TERMINAL = {"🔴", "🟡", "🟢", "⚫", "🆕", "⭕"}


def find_main_table(text: str):
    """Find the main task table under 'План на сегодня' heading (or variant).
    Returns (header_line_index, body_lines) or (None, None) if not found.
    """
    lines = text.split("\n")
    heading_re = re.compile(r"план\s+на\s+сегодня|today's plan|daily plan", re.IGNORECASE)
    # Find the heading
    start = None
    for i, line in enumerate(lines):
        stripped = re.sub(r"<[^>]+>", "", line)  # strip html tags (e.g. <summary>)
        if heading_re.search(stripped):
            start = i
            break
    if start is None:
        return None, None

    # Find first table header line after heading
    header_idx = None
    for j in range(start + 1, min(start + 40, len(lines))):
        line = lines[j]
        if "|" in line and "---" not in line:
            # Check next line is separator
            if j + 1 < len(lines) and re.match(r"^\s*\|?[\s\-:|]+\|?\s*$", lines[j + 1]):
                header_idx = j
                break
    if header_idx is None:
        return None, None

    # Collect body rows until blank line or non-table line
    body = []
    for k in range(header_idx + 2, len(lines)):
        line = lines[k]
        if not line.strip():
            break
        if "|" not in line:
            break
        body.append((k, line))
    return header_idx, body


def parse_header_columns(header_line: str):
    """Return normalized column names (lowercased, stripped)."""
    cells = [c.strip().lower() for c in header_line.strip().strip("|").split("|")]
    return cells


def extract_cell(row_line: str, col_idx: int):
    cells = [c.strip() for c in row_line.strip().strip("|").split("|")]
    if col_idx < len(cells):
        return cells[col_idx]
    return ""


def classify_status(status_cell: str, traffic_cell: str = "") -> tuple[str, bool]:
    """Return (category, is_terminal).
    Terminal categories: done, delegated, blocked, carry, dropped, near_done.
    Non-terminal: pending, unresolved.
    """
    # Check strikethrough — usually marks done/dropped rows
    cleaned = status_cell
    cleaned_lower = cleaned.lower()

    # Keyword match first
    for kw, cat in TERMINAL_KEYWORDS.items():
        if kw in cleaned_lower:
            return cat, True

    # Emoji match
    for emoji, cat in EMOJI_TERMINAL.items():
        if emoji in cleaned:
            return cat, True

    # Check traffic-light cell alone
    if traffic_cell:
        for emoji, cat in EMOJI_TERMINAL.items():
            if emoji in traffic_cell:
                return cat, True

    # Explicit pending or traffic-light only → non-terminal
    if "pending" in cleaned_lower:
        return "pending", False

    # Any non-terminal emoji without other signal
    for emoji in EMOJI_NON_TERMINAL:
        if emoji in cleaned or emoji in traffic_cell:
            return "unresolved", False

    # Empty status = unresolved
    if not cleaned:
        return "empty", False

    # Fallback: unresolved
    return f"unknown ({cleaned[:30]})", False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="Path to DayPlan markdown file")
    ap.add_argument("--json", action="store_true", help="Emit JSON output")
    args = ap.parse_args()

    p = Path(args.path).expanduser()
    if not p.exists():
        print(f"❌ File not found: {p}", file=sys.stderr)
        return 3

    text = p.read_text(encoding="utf-8")
    header_idx, body = find_main_table(text)
    if not body:
        print(f"❌ Не найдена таблица 'План на сегодня' в {p}", file=sys.stderr)
        return 3

    lines = text.split("\n")
    columns = parse_header_columns(lines[header_idx])

    # Locate key columns by normalized name
    col_status = None
    col_traffic = None
    col_name = None
    for i, c in enumerate(columns):
        if "статус" in c or "status" in c:
            col_status = i
        elif "🚦" in c or "traffic" in c or re.match(r"^\s*$", c):
            if col_traffic is None:
                col_traffic = i
        elif "рп" in c or "task" in c or "проект" in c:
            if col_name is None:
                col_name = i

    if col_status is None:
        # Try fallback — second-to-last column often has status
        col_status = len(columns) - 2 if len(columns) > 2 else len(columns) - 1

    summary = {
        "total": 0,
        "done": 0,
        "delegated": 0,
        "blocked": 0,
        "carry": 0,
        "dropped": 0,
        "near_done": 0,
        "pending": 0,
        "unresolved": 0,
        "empty": 0,
        "unknown": 0,
    }
    unresolved_rows = []

    for line_no, row_line in body:
        status_cell = extract_cell(row_line, col_status) if col_status is not None else ""
        traffic_cell = extract_cell(row_line, col_traffic) if col_traffic is not None else ""
        name_cell = extract_cell(row_line, col_name) if col_name is not None else row_line[:60]

        cat, is_terminal = classify_status(status_cell, traffic_cell)

        # Normalize category keys for summary
        key = cat.split()[0] if " " in cat else cat
        if key not in summary:
            summary["unknown"] += 1
        else:
            summary[key] += 1
        summary["total"] += 1

        if not is_terminal:
            unresolved_rows.append({
                "line": line_no + 1,
                "name": re.sub(r"\*\*|\*", "", name_cell)[:80],
                "status": status_cell[:60],
                "traffic": traffic_cell[:10],
                "category": cat,
            })

    if args.json:
        print(json.dumps({"summary": summary, "unresolved": unresolved_rows}, ensure_ascii=False, indent=2))
    else:
        print(f"DayPlan rows: {summary['total']} total")
        print(f"  ✅ done: {summary['done']}")
        if summary['delegated']:
            print(f"  ↗️ delegated: {summary['delegated']}")
        if summary['blocked']:
            print(f"  ⏸ blocked: {summary['blocked']}")
        if summary['carry']:
            print(f"  📦 carry: {summary['carry']}")
        if summary['dropped']:
            print(f"  ❌ dropped: {summary['dropped']}")
        if summary['near_done']:
            print(f"  🟢 near_done: {summary['near_done']}")
        total_unresolved = summary['pending'] + summary['unresolved'] + summary['empty'] + summary['unknown']
        if total_unresolved > 0:
            print(f"  🔴 UNRESOLVED: {total_unresolved}")
            for r in unresolved_rows:
                print(f"    Line {r['line']}: {r['name']}")
                print(f"      status='{r['status']}' traffic='{r['traffic']}' → {r['category']}")

    if len(unresolved_rows) > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

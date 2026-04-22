"""S1.1 — Timezone & DST handling audit.

Read-only static audit. Three checks:

  Check 1 — YAML time_windows: every session window in playbook YAML
    must be HH:MM strings (interpreted ET by playbook_loader). Flag any
    window that looks like UTC literal or odd shape.

  Check 2 — Production code naive-time usage: `datetime.now()` and
    `datetime.utcnow()` in production paths that influence session/daily
    decisions. Local OS time != ET, so a paper/live deployment in UTC
    triggers "new day" mid-trading-session.

  Check 3 — ZoneInfo coverage: confirm America/New_York is the only TZ
    referenced for session boundary logic.

Writes a markdown verdict to backend/data/backtest_results/timezone_audit.md.

Usage:
  cd backend && .venv/bin/python scripts/audit_timezone_handling.py \\
      --out data/backtest_results/timezone_audit.md
"""
from __future__ import annotations

import argparse
import ast
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

BACKEND = Path(__file__).resolve().parent.parent
CAMPAIGNS = BACKEND / "knowledge" / "campaigns"
PLAYBOOKS_YML = BACKEND / "knowledge" / "playbooks.yml"

CODE_DIRS = [
    BACKEND / "backtest",
    BACKEND / "engines",
    BACKEND / "models",
    BACKEND / "jobs",
    BACKEND / "routes",
]

# Files that are exempt from the naive-time scan (artifact stamps, test
# fixtures, downloads). Audit results stay informational rather than
# adding noise that hides the real session-impact hits.
NAIVE_TIME_EXEMPT_SUFFIXES = (
    "trade.py",         # Pydantic default_factory timestamps (artifacts)
    "setup.py",
    "market_data.py",
    "risk.py",
)

HHMM_RE = re.compile(r"^\d{1,2}:\d{2}$")


@dataclass
class Finding:
    severity: str  # "high" | "medium" | "low"
    file: str
    line: int | None
    detail: str

    def md_row(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else self.file
        return f"| {self.severity.upper()} | `{loc}` | {self.detail} |"


@dataclass
class AuditResult:
    yaml_findings: list[Finding] = field(default_factory=list)
    naive_time_findings: list[Finding] = field(default_factory=list)
    pytz_imports: list[Finding] = field(default_factory=list)
    tz_coverage: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return (len(self.yaml_findings) + len(self.naive_time_findings)
                + len(self.pytz_imports))


def iter_yaml_files() -> Iterable[Path]:
    yield PLAYBOOKS_YML
    yield from sorted(CAMPAIGNS.glob("*.yml"))
    yield from sorted(CAMPAIGNS.glob("*.yaml"))


def audit_yaml_time_windows(result: AuditResult) -> None:
    """Walk every YAML, flag time_windows that don't look like HH:MM ET."""
    for path in iter_yaml_files():
        if not path.exists():
            continue
        try:
            docs = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        except yaml.YAMLError as exc:
            result.yaml_findings.append(
                Finding("medium", str(path.relative_to(BACKEND)), None,
                        f"YAML parse error: {exc}")
            )
            continue
        for doc in docs:
            _walk_yaml(doc, path, result)


def _walk_yaml(node, path: Path, result: AuditResult) -> None:
    if isinstance(node, dict):
        # Per-playbook timefilters / time_windows
        tf = node.get("timefilters")
        if isinstance(tf, dict):
            windows = tf.get("time_windows") or tf.get("time_range")
            if windows:
                _check_windows(windows, path, result, ctx=node.get("playbook_name") or node.get("name"))
        # Recurse
        for v in node.values():
            _walk_yaml(v, path, result)
    elif isinstance(node, list):
        for item in node:
            _walk_yaml(item, path, result)


def _check_windows(windows, path: Path, result: AuditResult, ctx: str | None) -> None:
    rel = str(path.relative_to(BACKEND))
    name = f"playbook={ctx}" if ctx else "<no name>"
    if not isinstance(windows, list):
        result.yaml_findings.append(
            Finding("low", rel, None, f"{name}: time_windows is not a list ({type(windows).__name__})")
        )
        return
    for w in windows:
        if isinstance(w, list) and len(w) == 2:
            ok = all(isinstance(x, str) and HHMM_RE.match(x) for x in w)
            if not ok:
                result.yaml_findings.append(
                    Finding("medium", rel, None,
                            f"{name}: window {w!r} is not [HH:MM, HH:MM]")
                )
        elif isinstance(w, str) and HHMM_RE.match(w):
            # legacy time_range flat list — accepted
            continue
        else:
            result.yaml_findings.append(
                Finding("low", rel, None,
                        f"{name}: window entry {w!r} unrecognized shape")
            )


def audit_naive_time_usage(result: AuditResult) -> None:
    """Flag datetime.now() / datetime.utcnow() in production-impact code paths."""
    for d in CODE_DIRS:
        if not d.exists():
            continue
        for f in d.rglob("*.py"):
            rel = str(f.relative_to(BACKEND))
            if rel.endswith(NAIVE_TIME_EXEMPT_SUFFIXES):
                continue
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            _walk_code(tree, f, rel, result)


def _walk_code(tree, file: Path, rel: str, result: AuditResult) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = _stringify_callee(node.func)
        if callee not in {"datetime.now", "datetime.utcnow"}:
            continue
        # `datetime.now(timezone.utc)` / `datetime.now(tz=...)` is TZ-aware → skip.
        if callee == "datetime.now" and (
            node.args or any(kw.arg in {"tz", "tzinfo"} for kw in node.keywords)
        ):
            continue
        line = node.lineno
        try:
            src_line = file.read_text(encoding="utf-8").splitlines()[line - 1]
        except IndexError:
            src_line = ""
        keywords = ("session", "today", "daily", "reset", "current_time", "current_day")
        sev = "high" if any(k in src_line for k in keywords) else "medium"
        result.naive_time_findings.append(
            Finding(sev, rel, line, f"`{callee}()` near `{src_line.strip()[:120]}`")
        )


def _stringify_callee(node) -> str:
    if isinstance(node, ast.Attribute):
        parts = []
        cur = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))
    if isinstance(node, ast.Name):
        return node.id
    return ""


def audit_pytz_imports(result: AuditResult) -> None:
    """Flag any `import pytz` in production code (deprecated, ZoneInfo preferred)."""
    for d in CODE_DIRS + [BACKEND / "scripts", BACKEND / "utils"]:
        if not d.exists():
            continue
        for f in d.rglob("*.py"):
            rel = str(f.relative_to(BACKEND))
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "pytz" or alias.name.startswith("pytz."):
                            result.pytz_imports.append(
                                Finding("medium", rel, node.lineno,
                                        f"`import {alias.name}` — replace with `zoneinfo.ZoneInfo`"))
                elif isinstance(node, ast.ImportFrom):
                    if node.module and (node.module == "pytz" or node.module.startswith("pytz.")):
                        result.pytz_imports.append(
                            Finding("medium", rel, node.lineno,
                                    f"`from {node.module}` — replace with `zoneinfo.ZoneInfo`"))


def audit_tz_coverage(result: AuditResult) -> None:
    """Count ZoneInfo("America/New_York") and any other TZ string references."""
    pat_ny = re.compile(r"ZoneInfo\(\s*['\"]America/New_York['\"]\s*\)")
    pat_other = re.compile(r"ZoneInfo\(\s*['\"]([^'\"]+)['\"]\s*\)")
    counts: dict[str, int] = defaultdict(int)
    for d in CODE_DIRS:
        if not d.exists():
            continue
        for f in d.rglob("*.py"):
            txt = f.read_text(encoding="utf-8")
            counts["America/New_York"] += len(pat_ny.findall(txt))
            for tz in pat_other.findall(txt):
                if tz != "America/New_York":
                    counts[tz] += 1
    result.tz_coverage = dict(counts)


def render_md(result: AuditResult) -> str:
    lines: list[str] = []
    lines.append("# Timezone & DST handling audit (S1.1)")
    lines.append("")
    lines.append(f"**Findings**: {len(result.yaml_findings)} YAML, {len(result.naive_time_findings)} naive-time. ")
    lines.append("Generated by `backend/scripts/audit_timezone_handling.py` (read-only).")
    lines.append("")
    lines.append("## 1. YAML time_windows shape")
    lines.append("")
    if result.yaml_findings:
        lines.append("| Severity | File | Detail |")
        lines.append("|---|---|---|")
        for f in result.yaml_findings:
            lines.append(f.md_row())
    else:
        lines.append("All time_windows look like `[HH:MM, HH:MM]` (interpreted ET by `playbook_loader.py`). PASS.")
    lines.append("")
    lines.append("## 2. Naive-time usage in production code paths")
    lines.append("")
    lines.append("Filter: `datetime.now()` and `datetime.utcnow()` in `backtest/`, `engines/`, ")
    lines.append("`models/`, `jobs/`, `routes/`. `models/{trade,setup,market_data,risk}.py` exempt ")
    lines.append("(Pydantic artifact stamps). Severity HIGH if line mentions session/today/daily/reset/current_time/current_day.")
    lines.append("")
    if result.naive_time_findings:
        high = [f for f in result.naive_time_findings if f.severity == "high"]
        med = [f for f in result.naive_time_findings if f.severity == "medium"]
        lines.append(f"**HIGH-severity** (potential paper/live correctness bug — local OS != ET): {len(high)}")
        lines.append("")
        if high:
            lines.append("| Severity | Location | Detail |")
            lines.append("|---|---|---|")
            for f in high:
                lines.append(f.md_row())
            lines.append("")
        lines.append(f"**MEDIUM-severity** (artifact timestamps, run IDs, log stamps): {len(med)}")
        if med:
            lines.append("")
            lines.append("<details><summary>Show MEDIUM findings</summary>")
            lines.append("")
            lines.append("| Severity | Location | Detail |")
            lines.append("|---|---|---|")
            for f in med:
                lines.append(f.md_row())
            lines.append("")
            lines.append("</details>")
    else:
        lines.append("No `datetime.now()` / `datetime.utcnow()` usage in production code paths. PASS.")
    lines.append("")
    lines.append("## 3. pytz imports in production")
    lines.append("")
    lines.append("`pytz` is deprecated since Python 3.9 — `zoneinfo.ZoneInfo` is the standard. ")
    lines.append("`pytz` still works correctly for DST, but mixing both creates inconsistencies.")
    lines.append("")
    if result.pytz_imports:
        lines.append("| Severity | Location | Detail |")
        lines.append("|---|---|---|")
        for f in result.pytz_imports:
            lines.append(f.md_row())
    else:
        lines.append("No `pytz` imports in production code. PASS.")
    lines.append("")
    lines.append("## 4. ZoneInfo coverage")
    lines.append("")
    if result.tz_coverage:
        lines.append("| TZ string | Occurrences |")
        lines.append("|---|---:|")
        for tz, n in sorted(result.tz_coverage.items()):
            lines.append(f"| `{tz}` | {n} |")
        non_ny = [tz for tz in result.tz_coverage if tz != "America/New_York"]
        if non_ny:
            lines.append("")
            lines.append(f"**Warning**: non-ET TZs referenced: {non_ny}. Verify they are not used for session decisions.")
        else:
            lines.append("")
            lines.append("Only `America/New_York` referenced — consistent with US-equity session model.")
    else:
        lines.append("No ZoneInfo references found in production code (suspicious — DST handling likely missing).")
    lines.append("")
    lines.append("## 5. Conclusion")
    lines.append("")
    high_count = sum(1 for f in result.naive_time_findings if f.severity == "high")
    if high_count:
        lines.append(f"**Action required**: {high_count} HIGH-severity naive-time site(s). ")
        lines.append("Replace `datetime.now()` with an explicit ET clock for any session/daily-reset decision. ")
        lines.append("Backtest is unaffected (timestamps come from market data); paper/live deployments on UTC hosts ")
        lines.append("would fire daily resets at the wrong wall-clock moment.")
    elif result.yaml_findings:
        lines.append("YAML-shape findings only. No production-code naive-time hits at HIGH severity.")
    else:
        lines.append("Audit clean. Engine timezone discipline holds.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="data/backtest_results/timezone_audit.md",
                    help="Output markdown path (relative to backend/)")
    args = ap.parse_args()

    result = AuditResult()
    audit_yaml_time_windows(result)
    audit_naive_time_usage(result)
    audit_pytz_imports(result)
    audit_tz_coverage(result)

    out_path = (BACKEND / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_md(result), encoding="utf-8")

    high = sum(1 for f in result.naive_time_findings if f.severity == "high")
    print(f"Audit done. yaml={len(result.yaml_findings)} naive_high={high} "
          f"naive_total={len(result.naive_time_findings)} tz={result.tz_coverage}")
    print(f"Verdict: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

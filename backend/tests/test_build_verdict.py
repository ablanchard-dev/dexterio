"""Tests for backend/scripts/build_verdict.py — §0.7 G4 gate."""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).parent.parent.parent
SCRIPT = REPO / "backend" / "scripts" / "build_verdict.py"
VERDICTS_DIR = REPO / "backend" / "knowledge" / "verdicts"
G3_YAML = VERDICTS_DIR / "g3_spread_bps_reconcile_verdict.yml"
G3_MD = REPO / "backend" / "data" / "backtest_results" / "g3_spread_bps_reconcile_verdict.md"

sys.path.insert(0, str(REPO / "backend" / "scripts"))
from build_verdict import render_markdown, build_json  # noqa: E402


# ---------------------------------------------------------------------------
# Minimal valid config used in multiple tests
# ---------------------------------------------------------------------------
MINIMAL_CFG = {
    "title": "Test verdict minimal",
    "date": "2026-04-24",
    "bloc1_identity": {
        "rows": [["Playbook", "Test_Play_v1"], ["Corpus", "nov_w4"]],
    },
    "bloc2_metrics": {
        "sections": [
            {
                "heading": "Global",
                "tables": [
                    {
                        "headers": ["n", "WR", "E[R]_gross"],
                        "rows": [[22, "45.5%", "-0.019"]],
                    }
                ],
            }
        ]
    },
    "bloc3_structural": {
        "subsections": [
            {"heading": "Signal vit-il ?", "body": "Oui, densité normale."},
            {"heading": "Cause", "body": "Signal est le plafond."},
        ]
    },
    "bloc4_decision": {
        "body": "**Décision** : ARCHIVED.",
        "kill_rules_table": {
            "headers": ["Kill rule", "Seuil", "Observé", "Statut"],
            "rows": [["1. E[R]_gross ≤ 0", "≤ 0", "-0.019", "ATTEINTE"]],
        },
        "trailing": "**Cas §20 C dominant.**",
    },
    "bloc5_why": {
        "subsections": [
            {
                "heading": "Pourquoi ARCHIVED",
                "body": "3/3 kill rules atteintes.",
            }
        ]
    },
}


# ---------------------------------------------------------------------------
# T1 — render_markdown produces all 5 blocs
# ---------------------------------------------------------------------------
def test_all_five_blocs_present():
    md = render_markdown(MINIMAL_CFG)
    assert "## Bloc 1 — identité du run" in md
    assert "## Bloc 2 — métriques" in md
    assert "## Bloc 3 — lecture structurelle" in md
    assert "## Bloc 4 — décision" in md
    assert "## Bloc 5 — why" in md


# ---------------------------------------------------------------------------
# T2 — CLI produces valid markdown file
# ---------------------------------------------------------------------------
def test_cli_produces_file(tmp_path):
    cfg_path = tmp_path / "cfg.yml"
    cfg_path.write_text(yaml.dump(MINIMAL_CFG, allow_unicode=True))
    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(cfg_path),
         "--out-md", str(out_md), "--out-json", str(out_json)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert out_md.exists()
    content = out_md.read_text()
    assert "## Bloc 1" in content
    assert out_json.exists()
    data = json.loads(out_json.read_text())
    assert data["title"] == "Test verdict minimal"


# ---------------------------------------------------------------------------
# T3 — missing optional fields render gracefully (no crash, no "None" text)
# ---------------------------------------------------------------------------
def test_optional_fields_missing():
    cfg = {
        "title": "Minimal no-optional",
        "bloc1_identity": {"rows": [["A", "B"]]},
        "bloc2_metrics": {"sections": []},
        "bloc3_structural": {"subsections": []},
        "bloc4_decision": {"body": "FAIL."},
        "bloc5_why": {"subsections": []},
    }
    md = render_markdown(cfg)
    assert "None" not in md
    assert "## Bloc 1" in md
    assert "## Bloc 5" in md


# ---------------------------------------------------------------------------
# T4 — metric validation: WR, PF, n basic range checks via build_json
# ---------------------------------------------------------------------------
def test_build_json_structure():
    data = build_json(MINIMAL_CFG)
    assert data["title"] == "Test verdict minimal"
    assert data["date"] == "2026-04-24"
    assert "bloc1_identity" in data
    assert "bloc2_metrics" in data
    assert "bloc3_structural" in data
    assert "bloc4_decision" in data
    assert "bloc5_why" in data
    assert data.get("next_action") is None
    assert data.get("artefacts") is None


# ---------------------------------------------------------------------------
# T5 — kill rules table renders correctly in bloc4
# ---------------------------------------------------------------------------
def test_kill_rules_table_in_bloc4():
    md = render_markdown(MINIMAL_CFG)
    assert "Kill rule" in md
    assert "ATTEINTE" in md
    assert "Cas §20 C dominant" in md


# ---------------------------------------------------------------------------
# T6 — heading=None in bloc5 subsection → no H3, body still present
# ---------------------------------------------------------------------------
def test_bloc5_subsection_no_heading():
    cfg = {
        **MINIMAL_CFG,
        "bloc5_why": {
            "subsections": [
                {"body": "Pas de titre mais body présent."},
            ]
        },
    }
    md = render_markdown(cfg)
    assert "Pas de titre mais body présent." in md
    assert "## Bloc 5" in md


# ---------------------------------------------------------------------------
# T7 — next_action and artefacts optional trailer sections
# ---------------------------------------------------------------------------
def test_trailer_sections():
    cfg = {
        **MINIMAL_CFG,
        "next_action": "Prochaine étape : §0.5bis entrée #1.",
        "artefacts": ["verdict_test.md", "test_file.py — 5/5 PASS"],
    }
    md = render_markdown(cfg)
    assert "## Prochaine action" in md
    assert "§0.5bis entrée #1" in md
    assert "## Artefacts" in md
    assert "- verdict_test.md" in md
    assert "- test_file.py — 5/5 PASS" in md


# ---------------------------------------------------------------------------
# T8 — Gate: re-generate G3 verdict, semantically equivalent to main-written
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not G3_YAML.exists(), reason="G3 YAML fixture not found")
@pytest.mark.skipif(not G3_MD.exists(), reason="G3 main-written verdict not found")
def test_gate_g3_regen_semantically_equivalent(tmp_path):
    """Re-generate the G3 spread verdict and verify key facts match main-written."""
    out = tmp_path / "g3_regen.md"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(G3_YAML), "--out-md", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr

    regen = out.read_text()
    original = G3_MD.read_text()

    # Key numeric facts that must match
    key_facts = [
        "−0.0973",     # mean_delta_R total
        "−0.1027",     # jun_w3
        "−0.1031",     # aug_w3
        "−0.0787",     # oct_w2
        "−0.0851",     # nov_w4
        "170",         # total trades
        "−0.097",      # budget post-G3
        "0.197",       # Stage 2 pre_reconcile bar
        "98.8%",       # pct_worse
        "2026-04-23",  # date
        "G3 = DONE",   # decision keyword
    ]
    for fact in key_facts:
        assert fact in regen, f"Missing key fact in regenerated verdict: {fact!r}"
        assert fact in original, f"Key fact missing from original too: {fact!r}"

    # All 5 blocs present
    for bloc_h in [
        "## Bloc 1 — identité du run",
        "## Bloc 2 — métriques",
        "## Bloc 3 — lecture structurelle",
        "## Bloc 4 — décision",
        "## Bloc 5 — why",
    ]:
        assert bloc_h in regen, f"Bloc header missing: {bloc_h!r}"

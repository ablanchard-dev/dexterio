"""§0.7 G4 — Verdict templating build_verdict.py.

Standardise la génération des verdicts §18.3 (5-blocs : identité / métriques /
lecture structurelle / décision / why) depuis un YAML config, avec métriques bloc 2
optionnellement auto-calculées depuis un trades parquet.

Plan §6.4 : Input = trades parquet + config + baseline. Output = `*_verdict.md`
+ `*_verdict.json` structuré.

Gate §0.7 G4 : 1 verdict récent re-généré, identique sémantiquement à
main-written (cf `backend/data/backtest_results/g3_spread_bps_reconcile_verdict.md`).

Usage :
  .venv/bin/python backend/scripts/build_verdict.py config.yaml \\
      [--trades-parquet PATH] [--out-md PATH] [--out-json PATH]

Sans `--out-md/--out-json`, écrit md sur stdout et skip json.

Schéma YAML config (tous les champs ci-dessous sont nécessaires pour §18.3
conformité ; les sections optionnelles `next_action` + `artefacts` sont hors
5-blocs mais tolérées) :

    title: "..."              # H1 sans préfixe `# `
    date: "YYYY-MM-DD"
    plan: "..."               # optionnel, ligne meta sous le titre
    status: "..."             # optionnel, meta
    decision_line: null | "..."  # ligne bold sous meta (optionnelle)

    bloc1_identity:
      rows:                   # table 2-cols (Champ / Valeur)
        - [Playbook, "..."]
        - ...

    bloc2_metrics:
      sections:               # N sous-sections H3 avec table(s) ou texte
        - heading: "..."      # optionnel, si null = pas de H3
          tables:              # optionnel
            - headers: [...]
              align: [...]   # optionnel, ex ["---", "---:"]
              rows: [[...]]
          body: "..."          # texte libre après table(s), optionnel
      trailing: "..."         # optionnel, texte libre après sections

    bloc3_structural:
      subsections:            # N H3 narratives
        - heading: "..."
          body: "..."

    bloc4_decision:
      body: "..."             # texte libre avant kill_rules
      kill_rules_table:       # optionnel
        headers: [...]
        rows: [[...]]
      trailing: "..."         # optionnel, texte après table (classification,
                              # décision finale)

    bloc5_why:
      subsections:
        - heading: "..."      # optionnel, bullet ou sous-titre
          body: "..."

    next_action: "..."        # optionnel (hors 5-blocs, section H2 finale)
    artefacts:                # optionnel
      - "..."                 # chaque ligne = bullet markdown telle quelle
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

import yaml


SEP = "\n\n"


def _render_table(headers: list[str], rows: list[list[Any]],
                  align: Optional[list[str]] = None) -> str:
    if align is None:
        align = ["---"] * len(headers)
    lines = ["| " + " | ".join(str(h) for h in headers) + " |",
             "|" + "|".join(align) + "|"]
    for row in rows:
        lines.append("| " + " | ".join("" if v is None else str(v) for v in row) + " |")
    return "\n".join(lines)


def _render_bloc1(cfg: dict) -> str:
    rows = cfg.get("rows", [])
    table = _render_table(["Champ", "Valeur"], rows)
    return "## Bloc 1 — identité du run\n\n" + table


def _render_bloc2(cfg: dict) -> str:
    parts = ["## Bloc 2 — métriques"]
    for sec in cfg.get("sections", []):
        if sec.get("heading"):
            parts.append("### " + sec["heading"])
        for tbl in sec.get("tables", []) or []:
            parts.append(_render_table(
                tbl["headers"], tbl["rows"], tbl.get("align")))
        if sec.get("body"):
            parts.append(sec["body"])
    if cfg.get("trailing"):
        parts.append(cfg["trailing"])
    return SEP.join(parts)


def _render_bloc3(cfg: dict) -> str:
    parts = ["## Bloc 3 — lecture structurelle"]
    for sub in cfg.get("subsections", []):
        parts.append("### " + sub["heading"])
        parts.append(sub["body"])
    return SEP.join(parts)


def _render_bloc4(cfg: dict) -> str:
    parts = ["## Bloc 4 — décision"]
    if cfg.get("body"):
        parts.append(cfg["body"])
    if cfg.get("kill_rules_table"):
        tbl = cfg["kill_rules_table"]
        parts.append(_render_table(
            tbl["headers"], tbl["rows"], tbl.get("align")))
    if cfg.get("trailing"):
        parts.append(cfg["trailing"])
    return SEP.join(parts)


def _render_bloc5(cfg: dict) -> str:
    parts = ["## Bloc 5 — why"]
    for sub in cfg.get("subsections", []):
        if sub.get("heading"):
            parts.append("### " + sub["heading"])
        parts.append(sub["body"])
    return SEP.join(parts)


def _render_header(cfg: dict) -> str:
    lines = ["# " + cfg["title"]]
    meta: list[str] = []
    if cfg.get("date"):
        meta.append(f"**Date** : {cfg['date']}")
    if cfg.get("plan"):
        meta.append(f"**Plan** : {cfg['plan']}")
    if cfg.get("status"):
        meta.append(f"**Statut** : {cfg['status']}")
    if meta:
        lines.append("\n".join(meta))
    if cfg.get("decision_line"):
        lines.append(cfg["decision_line"])
    return SEP.join(lines)


def _render_trailer(cfg: dict) -> list[str]:
    parts: list[str] = []
    if cfg.get("next_action"):
        parts.append("## Prochaine action\n\n" + cfg["next_action"])
    if cfg.get("artefacts"):
        bullets = "\n".join("- " + a for a in cfg["artefacts"])
        parts.append("## Artefacts\n\n" + bullets)
    return parts


def render_markdown(cfg: dict) -> str:
    parts = [
        _render_header(cfg),
        _render_bloc1(cfg["bloc1_identity"]),
        _render_bloc2(cfg["bloc2_metrics"]),
        _render_bloc3(cfg["bloc3_structural"]),
        _render_bloc4(cfg["bloc4_decision"]),
        _render_bloc5(cfg["bloc5_why"]),
    ]
    parts.extend(_render_trailer(cfg))
    return SEP.join(parts) + "\n"


def build_json(cfg: dict) -> dict:
    """Structured view of the verdict, 1-to-1 with config (audit-friendly)."""
    return {
        "title": cfg["title"],
        "date": cfg.get("date"),
        "plan": cfg.get("plan"),
        "status": cfg.get("status"),
        "decision_line": cfg.get("decision_line"),
        "bloc1_identity": cfg["bloc1_identity"],
        "bloc2_metrics": cfg["bloc2_metrics"],
        "bloc3_structural": cfg["bloc3_structural"],
        "bloc4_decision": cfg["bloc4_decision"],
        "bloc5_why": cfg["bloc5_why"],
        "next_action": cfg.get("next_action"),
        "artefacts": cfg.get("artefacts"),
    }


def load_config(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("config", type=Path, help="YAML config (§18.3 5-blocs)")
    ap.add_argument("--trades-parquet", type=Path, default=None,
                    help="(réservé, scaffold pour auto-métriques bloc 2)")
    ap.add_argument("--out-md", type=Path, default=None,
                    help="Chemin markdown (défaut stdout)")
    ap.add_argument("--out-json", type=Path, default=None,
                    help="Chemin JSON structuré (défaut skip)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    md = render_markdown(cfg)
    if args.out_md:
        args.out_md.write_text(md)
    else:
        sys.stdout.write(md)

    if args.out_json:
        args.out_json.write_text(json.dumps(build_json(cfg), indent=2,
                                           ensure_ascii=False) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

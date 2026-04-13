# Phase 6 — FULL mode (expansion contrôlée)

**Date :** 2026-04-11  
**Statut :** règles produit + ordre d’attaque — **pas** d’activation globale dans le code sur ce passage.

---

## PREUVE CODE

Références code existantes :

- **Allowlists / denylist** : `backend/engines/risk_engine.py` (`AGGRESSIVE_ALLOWLIST`, denylist, optional `paper_wave1`).
- **Playbooks chargés** : `PlaybookLoader` + `playbooks.yml` (11 core) + `aplus_setups.yml` (2) → **13** actifs loader — voir `PHASE_2_PLAYBOOK_INVENTORY.md`.
- **Wave 2 plan** : `backend/docs/WAVE2_PLAN_FVG_SESSIONOPEN_NEWSFADE.md`.

---

## PREUVE RUN

Aucun nouveau backtest dans cette session. Dernière preuve quantitative agrégée : `PHASE_5_SAFE_MODE_PARQUET_PROOF.md` (nov 2025).

---

## PREUVE TEST

N/A.

---

## Principes FULL (cahier utilisateur)

1. **Jamais** activer tous les playbooks YAML d’un coup.
2. **Ordre suggéré Wave 2** : `FVG_Fill_Scalp`, `Session_Open_Scalp`, `News_Fade` — puis ORB / VWAP / SMT selon labs dédiés.
3. Pour chaque ajout : **un** lab + métriques funnel (Phase 4) + parquet (Phase 5) avant élargissement allowlist.
4. Playbooks **BLOCKED_BY_POLICY** aujourd’hui (London, BOS, A+) : réintégration = **retirer DENYLIST** ou **allowlist explicite** + test de non-régression **NY_Open_Reversal**.

---

## ANALYSE

- L’inventaire **27** historique vs **13** actuels impose de **recharger** des playbooks YAML avant d’atteindre « 15–20 » en FULL.
- Sur nov 2025, **LSS** et **TC-FVG** tirent beaucoup de volume mais **ΣR** très négatifs — l’expansion FULL doit être **mesurée**, pas seulement « plus de noms ».

---

## DÉCISION

| Élément | Verdict |
|---------|---------|
| Patch massif allowlist | **ROLLBACK si tenté sans lab** |
| Stratégie d’expansion | **KEEP** (vagues + preuves) |

---

## NEXT STEP

- Restaurer / ajouter des playbooks dans YAML (Phase 2 suite) **ou** accepter un panier FULL à **13** max tant que le YAML n’est pas étendu.
- Phase 7 : scoring / placeholders mesurables (ATR, structure, volume).
- Phase 8 : slippage, fees, caps — `backtest/costs.py`, `ExecutionEngine`.

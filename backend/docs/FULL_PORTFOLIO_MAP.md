# FULL Portfolio Map (Repo-Driven)

- Schema: `FullPortfolioMapV0`
- Generated at (UTC): `2026-04-15T01:22:51+00:00`
- Git SHA: `59030d59aeee357116d853b1770a99f2a4754967`

## Regenerate
```bash
cd /home/dexter/dexterio1-main/backend
.venv/bin/python scripts/generate_full_portfolio_map.py
```

## Policy Runtime (AGGRESSIVE)

- Allowlist: News_Fade, Session_Open_Scalp, NY_Open_Reversal, Morning_Trap_Reversal, Liquidity_Sweep_Scalp, FVG_Fill_Scalp, IFVG_Flip_5m_Bull, IFVG_Flip_5m_Bear
- Denylist: London_Sweep_NY_Continuation, BOS_Momentum_Scalp, Power_Hour_Expansion, DAY_Aplus_1_Liquidity_Sweep_OB_Retest, Lunch_Range_Scalp, SCALP_Aplus_1_Mini_FVG_Retest_NY_Open, Trend_Continuation_FVG_Retest

## Families (Rollup)

| Family | Total | Status Breakdown |
|---|---:|---|
| A+ branchés | 2 | blocked by deny=2 |
| A+ transcripts research-only | 4 | research-only=4 |
| FVG / IFVG | 4 | FULL runnable=1, FULL runnable via --playbooks-yaml=2, blocked by deny=1 |
| NY / reversals | 2 | FULL runnable=1, blocked by deny=1 |
| News Fade | 1 | FULL runnable=1 |
| Other / uncategorized | 4 | FULL runnable (quarantined / needs revalidation)=1, blocked by deny=3 |
| Session / opening range | 1 | FULL runnable=1 |
| sweeps / liquidity | 1 | FULL runnable (quarantined / needs revalidation)=1 |

## Playbooks / Candidates (Detail)

| Name | Family | Source | Loader | Policy | Quarantine | Status | Campaign YAMLs | Evidence (results/) | TF Suspicion |
|---|---|---|---|---|---|---|---|---|---|
| DAY_Aplus_1_Liquidity_Sweep_OB_Retest | A+ branchés | APLUS_BRANCHED | yes | denylist | no | blocked by deny |  |  | high |
| SCALP_Aplus_1_Mini_FVG_Retest_NY_Open | A+ branchés | APLUS_BRANCHED | yes | denylist | yes | blocked by deny |  |  | high |
| Aplus_01_MarketOpen_Sweep_IFVG_Breaker | A+ transcripts research-only | APLUS_TRANSCRIPTS | no | n/a | no | research-only |  |  | high |
| Aplus_02_PremarketSweep_5mConfirm_5mContinuation_EntryConfluence | A+ transcripts research-only | APLUS_TRANSCRIPTS | no | n/a | no | research-only |  |  | high |
| Aplus_03_IFVG_Flip_from_FVG_Invalidation | A+ transcripts research-only | APLUS_TRANSCRIPTS | no | n/a | no | research-only |  |  | high |
| Aplus_04_HTF_Bias_15m_Sweep_BOS_EntryConfluence | A+ transcripts research-only | APLUS_TRANSCRIPTS | no | n/a | no | research-only |  |  | high |
| FVG_Fill_Scalp | FVG / IFVG | CORE | yes | allowlist | no | FULL runnable | knowledge/campaigns/campaign_wf_core3_fvg_only.yml, knowledge/campaigns/campaign_wf_core3_jun_nov2025.yml, knowledge/campaigns/campaign_wf_core3_tune_stricter_grades.yml | wf_core3_fvg_only/(WF), wf_core3_fvg_only/wf_s0_test@b8ac81f, wf_core3_fvg_only/wf_s1_test@b8ac81f, wf_core3_oos_jun_nov2025/(WF), wf_core3_oos_jun_nov2025/wf_s0_test@b8e7bcf, wf_core3_oos_jun_nov2025/wf_s1_test@b8e7bcf, wf_core3_tune_stricter_grades/(WF), wf_core3_tune_stricter_grades/wf_s0_test@2ea7add, wf_core3_tune_stricter_grades/wf_s1_test@2ea7add | medium |
| IFVG_Flip_5m_Bear | FVG / IFVG | CAMPAIGN_ONLY | no | allowlist | no | FULL runnable via --playbooks-yaml | knowledge/campaigns/campaign_ifvg_5m_oos_jun_nov2025.yml, knowledge/campaigns/campaign_smoke_ifvg_5m.yml | data_coverage_contract_probe/coverage_enddate_probe@4e7246a, debug_sep30_tight/debug_sep30_tight@c3eb1d6, ifvg_oos_jun_nov2025/(WF), ifvg_oos_jun_nov2025/wf_s0_test@c3eb1d6, ifvg_oos_jun_nov2025/wf_s1_test@c3eb1d6, ifvg_oos_jun_nov2025_postfix/wf_s0_test@4e7246a, ifvg_oos_jun_nov2025_postfix/wf_s1_test@4e7246a, ifvg_oos_jun_nov2025_postfix_covfix/wf_s0_test@ad8ba70, ifvg_oos_jun_nov2025_postfix_covfix/wf_s1_test@ad8ba70, ifvg_probe_sep29_oct02/ifvg_sep29_oct02@c3eb1d6, ifvg_probe_sep29_oct02_postfix/ifvg_sep29_oct02_postfix@4e7246a, smoke_ifvg_5m/smoke_ifvg_5m_day1@c3eb1d6, smoke_ifvg_5m/smoke_ifvg_5m_day1_v2@c3eb1d6, smoke_ifvg_5m/smoke_ifvg_5m_day1_v3@c3eb1d6 | low |
| IFVG_Flip_5m_Bull | FVG / IFVG | CAMPAIGN_ONLY | no | allowlist | no | FULL runnable via --playbooks-yaml | knowledge/campaigns/campaign_ifvg_5m_oos_jun_nov2025.yml, knowledge/campaigns/campaign_smoke_ifvg_5m.yml | data_coverage_contract_probe/coverage_enddate_probe@4e7246a, debug_sep30_tight/debug_sep30_tight@c3eb1d6, ifvg_oos_jun_nov2025/(WF), ifvg_oos_jun_nov2025/wf_s0_test@c3eb1d6, ifvg_oos_jun_nov2025/wf_s1_test@c3eb1d6, ifvg_oos_jun_nov2025_postfix/wf_s0_test@4e7246a, ifvg_oos_jun_nov2025_postfix/wf_s1_test@4e7246a, ifvg_oos_jun_nov2025_postfix_covfix/wf_s0_test@ad8ba70, ifvg_oos_jun_nov2025_postfix_covfix/wf_s1_test@ad8ba70, ifvg_probe_sep29_oct02/ifvg_sep29_oct02@c3eb1d6, ifvg_probe_sep29_oct02_postfix/ifvg_sep29_oct02_postfix@4e7246a, smoke_ifvg_5m/smoke_ifvg_5m_day1@c3eb1d6, smoke_ifvg_5m/smoke_ifvg_5m_day1_v2@c3eb1d6, smoke_ifvg_5m/smoke_ifvg_5m_day1_v3@c3eb1d6 | low |
| Trend_Continuation_FVG_Retest | FVG / IFVG | CORE | yes | denylist | yes | blocked by deny |  |  | medium |
| London_Sweep_NY_Continuation | NY / reversals | CORE | yes | denylist | no | blocked by deny |  |  | high |
| NY_Open_Reversal | NY / reversals | CORE | yes | allowlist | no | FULL runnable | knowledge/campaigns/campaign_wf_core3_jun_nov2025.yml, knowledge/campaigns/campaign_wf_core3_no_fvg.yml, knowledge/campaigns/campaign_wf_core3_ny_only.yml, knowledge/campaigns/campaign_wf_core3_tune_stricter_grades.yml | wf_core3_no_fvg/(WF), wf_core3_no_fvg/wf_s0_test@99a5780, wf_core3_no_fvg/wf_s1_test@99a5780, wf_core3_ny_only/(WF), wf_core3_ny_only/wf_s0_test@9716e2d, wf_core3_ny_only/wf_s1_test@9716e2d, wf_core3_oos_jun_nov2025/(WF), wf_core3_oos_jun_nov2025/wf_s0_test@b8e7bcf, wf_core3_oos_jun_nov2025/wf_s1_test@b8e7bcf, wf_core3_tune_stricter_grades/(WF), wf_core3_tune_stricter_grades/wf_s0_test@2ea7add, wf_core3_tune_stricter_grades/wf_s1_test@2ea7add | high |
| News_Fade | News Fade | CORE | yes | allowlist | no | FULL runnable |  |  | medium |
| BOS_Momentum_Scalp | Other / uncategorized | CORE | yes | denylist | no | blocked by deny |  |  | medium |
| Lunch_Range_Scalp | Other / uncategorized | CORE | yes | denylist | no | blocked by deny |  |  | medium |
| Morning_Trap_Reversal | Other / uncategorized | CORE | yes | allowlist | yes | FULL runnable (quarantined / needs revalidation) |  |  | medium |
| Power_Hour_Expansion | Other / uncategorized | CORE | yes | denylist | no | blocked by deny |  |  | medium |
| Session_Open_Scalp | Session / opening range | CORE | yes | allowlist | no | FULL runnable | knowledge/campaigns/campaign_wf_core3_jun_nov2025.yml, knowledge/campaigns/campaign_wf_core3_no_fvg.yml, knowledge/campaigns/campaign_wf_core3_tune_stricter_grades.yml | wf_core3_no_fvg/(WF), wf_core3_no_fvg/wf_s0_test@99a5780, wf_core3_no_fvg/wf_s1_test@99a5780, wf_core3_oos_jun_nov2025/(WF), wf_core3_oos_jun_nov2025/wf_s0_test@b8e7bcf, wf_core3_oos_jun_nov2025/wf_s1_test@b8e7bcf, wf_core3_tune_stricter_grades/(WF), wf_core3_tune_stricter_grades/wf_s0_test@2ea7add, wf_core3_tune_stricter_grades/wf_s1_test@2ea7add | medium |
| Liquidity_Sweep_Scalp | sweeps / liquidity | CORE | yes | allowlist | yes | FULL runnable (quarantined / needs revalidation) |  |  | medium |

## Notes
- policy_runtime is derived from engines/risk_engine.py list literals (no code execution).
- evidence_runs is derived from results/**/run_manifest.json playbooks_yaml linkage; runs without playbooks_yaml are ignored.
- APLUS_TRANSCRIPTS entries are keyed by transcript 'id' (not a runtime playbook_name).

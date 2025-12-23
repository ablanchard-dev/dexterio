# PATCH B: Allowlist/Denylist cohérents
# Fichier: /app/backend/engines/risk_engine.py
# Lignes 30-45

# PLAYBOOKS RÉELS dans playbooks.yml:
# - DAY_Aplus_1_Liquidity_Sweep_OB_Retest
# - SCALP_Aplus_1_Mini_FVG_Retest_NY_Open
# - News_Fade
# - Session_Open_Scalp
# - London_Sweep_NY_Retest
# - Morning_Trap_Reversal
# - NY_Open_Reversal

# REMPLACER:
AGGRESSIVE_ALLOWLIST = []
AGGRESSIVE_DENYLIST = [
    'Morning_Trap_Reversal',  # Mauvaise perf connue
]

SAFE_ALLOWLIST = [
    'SCALP_Aplus_1_Mini_FVG_Retest_NY_Open',
    'DAY_Aplus_1_Liquidity_Sweep_OB_Retest',
]

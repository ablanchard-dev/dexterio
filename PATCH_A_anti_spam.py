# PATCH A: Câbler anti-spam dans backtest engine
# Fichier: /app/backend/backtest/engine.py
# Ligne ~660-670 (avant place_order)

# AVANT (ligne existante):
# allowed, reason = self.risk_engine.is_setup_allowed(setup)
# if not allowed:
#     logger.debug(f"⚠️ Setup refusé: {reason}")
#     return

# AJOUTER APRÈS:
session_info = get_session_info(current_time)
current_session = session_info.get('name', 'unknown')
cooldown_ok, cooldown_reason = self.risk_engine.check_cooldown_and_session_limit(
    setup, current_time, current_session
)
if not cooldown_ok:
    playbook_name = setup.playbook_matches[0].playbook_name if setup.playbook_matches else "UNKNOWN"
    logger.info(f"⏸️ SKIP (anti-spam): {playbook_name} {setup.symbol} - {cooldown_reason} @ {current_time.strftime('%H:%M')}")
    return

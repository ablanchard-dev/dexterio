"""
Test de connectivité Interactive Brokers (TWS / Gateway) via ib_insync.
Les ordres bracket complets seront branchés progressivement sur ExecutionEngine.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def ibkr_connection_check(
    host: str,
    port: int,
    client_id: int,
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """
    Tente une connexion courte à TWS / IB Gateway.

    Returns:
        dict avec clés ok (bool), error (str optionnel), detail (str optionnel)
    """
    try:
        from ib_insync import IB  # type: ignore
    except ImportError:
        return {
            "ok": False,
            "error": "ib_insync_non_installé",
            "detail": "pip install -r requirements-ibkr.txt",
        }

    ib = IB()
    try:
        ib.connect(host, port, clientId=client_id, timeout=timeout)
        ib.disconnect()
        return {"ok": True, "host": host, "port": port, "client_id": client_id}
    except Exception as e:
        logger.warning("IBKR connect failed: %s", e)
        return {
            "ok": False,
            "error": type(e).__name__,
            "detail": str(e),
            "host": host,
            "port": port,
            "client_id": client_id,
        }

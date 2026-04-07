"""
Vérification X-API-KEY pour routes sensibles (backtests, trading).

Quand DEXTERIO_API_KEY est défini dans l'environnement, toute requête doit
envoyer le même secret en en-tête X-API-KEY. Comparaison résistante au timing
sur le hachage SHA-256 des deux chaînes.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException, status


def _constant_time_key_match(provided: str, expected: str) -> bool:
    """Compare deux secrets sans dépendre de longueurs identiques."""
    hp = hashlib.sha256(provided.encode("utf-8")).digest()
    he = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(hp, he)


def require_dexterio_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-KEY"),
) -> None:
    """
    Dépendance FastAPI : exige X-API-KEY si DEXTERIO_API_KEY est configuré.

    Mode dev : si DEXTERIO_API_KEY est absent ou vide après strip → pas d'exigence.
    Réponse unique 401 (message générique) si fourni invalide ou manquant en prod.
    """
    expected = (os.getenv("DEXTERIO_API_KEY") or "").strip()
    if not expected:
        return

    if not x_api_key or not x_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    if not _constant_time_key_match(x_api_key.strip(), expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

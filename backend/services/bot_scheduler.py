"""
Planification de la boucle paper/live : analyse + mise à jour des positions.
Évite de bloquer l’event loop FastAPI (travail synchrone dans un thread).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_running = False
_task: Optional[asyncio.Task] = None


def is_bot_running() -> bool:
    return _running


async def _loop_body(get_pipeline: Callable[[], Any], interval_sec: float) -> None:
    global _running
    while _running:
        try:
            pipeline = get_pipeline()
            await asyncio.to_thread(pipeline.execute_trading_loop)
            await asyncio.to_thread(pipeline.update_open_positions)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Erreur dans la boucle trading automatique")
        await asyncio.sleep(interval_sec)


async def start_bot(get_pipeline: Callable[[], Any], interval_sec: float) -> dict:
    global _running, _task
    if _task is not None and not _task.done():
        return {"status": "already_running", "message": "La boucle est déjà active"}
    _running = True
    _task = asyncio.create_task(_loop_body(get_pipeline, interval_sec))
    logger.info("Boucle trading démarrée (intervalle %.1fs)", interval_sec)
    return {
        "status": "started",
        "interval_sec": interval_sec,
        "message": "Boucle automatique démarrée (paper ou selon EXECUTION_BACKEND)",
    }


async def stop_bot() -> None:
    global _running, _task
    _running = False
    t = _task
    _task = None
    if t is not None:
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass
    logger.info("Boucle trading arrêtée")

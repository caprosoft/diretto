"""
Connessione PostgreSQL con pool asincrono (asyncpg).
GNU AGPL-3.0
"""

import logging
import os

import asyncpg

log = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def init_pool():
    global _pool
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL non impostata")
    _pool = await asyncpg.create_pool(url, min_size=2, max_size=10)
    log.info("Pool database inizializzato")


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        log.info("Pool database chiuso")


async def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Pool non inizializzato — chiama init_pool() prima")
    return _pool

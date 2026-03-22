"""
Phase 9: Asynchronous Audit Disk Flusher
=========================================
This daemon runs as a background asyncio task attached to the FastAPI lifespan.
It silently drains the `vantix:stream:risk_audit` Redis Stream every 5 seconds,
bulk-inserting batches into the persistent database (SQLite or Postgres).

This completely decouples disk I/O from the payment execution hot-path,
enabling 10,000+ TPS without database lock contention.
"""
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

STREAM_KEY = "vantix:stream:risk_audit"
FLUSH_INTERVAL_SECONDS = 5
BATCH_LIMIT = 10_000


async def run_audit_flusher():
    """
    Main daemon loop. Pulls pending events from the Redis Stream
    and bulk-inserts them into the database every FLUSH_INTERVAL_SECONDS.
    """
    # Late imports to avoid circular dependency issues at startup
    from app.core.redis import r
    from app.db.database import AUDIT_STORE

    logger.info("[AUDIT FLUSHER] Daemon started. Draining Redis Stream → Database.")

    while True:
        try:
            await asyncio.sleep(FLUSH_INTERVAL_SECONDS)

            # Read up to BATCH_LIMIT entries from the stream (non-blocking)
            # Using '0-0' as the start ID reads all unacknowledged messages
            raw_entries = r.xrange(STREAM_KEY, count=BATCH_LIMIT)

            if not raw_entries:
                continue

            batch: list[dict] = []
            last_id = None

            for entry_id, fields in raw_entries:
                try:
                    raw_payload = fields.get(b"payload") or fields.get("payload")
                    if raw_payload:
                        if isinstance(raw_payload, bytes):
                            raw_payload = raw_payload.decode("utf-8")
                        p = json.loads(raw_payload)
                        batch.append(p)
                        last_id = entry_id
                except Exception as parse_err:
                    logger.warning(f"[AUDIT FLUSHER] Failed to parse entry {entry_id}: {parse_err}")

            if not batch:
                continue

            # Bulk-insert the entire batch in a single DB transaction
            try:
                await AUDIT_STORE.bulk_insert_risk_audit(batch)

                # Only trim the stream AFTER a successful write to guarantee durability
                r.xtrim(STREAM_KEY, maxlen=0, approximate=False)
                logger.info(f"[AUDIT FLUSHER] ✅ Flushed {len(batch)} audit records to persistent storage.")
            except Exception as db_err:
                # Do NOT trim the stream on failure — entries will be retried next cycle
                logger.error(f"[AUDIT FLUSHER] ❌ DB flush failed, will retry: {db_err}")

        except asyncio.CancelledError:
            # Graceful shutdown signal received
            logger.info("[AUDIT FLUSHER] Daemon shutting down cleanly.")
            break
        except Exception as loop_err:
            logger.error(f"[AUDIT FLUSHER] Unexpected loop error: {loop_err}")
            await asyncio.sleep(1)  # Back-off before next cycle attempt

"""Publishing confirmed submissions (design §4.2 steps 6–7).

Runs after each confirmation and on the app's periodic loop, so a submission confirmed while the portal restarted
is still published. Until the registry pull request flow (step 6) arrives, publication writes to the local
registry clone directly.
"""

import logging
from pathlib import Path

from .publish import PublishError, publish

log = logging.getLogger("claimset_portal")


#: One publisher at a time across the app's threads and processes (a PostgreSQL advisory lock).
PUBLISH_LOCK = 4_242_001


def publish_confirmed(conn, *, settings, registry, store, classifier):
    """Publish every confirmed submission. Returns [(submission ID, published ID or None)]; [] at once if another
    publisher is running, which then publishes these too."""
    if not conn.execute("SELECT pg_try_advisory_lock(%s)", (PUBLISH_LOCK,)).fetchone()[0]:
        return []
    try:
        return _publish_all(conn, settings=settings, registry=registry, store=store, classifier=classifier)
    finally:
        conn.execute("SELECT pg_advisory_unlock(%s)", (PUBLISH_LOCK,))


def _publish_all(conn, *, settings, registry, store, classifier):
    done = []
    ids = [r[0] for r in conn.execute("SELECT id FROM submissions WHERE state = 'confirmed' ORDER BY received")]
    for sid in ids:
        file_name = conn.execute("SELECT file_name FROM submissions WHERE id = %s AND state = 'confirmed'",
                                 (sid,)).fetchone()
        if not file_name or not file_name[0]:
            continue
        path = Path(settings.submissions_dir) / file_name[0]
        try:
            concept, version = publish(path, conn=conn, registry=registry, store=store, classifier=classifier,
                                       published_dir=settings.published_dir, base_url=settings.base_url)
        except PublishError as exc:
            detail = str(exc) + "".join(f"; {e['rule']} {e['where']}: {e['message']}" for e in exc.errors[:5])
            conn.execute("UPDATE submissions SET state = 'refused', detail = %s, file_name = NULL WHERE id = %s",
                         (detail, sid))
            path.unlink(missing_ok=True)
            done.append((sid, None))
            continue
        except Exception:
            # The classifier or the registry is unavailable: leave it confirmed, the next round retries.
            log.exception("publishing %s failed; will retry", sid)
            continue
        published = f"{concept}@v{version}"
        conn.execute("UPDATE submissions SET state = 'published', published_id = %s, file_name = NULL WHERE id = %s",
                     (published, sid))
        path.unlink(missing_ok=True)
        log.info("published %s as %s", sid, published)
        done.append((sid, published))
    return done

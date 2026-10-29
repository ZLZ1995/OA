"""Never remove physical files before the database transaction commits."""
import logging
from pathlib import Path
from sqlalchemy import event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def after_commit_delete(db: Session, paths):
    db.info.setdefault("committed_file_cleanup", set()).update(str(p) for p in paths)


@event.listens_for(Session, "after_commit")
def remove_committed_files(db):
    for path in db.info.pop("committed_file_cleanup", set()):
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            logger.exception("Committed file cleanup failed: %s", path)


@event.listens_for(Session, "after_rollback")
def cancel_cleanup(db):
    db.info.pop("committed_file_cleanup", None)

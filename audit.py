"""Append-only CSV audit logging for API requests.

Each row records when a research job was started, which user requested it
(the redacted product idea), and the Celery task id so activity can be
traced. Only redacted data should be passed to :func:`log_request`.
"""

import csv
import datetime
from pathlib import Path

AUDIT_PATH = Path(__file__).resolve().parent / "audit.csv"

_HEADER = ["timestamp", "user_id", "product_idea", "task_id"]


def log_request(user_id: str, product: str, task_id: str) -> None:
    """Append one request to the audit log.

    Args:
        user_id: Identifier of the caller (already redacted if needed).
        product: The product idea (pass it through :func:`redact_pii` first).
        task_id: The Celery task id returned to the caller.
    """
    with open(AUDIT_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if AUDIT_PATH.stat().st_size == 0:
            writer.writerow(_HEADER)
        writer.writerow(
            [
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
                user_id,
                product,
                task_id,
            ]
        )
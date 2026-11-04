"""The one write to courier serve: queue a message the way ``courier send --human`` does."""

import uuid
from typing import Any

from herdr_courier.client import LostContact, Refused, Unavailable, request

# courier send's own limit: longer than courier serve's worst case for resolving a target.
SEND_TIMEOUT = 30.0


def send(target: str, text: str, source: str, human: bool = True) -> dict[str, Any]:
    """Queue ``text`` for ``target``; the result is queued, refused or uncertain."""
    body = {
        "target": target,
        "text": text,
        "source": source,
        "human": human,
        # Lets the retry after a lost reply find the first request instead of queuing twice.
        "client_id": uuid.uuid4().hex,
    }
    try:
        try:
            item = request("POST", "send", body, timeout=SEND_TIMEOUT)["item"]
        except LostContact:
            item = request("POST", "send", body, timeout=SEND_TIMEOUT)["item"]
    except LostContact as exc:
        detail = f"{exc}; it may have been queued, check courier status"
        return {"result": "uncertain", "detail": detail, "id": None}
    except Unavailable as exc:
        return {"result": "refused", "detail": f"courier serve not running ({exc})", "id": None}
    except Refused as exc:
        return {"result": "refused", "detail": str(exc), "id": None}
    return {
        "result": "queued",
        "detail": f"queued {item['id']} for {item['target']} ({item['pane_id']})",
        "id": item["id"],
    }

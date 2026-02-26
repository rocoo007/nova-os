from __future__ import annotations
import secrets
import time
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PendingAction:
    cmd: str
    created_at: float

# token -> PendingAction
_pending: Dict[str, PendingAction] = {}

TTL_SEC = 120  # token expires in 2 minutes

def create_token(cmd: str) -> str:
    token = secrets.token_hex(3)  # short token like "a1b2c3"
    _pending[token] = PendingAction(cmd=cmd, created_at=time.time())
    return token

def pop_if_valid(token: str) -> Optional[str]:
    item = _pending.pop(token, None)
    if not item:
        return None
    if (time.time() - item.created_at) > TTL_SEC:
        return None
    return item.cmd

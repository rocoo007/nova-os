from fastapi import FastAPI
from pydantic import BaseModel
import json
from pathlib import Path

from backend.tools.shell_tool import run_shell, ALLOWED_PREFIXES
from backend.state.confirm_state import create_token, pop_if_valid

app = FastAPI(title="NOVA OS")

PROFILE_PATH = Path("memory/profile.json")


def load_profile() -> dict:
    if PROFILE_PATH.exists():
        return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    return {"assistant_name": "NOVA", "user_name": "User", "preferences": {}}


class ChatIn(BaseModel):
    message: str


class ShellIn(BaseModel):
    cmd: str
    timeout_sec: int = 10


@app.get("/")
def root():
    return {
        "name": "NOVA OS",
        "routes": ["/health", "/chat", "/docs", "/tools/shell/run", "/tools/shell/allowed"],
    }


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/tools/shell/allowed")
def shell_allowed():
    return {"allowed_prefixes": ALLOWED_PREFIXES}


@app.post("/tools/shell/run")
def shell_run(payload: ShellIn):
    r = run_shell(payload.cmd, timeout_sec=payload.timeout_sec)
    return {
        "ok": r.ok,
        "blocked": r.blocked,
        "needs_confirm": r.needs_confirm,
        "reason": r.reason,
        "stdout": r.stdout,
        "stderr": r.stderr,
        "returncode": r.returncode,
    }


@app.post("/chat")
def chat(payload: ChatIn):
    prof = load_profile()
    assistant = prof.get("assistant_name", "NOVA")

    msg = payload.message.strip()
    low = msg.lower()

    # Confirm flow:
    # "confirm <token>"
    if low.startswith("confirm "):
        token = msg.split(" ", 1)[1].strip()
        cmd = pop_if_valid(token)
        if not cmd:
            return {"reply": f"{assistant}: ❌ Invalid/expired token. Please retry the command."}

        # Execute the saved command (still goes through safety deny list)
        r = run_shell(cmd, timeout_sec=10)
        if r.blocked:
            return {"reply": f"{assistant}: ⚠️ Blocked -> {r.reason}"}
        out = r.stdout if r.stdout else r.stderr
        return {"reply": f"{assistant}: ✅ Confirmed & executed.\n{out}"}

    # Tool trigger:
    # "cmd: <command>" or "run: <command>"
    if low.startswith("cmd:") or low.startswith("run:"):
        cmd = msg.split(":", 1)[1].strip()
        r = run_shell(cmd, timeout_sec=10)

        if r.blocked:
            return {"reply": f"{assistant}: ⚠️ Blocked -> {r.reason}"}

        if r.needs_confirm:
            token = create_token(cmd)
            return {
                "reply": f"{assistant}: ⚠️ This action needs confirmation.\nType: confirm {token}"
            }

        out = r.stdout if r.stdout else r.stderr
        return {"reply": f"{assistant}: ✅ Done (code {r.returncode})\n{out}"}

    return {"reply": f"{assistant}: I heard -> {msg}"}

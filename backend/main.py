from fastapi import FastAPI
from pydantic import BaseModel
import json
from pathlib import Path

from backend.tools.shell_tool import run_shell, ALLOWED_PREFIXES
from backend.state.confirm_state import create_token, pop_if_valid

app = FastAPI(title="NOVA OS")

PROFILE_PATH = Path("memory/profile.json")



def plan_to_cmd(user_text: str) -> str | None:
    """
    Ultra-simple MVP planner (no LLM yet):
    maps common intents -> safe shell commands.
    """
    t = user_text.strip().lower()

    # file/system
    if any(x in t for x in ["where am i", "current folder", "current directory", "pwd", "kothay achi", "folder kothay"]):
        return "pwd"
    if any(x in t for x in ["list files", "show files", "files dekhao", "ls", "folder er file", "ki ki ache"]):
        return "ls"
    if any(x in t for x in ["who am i", "user", "ami ke", "whoami"]):
        return "whoami"

    # git
    if any(x in t for x in ["git status", "status dekhao", "repo status", "working tree"]):
        return "git status"
    if any(x in t for x in ["git log", "commit history", "log dekhao"]):
        return "git log --oneline -5"

    # dangerous (confirm-gated)
    if any(x in t for x in ["reset repo", "hard reset", "git reset"]):
        return "git reset --hard"
    if any(x in t for x in ["clean repo", "git clean", "remove untracked"]):
        return "git clean -fd"

    return None


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

    # Confirm flow: "confirm <token>"
    if low.startswith("confirm "):
        token = msg.split(" ", 1)[1].strip()
        cmd = pop_if_valid(token)
        if not cmd:
            return {"reply": f"{assistant}: ❌ Invalid/expired token. Please retry the command."}

        r = run_shell(cmd, timeout_sec=10)
        if r.blocked:
            return {"reply": f"{assistant}: ⚠️ Blocked -> {r.reason}"}
        out = r.stdout if r.stdout else r.stderr
        return {"reply": f"{assistant}: ✅ Confirmed & executed.
{out}"}

    # Explicit tool trigger: "cmd:" / "run:"
    if low.startswith("cmd:") or low.startswith("run:"):
        cmd = msg.split(":", 1)[1].strip()
        r = run_shell(cmd, timeout_sec=10)

        if r.blocked:
            return {"reply": f"{assistant}: ⚠️ Blocked -> {r.reason}"}

        if r.needs_confirm:
            token = create_token(cmd)
            return {"reply": f"{assistant}: ⚠️ This action needs confirmation.
Type: confirm {token}"}

        out = r.stdout if r.stdout else r.stderr
        return {"reply": f"{assistant}: ✅ Done (code {r.returncode})
{out}"}

    # ✅ Planner mode (no cmd needed)
    planned = plan_to_cmd(msg)
    if planned:
        r = run_shell(planned, timeout_sec=10)

        if r.blocked:
            return {"reply": f"{assistant}: ⚠️ Blocked -> {r.reason}"}

        if r.needs_confirm:
            token = create_token(planned)
            return {"reply": f"{assistant}: ⚠️ This action needs confirmation.
Type: confirm {token}"}

        out = r.stdout if r.stdout else r.stderr
        return {"reply": f"{assistant}: ✅ Done
{out}"}

    # default chat
    return {"reply": f"{assistant}: I heard -> {msg}"}


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

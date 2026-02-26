from fastapi import FastAPI
from pydantic import BaseModel


from backend.tools.shell_tool import run_shell, ALLOWED_PREFIXES
app = FastAPI(title="NOVA OS")

class ChatIn(BaseModel):
    message: str

class ShellIn(BaseModel):
    cmd: str
    timeout_sec: int = 10


    message: str

@app.get("/")
def root():
    return {
        "name": "NOVA OS",
        "routes": ["/health", "/chat", "/docs"]
    }

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/chat")
def chat(payload: ChatIn):
    msg = payload.message.strip()

    # MVP tool trigger:
    # "cmd: <command>" or "run: <command>"
    low = msg.lower()
    if low.startswith("cmd:") or low.startswith("run:"):
        cmd = msg.split(":", 1)[1].strip()
        r = run_shell(cmd, timeout_sec=10)
        if r.blocked:
            return {"reply": f"NOVA: ⚠️ I blocked that command. Reason: {r.reason}"}
        out = r.stdout if r.stdout else r.stderr
        return {"reply": f"NOVA: ✅ Command done (code {r.returncode}). Output:
{out}"}

    return {"reply": f"NOVA: I heard -> {msg}"}
@app.get("/tools/shell/allowed")
def shell_allowed():
    return {"allowed_prefixes": ALLOWED_PREFIXES}

@app.post("/tools/shell/run")
def shell_run(payload: ShellIn):
    r = run_shell(payload.cmd, timeout_sec=payload.timeout_sec)
    return {
        "ok": r.ok,
        "blocked": r.blocked,
        "reason": r.reason,
        "stdout": r.stdout,
        "stderr": r.stderr,
        "returncode": r.returncode,
    }

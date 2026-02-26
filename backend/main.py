from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="NOVA OS")

class ChatIn(BaseModel):
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
    return {"reply": f"NOVA: I heard -> {payload.message}"}
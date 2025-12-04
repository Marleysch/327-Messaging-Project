import os
import json
import time
import asyncio
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel
import httpx

NODE_ID = os.environ.get("NODE_ID", "1")
PEERS = [p.strip() for p in os.environ.get("PEERS", "").split(",") if p.strip()]
WAL = Path(f"./wal_{NODE_ID}.log")

app = FastAPI()

STORE = {}
STAGED = {}
LOCKS = {}
TX = {}


def log_write(data):
    with WAL.open("a") as f:
        f.write(json.dumps({"ts": time.time(), **data}) + "\n")


class TxStart(BaseModel):
    tx_id: str
    key: str
    value: str


class Prepare(BaseModel):
    tx_id: str
    key: str
    value: str


@app.post("/prepare")
async def prepare(req: Prepare):
    tx_id = req.tx_id
    key = req.key

    if key in LOCKS and LOCKS[key] != tx_id:
        TX[tx_id] = "ABORTED"
        log_write({"prep": "NO", "tx": tx_id})
        return {"vote": "NO", "node": NODE_ID}

    LOCKS[key] = tx_id
    STAGED[tx_id] = {"key": key, "value": req.value}
    TX[tx_id] = "PREPARED"
    log_write({"prep": "YES", "tx": tx_id})
    return {"vote": "YES", "node": NODE_ID}


@app.post("/commit")
async def commit(req: Prepare):
    tx_id = req.tx_id
    if tx_id in STAGED:
        key = STAGED[tx_id]["key"]
        STORE[key] = STAGED[tx_id]["value"]
        LOCKS.pop(key, None)
        STAGED.pop(tx_id, None)

    TX[tx_id] = "COMMITTED"
    log_write({"commit": tx_id})
    return {"ok": True, "node": NODE_ID}


@app.post("/abort")
async def abort(req: Prepare):
    tx_id = req.tx_id
    if tx_id in STAGED:
        key = STAGED[tx_id]["key"]
        LOCKS.pop(key, None)
        STAGED.pop(tx_id, None)

    TX[tx_id] = "ABORTED"
    log_write({"abort": tx_id})
    return {"ok": True, "node": NODE_ID}


@app.get("/kv/{key}")
def get_value(key: str):
    return {"key": key, "value": STORE.get(key)}


@app.get("/state")
def get_state():
    return {
        "node": NODE_ID,
        "store": STORE,
        "locks": LOCKS,
        "staged": STAGED,
        "tx": TX,
        "peers": PEERS
    }


@app.post("/start")
async def start_tx(req: TxStart):

    tx_id = req.tx_id
    TX[tx_id] = "STARTED"
    log_write({"start": tx_id})

    votes = {}
    all_yes = True

    async with httpx.AsyncClient(timeout=3.0) as client:
        results = await asyncio.gather(
            *[client.post(f"{p}/prepare", json=req.model_dump()) for p in PEERS],
            return_exceptions=True
        )

    for peer, r in zip(PEERS, results):
        if isinstance(r, Exception):
            votes[peer] = "NO"
            all_yes = False
        else:
            info = r.json()
            votes[info["node"]] = info["vote"]
            if info["vote"] != "YES":
                all_yes = False

    decision = "commit" if all_yes else "abort"
    log_write({"decision": decision, "tx": tx_id})

    endpoint = "/commit" if decision == "commit" else "/abort"
    async with httpx.AsyncClient(timeout=3.0) as client:
        await asyncio.gather(
            *[client.post(f"{p}{endpoint}", json={"tx_id": tx_id, "key": req.key, "value": req.value}) for p in PEERS],
            return_exceptions=True
        )

    if decision == "commit":
        STORE[req.key] = req.value

    TX[tx_id] = decision.upper()
    return {"tx": tx_id, "decision": decision, "votes": votes}

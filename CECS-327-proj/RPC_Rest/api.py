from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import socket
import json
import zmq
import time
from typing import Dict, Any
from IPC.transaction_manager import TransactionManager

app = FastAPI(title="Messaging Service API")

# One TransactionManager per node / process (GLOBAL SINGLETON)
tx_manager = TransactionManager(node_id="api-node")


# -----------------------------
# Message models
# -----------------------------
class Message(BaseModel):
    sender: str
    content: str


class TxBeginResponse(BaseModel):
    tx_id: str


class TxWriteRequest(BaseModel):
    key: str
    value: str


class TxReadResponse(BaseModel):
    key: str
    value: str | None


class ReservationRequest(BaseModel):
    station_id: str
    vehicle_id: str


# temp storage
messages_store = []


# -----------------------------
# API Endpoint 1 - POST message
# -----------------------------
@app.post("/send_message")
async def post_message(msg: Message):
    """
    Store a message locally, forward it to the TCP server,
    and publish a ZMQ update.
    """
    message = {
        "sender": msg.sender,
        "content": msg.content,
        "timestamp": datetime.now().isoformat(),
    }

    messages_store.append(message)

    tcp_connection(message)  # forward to TCP server
    publish_update(message)  # publish to subscribers

    return {
        "status": "Message stored & forwarded",
        "total_messages": len(messages_store),
    }


# -----------------------------
# API Endpoint 2 - GET messages
# -----------------------------
@app.get("/get_messages")
async def get_messages():
    return {"messages": messages_store}


# -----------------------------
# TCP helper
# -----------------------------
def tcp_connection(message: dict, host: str = "127.0.0.1", port: int = 7896):
    """
    Helper function to forward messages from FastAPI to TCP server.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        payload = json.dumps(message).encode("utf-8")
        s.sendall(payload)
        response = s.recv(1024).decode("utf-8")
        print(f"[TCP RESPONSE] {response}")


# -----------------------------
# ZMQ Pub/Sub helper
# -----------------------------
def publish_update(message: dict):
    """
    Helper function to connect pub/sub system to API.
    Publishes 'new_messages' events.
    """
    try:
        context = zmq.Context()
        pub_socket = context.socket(zmq.PUB)
        pub_socket.connect("tcp://127.0.0.1:5556")  # connect to pub server
        time.sleep(0.1)  # small delay so subscriber can connect
        pub_socket.send_string(f"new_messages {json.dumps(message)}")
        pub_socket.close()
        context.term()
        print(f"Published new message event for {message['sender']}")
    except Exception as e:
        print(f"Failed to publish update: {e}")


# -----------------------------
# Transactional API
# -----------------------------
@app.post("/transactions/begin", response_model=TxBeginResponse)
def begin_transaction():
    """
    Begin a new transaction.
    """
    tx_id = tx_manager.begin()
    print(f"[TX] BEGIN {tx_id}")
    return TxBeginResponse(tx_id=tx_id)


@app.post("/transactions/{tx_id}/write")
def transactional_write(tx_id: str, body: TxWriteRequest):
    """
    Transactional write(key, value) under strict 2PL.
    """
    try:
        print(f"[TX] WRITE {tx_id} key={body.key} value={body.value}")
        tx_manager.write(tx_id, body.key, body.value)
        return {"status": "ok"}
    except Exception as e:
        print(f"[TX] WRITE ERROR for {tx_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/transactions/{tx_id}/read", response_model=TxReadResponse)
def transactional_read(tx_id: str, key: str):
    """
    Transactional read(key) that obeys locks and read-your-own-writes.
    """
    try:
        print(f"[TX] READ {tx_id} key={key}")
        value = tx_manager.read(tx_id, key)
        return TxReadResponse(key=key, value=value)
    except Exception as e:
        print(f"[TX] READ ERROR for {tx_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/transactions/{tx_id}/commit")
def commit_transaction(tx_id: str):
    """
    Commit a transaction. Applies all its buffered writes atomically.
    """
    try:
        print(f"[TX] COMMIT {tx_id}")
        ok = tx_manager.commit(tx_id)
        if not ok:
            print(f"[TX] COMMIT ABORTED {tx_id}")
            raise HTTPException(status_code=409, detail="Transaction was aborted")
        return {"status": "committed"}
    except Exception as e:
        print(f"[TX] COMMIT ERROR for {tx_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/transactions/{tx_id}/abort")
def abort_transaction(tx_id: str):
    """
    Abort a transaction and roll back any changes.
    """
    print(f"[TX] ABORT {tx_id}")
    tx_manager.abort(tx_id)
    return {"status": "aborted"}


# -----------------------------
# Debug endpoint: inspect store
# -----------------------------
@app.get("/debug/store")
def debug_store() -> Dict[str, Any]:
    """
    Return the current committed key-value store.
    ONLY for debugging / testing.
    """
    store = tx_manager.dump_store()
    print(f"[DEBUG] STORE {store}")
    return store


# -----------------------------
# Reservation example: prevent double-booking
# -----------------------------
@app.post("/stations/reserve")
def reserve_station(body: ReservationRequest):
    """
    Example transactional operation:

    Reserve a charging station so that only one vehicle can hold it
    at a time, even under concurrent requests.
    """
    tx_id = tx_manager.begin()
    key = f"station:{body.station_id}"

    try:
        print(f"[RESERVE] BEGIN tx={tx_id} station={body.station_id} vehicle={body.vehicle_id}")

        # Check current reservation under shared lock
        current_holder = tx_manager.read(tx_id, key)
        if current_holder is not None:
            # Someone already has this station
            tx_manager.abort(tx_id)
            print(f"[RESERVE] CONFLICT station={body.station_id} held by {current_holder}")
            raise HTTPException(
                status_code=409,
                detail=f"Station {body.station_id} already reserved by {current_holder}",
            )

        # Reserve it under exclusive lock
        tx_manager.write(tx_id, key, body.vehicle_id)

        # Commit makes the reservation visible atomically
        tx_manager.commit(tx_id)

        # OPTIONAL: publish an event via existing ZeroMQ publisher
        publish_update(
            {
                "sender": "reservation-system",
                "content": f"{body.vehicle_id} reserved station {body.station_id}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        print(f"[RESERVE] SUCCESS tx={tx_id} station={body.station_id} vehicle={body.vehicle_id}")
        return {
            "status": "reserved",
            "station_id": body.station_id,
            "vehicle_id": body.vehicle_id,
            "tx_id": tx_id,
        }

    except HTTPException:
        # bubbled up error, already aborted
        raise
    except Exception as e:
        # Any error: abort and surface
        print(f"[RESERVE] ERROR tx={tx_id}: {e}")
        tx_manager.abort(tx_id)
        raise HTTPException(status_code=500, detail=f"Reservation failed: {e}")

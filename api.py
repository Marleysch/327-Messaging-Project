from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import socket
import json



app = FastAPI(title = "Messaging Service API")


# each message is comprised of a: thread and sender id, content, and timestamp 
# of when it was sent
class Message(BaseModel):
    thread_id: str
    sender_id: str
    content: str
    timestamp: datetime | None = None

# temp storage
MESSAGES: dict[str, list[Message]] = {}

# API Endpoint number 1 - POSTing
# Post purpose: used for submitting data to be processed by server
# in this case, it's TCP server 
@app.post("/messages")

# async funct to implement non blocking to handle multiple connections
async def post_message(msg: Message):
    msg.timestamp = msg.timestamp or datetime.now()
    MESSAGES.setdefault(msg.thread_id, []).append(msg)

    tcp_connection(msg.model_dump())
    return {
        "status": "ok",
        "thread_id": msg.thread_id,
        "count": len(MESSAGES[msg.thread_id])
    }

# API Endpoint number 2 - GETting
# Get purpose - retrieve data from server 
@app.get("/messages/{thread_id}")
async def get_thread(thread_id: str):
    return MESSAGES.get(thread_id, [])


def tcp_connection(message: dict, host = "127.0.0.1", port = 7896):
    # help funct to forward messages from fastapi to tcp server

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:       
            s.connect((host, port))
            payload = json.dumps(message, default = json_serial).encode("utf-8")
            s.sendall(payload)


    except Exception as e:
        print(f"TCP forwarding failed: {e}")

# helper funct to json serialize that aren't by default
def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError ("Type %s not serilizable" % type(obj))

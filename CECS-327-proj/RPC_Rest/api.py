from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import socket
import json
import zmq 
import time

app = FastAPI(title = "Messaging Service API")


# each message is comprised of a: sender and sender and it's content 
class Message(BaseModel):
    sender: str
    content: str

# temp storage
messages_store = []

# API Endpoint number 1 - POSTing
# Post purpose: used for submitting data to be processed by server
# in this case, it's TCP server 
@app.post("/send_message")

# async funct to implement non blocking to handle multiple connections
async def post_message(msg: Message):
    message = {
        "sender": msg.sender, 
        "content": msg.content, 
        "timestamp": datetime.now().isoformat()
               }
    
    messages_store.append(message)

    tcp_connection(message)  # fwd to the TCP server
    publish_update(message)

    return {
        "status": "Message stored & forwarded", 
        "total_messages": len(messages_store)
            }


# API Endpoint number 2 - GETting
# Get purpose - retrieve data from server 
@app.get("/get_messages")
async def get_messages():
    return {"messages": messages_store}


def tcp_connection(message: dict, host = "127.0.0.1", port = 7896):
    # help funct to forward messages from fastapi to tcp server

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:       
        s.connect((host, port))
        payload = json.dumps(message).encode("utf-8")
        s.sendall(payload)
        response = s.recv(1024).decode("utf-8")
        print(f"[TCP RESPONSE] {response}")

        


def publish_update(message: dict):
    # helper funct to connect pubsub sytem to api
    try:
        context = zmq.Context()
        pub_socket = context.socket(zmq.PUB)
        pub_socket.connect("tcp://127.0.0.1:5556")  # connect to pub server
        time.sleep(0.1)
        pub_socket.send_string(f"new_messages {json.dumps(message)}")
        pub_socket.close()
        context.term()
        print(f"Published new message event for {message['sender']}")
    except Exception as e:
        print(f"Failed to publish update: {e}")

import sys
import threading
import subprocess
from TCPServer import main as run_server
from pathlib import Path
from lamport_clock import LamportClock
import time
import httpx

class Node:
    def __init__(self, node_id, peers=None, host="127.0.0.1", base_port=7896):
        self.node_id = node_id
        self.host = host
        self.port = base_port + int(node_id)
        self.peers = peers or []
        self.clock = LamportClock()

    def start_server_thread(self):
        print(f"[Node {self.node_id}] Starting server on port {self.port}")
        process = threading.Thread(
            target=run_server, args=(self,), daemon=True
        )
        process.start()

    def send_test_message(self):
        
        BASE_DIR = Path(__file__).resolve().parent
        file_path = BASE_DIR / "TCPClient.py"

        message = input(f"[Node {self.node_id}] Enter message (blank to skip): ")
        message = f'{str(self.clock.now())}|{message}'

        tx_id = f"{self.node_id}-{int(time.time() * 1000)}"
        key = "messages"   # or "chat-log", or one key per channel
        value = message

        payload = {
            "tx_id": tx_id,
            "key": key,
            "value": value,
        }

        # This node is the leader → it calls /start on *itself*
        coord_url = "http://127.0.0.1:8000/start"  # adjust if your FastAPI runs elsewhere

        print(f"[Node {self.node_id}] Starting 2PC tx={tx_id}")
        try:
            r = httpx.post(coord_url, json=payload, timeout=5.0)
            r.raise_for_status()
            result = r.json()
        except Exception as e:
            print(f"[Node {self.node_id}] 2PC failed: {e}")
            return

        decision = result.get("decision")
        print(f"[Node {self.node_id}] 2PC decision for {tx_id}: {decision}, votes={result.get('votes')}")

        if decision != "commit":
            print(f"[Node {self.node_id}] Transaction aborted, not sending message.")
            return
        
        if not message.strip():
            return
        for peer in self.peers:
            host, port = peer.split(":")
            print(f"[Node {self.node_id}] Sending to {peer}")
            print(message,host,port)
            subprocess.run(
                ["python3", file_path, message, host, port], check=True
            )
            print(f"[Node {self.node_id}] Message sent to {peer}")
            self.clock.tick()
            print(f'LCtime: {self.clock.now()}')

    def run(self):
        self.start_server_thread()
        while True:
            self.send_test_message()


if __name__ == "__main__":
    node_id = sys.argv[1]
    peers = sys.argv[2:]
    node = Node(node_id, peers=peers)
    node.run()

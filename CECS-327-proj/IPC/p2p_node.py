import sys
import multiprocessing
import subprocess
from TCPServer import main as run_server


class Node:
    def __init__(self, node_id, peers=None, host="127.0.0.1", base_port=7896):
        self.node_id = node_id
        self.host = host
        self.port = base_port + int(node_id)
        self.peers = peers or []

    def start_server_thread(self):
        print(f"[Node {self.node_id}] Starting server on port {self.port}")
        process = multiprocessing.Process(
            target=run_server, args=(self.host, self.port), daemon=True
        )
        process.start()

    def send_test_message(self):
        message = input(f"[Node {self.node_id}] Enter message (blank to skip): ")
        if not message.strip():
            return
        for peer in self.peers:
            host, port = peer.split(":")
            print(f"[Node {self.node_id}] Sending to {peer}")
            subprocess.run(
                ["python3", "TCPClient.py", message, host, str(port)], check=True
            )
            print(f"[Node {self.node_id}] Message sent to {peer}")

    def run(self):
        self.start_server_thread()
        while True:
            self.send_test_message()


if __name__ == "__main__":
    node_id = sys.argv[1]
    peers = sys.argv[2:]
    node = Node(node_id, peers=peers)
    node.run()

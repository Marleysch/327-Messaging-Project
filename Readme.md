
# How to run?

### For each node in the group

Open 2 terminal windows in CECS-327-proj dir.

In terminal 1, run:

$env:NODE_ID="<node_id#>"
>> $env:COORD="1"
>> $env:PEERS="http://<IP of Peer>:<Port of Peer>,..." #For each peer in group
>> python -m uvicorn coord.two_phase_commit:app --host <IP> --port <port>

In terminal 2, run:

python IPC/p2p_node.py <node_id> <IP>:<port>


Messages will be sent and received in the terminal that ran IPC/p2p_node.py


## Testing zero_mq sub_client (pub/sub system)
- the api is also acting as a publisher via a helper funct.
- usage: python3 zero_mq/sub_client.py
- after doing this in terminal, use the same curl commands from before
- the client is subscribed to the port 8000, while the tcp server is bound to 7896
- any messages sent on 8000 will be returned via the pubsub system, whereas messages sent on the 7896 will only return on the TCP Server
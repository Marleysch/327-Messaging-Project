## HOW TO RUN
- run the tcp server first in terminal: python3 IPC/TCPServer.py

## Testing TCP CLIENT
- usage: python3 IPC/TCPClient.py <message> <host>
- not typing a host will still work, as the program will just use the default hose

## Testing API
- usage: uvicorn RPC_Rest.api:app --reload
- 2 optons: go to http://127.0.0.1:8000/docs to directly test endpoints (post and get)
- or use curl
- Usage: curl -X 'POST' \
  'http://127.0.0.1:8000/send_message' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "sender": "string",
  "content": "string"
}'

## Testing zero_mq sub_client (pub/sub system)
- the api is also acting as a publisher via a helper funct.
- usage: python3 zero_mq/sub_client.py
- after doing this in terminal, use the same curl commands from before
- the client is subscribed to the port 8000, while the tcp server is bound to 7896
- any messages sent on 8000 will be returned via the pubsub system, whereas messages sent on the 7896 will only return on the TCP Server

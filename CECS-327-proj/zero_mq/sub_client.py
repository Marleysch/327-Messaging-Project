import zmq
import json


# socket to talk to server
context = zmq.Context()

socket = context.socket(zmq.SUB)
socket.connect("tcp://127.0.0.1:5556")
socket.setsockopt_string(zmq.SUBSCRIBE, "new_messages")

while True:
    topic, payload = socket.recv_string().split(" ", 1)
    data = json.loads(payload)
    print(f"[NEW_MESSAGE] From {data['sender']}: {data['content']} (timestamp: {data['timestamp']})")









# just for getting the concept below:

# if len(sys.argv) > 1:
#     port = sys.argv0[1]
#     int(port)

# if len(sys.argv) > 2:
#     port1 = sys.argv[2]
#     int(port1)


# if len(sys.argv) > 2:
#     socket.connect("tcp://localhost:%s" % port1)

# example connection for zipcodes via topicfilter
# topicfilter = "10001"

# Process 5 updates
# total_value = 0
# for update_nbr in range (5):
#     string = socket.recv()
#     topic, messagedata = string.split()
#     total_value += int(messagedata)
#     print(topic, messagedata)

# print("Average messagedata value for topic '%s' was %dF" % (topicfilter, total_value / update_nbr))
      
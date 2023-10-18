import zmq
import json
import binascii

port = "5556"

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect ("tcp://127.0.0.1:%s" % port)


# Subscribe to privateData
# topicfilter = "privateData"
# socket.setsockopt(zmq.SUBSCRIBE, topicfilter)
socket.subscribe("")

while True:
    print("Starting ZMQ recv.")
    string = socket.recv_string()
    print("Got a message.")
    # ascii_string = byte_string.decode("ASCII")
    data = json.loads(string)
    # byte_string = binascii.unhexlify(data['data'])  
    # print(type(byte_string))
    print(data['data'])
      


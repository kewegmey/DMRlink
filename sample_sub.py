import zmq
import json

port = "5556"

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect ("tcp://localhost:%s" % port)


# Subscribe to privateData
# topicfilter = "privateData"
# socket.setsockopt(zmq.SUBSCRIBE, topicfilter)
socket.setsockopt(zmq.SUBSCRIBE,'')

while True:
    string = socket.recv_string()
    # byte_string = binascii.unhexlify(string)  
    # ascii_string = byte_string.decode("ASCII")
    data = json.loads(string)
    print(data['data'])
      


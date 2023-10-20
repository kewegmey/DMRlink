import zmq
import json
import binascii
import pprint

port = "5556"
TMS_PAYLOADS = [b"\x03", b"\x08", b"\x06"]

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect ("tcp://127.0.0.1:%s" % port)


# Subscribe to privateData
# topicfilter = "privateData"
# socket.setsockopt(zmq.SUBSCRIBE, topicfilter)
socket.subscribe("")

def tms_parser():
    pass

while True:
    #print("Starting ZMQ recv.")
    string = socket.recv_string()
    #print("Got a message.")
    data = json.loads(string)
    bdata = bytes.fromhex(data['data'])
    #print(data['data'])
    # Parse it - Some of these are already parsed in dmrlink and sent over here but we need to understand in the context of TMS
    parsed = {
        "packetType": bdata[0],
        "peerID": (bdata[1:5]),
        "IPSCSeq": bdata[5],
        "srcSub": (bdata[6:9]),
        "dstSub": (bdata[9:12]),
        "callType": bdata[12],
        "callControlInfo": (bdata[13:17]),
        "callInfo": bdata[17],
        "RTPCallCtrlSrc": bdata[18],
        "RTPType": bdata[19],
        "RTPSeq": bdata[20:22],
        "RTPTmstmp": bdata[22:26],
        "RTPSSID": bdata[26:30],
        "payloadType": bdata[30],
    }
    if parsed['payloadType'].to_bytes(length=1, byteorder='big') in TMS_PAYLOADS:
        parsed.update({
            "RSSIThreasholdParity": bdata[31],
            "lengthToFollow": (bdata[32:34]),
            "RSSIStatus": bdata[34],
            "slotTypeSync": bdata[35],
            "dataSize": (bdata[36:38]),
        })
        dataEnd = int.from_bytes(parsed['dataSize'], "big") // 8 + 38
        parsed['data'] = bdata[38:dataEnd]
        parsed['?'] = bdata[dataEnd:]
        #IPSCEndOffset = (int.from_bytes(parsed["lengthToFollow"], "big") * 2)-4
        #IPSCData = bdata[38:38 + IPSCEndOffset]
    else:
        parsed['therest'] = bdata[31:]
    
    outstr = str(data['end'])

    for v in parsed:
        if isinstance(parsed[v], int):
            outstr = outstr + "," + bytes.hex(parsed[v].to_bytes(length=1, byteorder='big'))
        else:
            outstr = outstr + "," + bytes.hex(parsed[v])
    print(outstr)

    if parsed['payloadType'].to_bytes(length=1, byteorder='big') == b"\x08":
        # TMS
        pass

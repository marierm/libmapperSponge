#!/usr/bin/python

import slip.SerialComm as SerialComm
import slip.ProtoSLIP as ProtoSLIP
import mapper

dev = mapper.device("sponge", 9000)

continuousNames = [
    "/acc1x", "/acc1y", "/acc1z",
    "/acc2x", "/acc2y", "/acc2z",
    "/fsr1", "/fsr2"
]
numButt = 10
numCont = len(continuousNames)


outputs = []

for i in range(numCont):
    outputs.append(dev.add_output(continuousNames[i], 1, 'i', "", 0, 1023))
for i in range(numButt):
    outputs.append(dev.add_output("/button" + str(i), 1, 'i', "", 0, 1))


ser = SerialComm.connectToSerialPort()
bytes = ProtoSLIP.decodeFromSLIP(ser)

# Make sure we have a complete packet before going on.
while (len(bytes) != 18):
    print len(bytes)
    bytes = ProtoSLIP.decodeFromSLIP(ser)

while 1:
    dev.poll(1)
    for i in range(numCont):
        outputs[i].update( (bytes[i*2] << 8) + bytes[(i*2)+1] )
    buttVal = (bytes[numCont*2] << 8) + bytes[(numCont*2) + 1]
    for i in range(numButt):
        outputs[numCont + i].update( buttVal >> i & 1 )
    bytes = ProtoSLIP.decodeFromSLIP(ser)
    
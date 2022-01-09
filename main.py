from os import name
from threading import Thread, Lock
import json
import socket, select
from datetime import datetime
import sys
import base64
import time
from pathlib import Path


ENCODING = "utf-8"
DISCOVER_MESSAGE_BYTES = b""
RESPONSE_MESSAGE_BYTES = b""

DISCOVER_TYPE = 1
DISCOVER_RESPONSE_TYPE = 2
MESSAGE_TYPE = 3
FILE_TYPE = 4
FILE_ACK_TYPE = 5


USER_NAME = ""
PORT =12345
IP =""
IP_BASE = ""
ONLINE_USERS = {}
DISCOVER_TIMESTAMPS = {}
# File Send
MAX_NUMBER_WINDOWS_OTHER = -1
FILE_TO_SEND = []
numberOfFilePartsOnAir = 0
isFileTotallySent = True

# File Recieve
MAX_NUMBER_WINDOWS = 10

mutex = Lock()

def getIP():
    sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sckt.connect(("10.10.10.10", 80))
    ip = sckt.getsockname()[0]
    sckt.close()
    ip_base = ".".join(ip.split(".")[0:-1]) + "."
    return ip, ip_base

### Listen and Discover Threads
def listen_thread_udp():
    decodedDiscoverMessageObject = ""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("", PORT))
        s.setblocking(0)
        while True:
            try:
                result = select.select([s],[],[])
                data = result[0][0].recv(10240)
                # print(data)
                decodedDiscoverMessageObject = json.loads(data.decode(ENCODING))
                # print(decodedDiscoverMessageObject)
                if decodedDiscoverMessageObject["type"] == DISCOVER_TYPE:
                    if decodedDiscoverMessageObject["IP"] == IP:
                        continue
                    hasSent = False
                    try:
                        timestamp = DISCOVER_TIMESTAMPS[decodedDiscoverMessageObject["name"]]
                        if timestamp == decodedDiscoverMessageObject["ID"]:
                            hasSent = True
                    except:
                        hasSent = False
                    if not hasSent:
                        mutex.acquire()
                        ONLINE_USERS[decodedDiscoverMessageObject["name"]] =  decodedDiscoverMessageObject["IP"]
                        mutex.release()
                        DISCOVER_TIMESTAMPS[decodedDiscoverMessageObject["name"]] = decodedDiscoverMessageObject["ID"]
                        sendMessageToIp(decodedDiscoverMessageObject["IP"], RESPONSE_MESSAGE_BYTES)
                elif decodedDiscoverMessageObject["type"] == FILE_TYPE:
                    if decodedDiscoverMessageObject["SEQ"] == 1:
                        print(decodedDiscoverMessageObject["name"]," is sending you a file!")
                    print(".", end="")
                    sys.stdout.flush()
                    writeFilePart(decodedDiscoverMessageObject["NAME"], decodedDiscoverMessageObject["BODY"], decodedDiscoverMessageObject["SEQ"])
                    ack_message_bytes = json.dumps({"type":FILE_ACK_TYPE, "SEQ":decodedDiscoverMessageObject["SEQ"], "name":USER_NAME, "RWND": MAX_NUMBER_WINDOWS}).encode(ENCODING)
                    ip = ONLINE_USERS[decodedDiscoverMessageObject["name"]]
                    sendMessageToIp(ip, ack_message_bytes)
                else:
                    print("ERROROCCURED")
            except:
                continue
                       
def listen_thread_tcp():
    global numberOfFilePartsOnAir
    global MAX_NUMBER_WINDOWS_OTHER
    decodedDiscoverMessageObject = ""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", PORT))
        s.listen()
        while True:
            # print("LISTENING")
            conn, a = s.accept()
            # print("connected to ", a)
            try:
                with conn:
                    data = conn.recv(10240)
                    # print(data)
                    decodedDiscoverMessageObject = json.loads(data.decode(ENCODING))
                    if decodedDiscoverMessageObject["type"] == DISCOVER_RESPONSE_TYPE: 
                        mutex.acquire()
                        ONLINE_USERS[decodedDiscoverMessageObject["name"]] =  decodedDiscoverMessageObject["IP"]
                        mutex.release()
                    elif decodedDiscoverMessageObject["type"] == MESSAGE_TYPE: 
                        print("Message from ", decodedDiscoverMessageObject["name"],": ", decodedDiscoverMessageObject["body"])
                    elif decodedDiscoverMessageObject["type"] == FILE_ACK_TYPE:
                        mutex.acquire()
                        numberOfFilePartsOnAir -= 1
                        FILE_TO_SEND[decodedDiscoverMessageObject["SEQ"]-1]["ACK"] = True
                        MAX_NUMBER_WINDOWS_OTHER = decodedDiscoverMessageObject["RWND"]
                        mutex.release()
                    else:
                        print("ERROROCCURED")
            except:
                continue

def discover_thread():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for i in range(10):
            sock.sendto(DISCOVER_MESSAGE_BYTES, ('<broadcast>', PORT))

def main_thread():
    global ONLINE_USERS
    print("You can type \'users\' to list the users online, \'exit\' to log out, or \'message <name> <message>\' to send messages, \'send <name> <fileName>\' to send files. Remember that the main.py and the file you are going to send must be in the same directory: ")
    while True:
        command = input()
        try:
            if len(command) == 0:
                continue
            elif command.split()[0] == 'users':
                for user in ONLINE_USERS.keys():
                    print(user)
                print()
            elif command.split()[0] == 'message':
                try:
                    mutex.acquire()
                    ip = ONLINE_USERS[command.split()[1]]
                    message = ' '.join(command.split()[2:])
                    mutex.release()
                    mes = {}
                    mes["type"] = 3
                    mes["name"] = USER_NAME
                    mes["body"] = message
                    mes = json.dumps(mes).encode(ENCODING)
                    didSentMessage = sendMessageToIpWithCheck(ip, message=mes)
                    if not didSentMessage:
                        print(command.split()[1], "seems disconnected. Please try again later.")
                        mutex.acquire()
                        ONLINE_USERS.pop(command.split()[1])
                        mutex.release()
                except: 
                    print("Ups, no user found")
            elif command.split()[0] == "send":
                try:
                    ip = ONLINE_USERS[command.split()[1]]
                except:
                    print("Ups, no user found")
                    continue
                fileName = command.split()[2]
                sendFile(fileName, ip)
            elif command.split()[0] == "exit":
                print("...Logging out...")
                sys.exit()
            else: 
                print("Ups, no command found")
        except KeyboardInterrupt:
            print("...Logging out...")
            exit()


### UDP TCP Send Message Functions
def sendMessageToIpWithCheck(ip, message):
    try:
        sendMessageToIp(ip, message, timeout=1)
        return True
    except:
        return False

def sendMessageToIp(ip, message, timeout = 0.2):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((ip, PORT))
        s.sendall(message)

def sendMessageToIpUdp(ip, message):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(message, (ip, PORT))


### FILE
## Send File
def readFile(filePath):
    global FILE_TO_SEND
    FILE_TO_SEND = []
    count = 1
    with open(filePath, "rb") as f:
        data = f.read(1500)
        while data:
            mes = {}
            mes["SEQ"] = count
            mes["ACK"] = False
            mes["TIME"] = 0
            mes["DATA"] = base64.b64encode(data).decode(ENCODING) # string
            count += 1
            FILE_TO_SEND.append(mes)
            data = f.read(1500)



def sendFile(fileName, ip):
    global isFileTotallySent
    global numberOfFilePartsOnAir
    if isFileTotallySent:
        isFileTotallySent = False
        numberOfFilePartsOnAir = 0
        try:
            f = open(fileName, "r")
            f.close()
        except:
            print("File not found")
            return
        readFile(fileName)
    sendFilePart(fileName, ip, 1)
    # print(len(FILE_TO_SEND))
    for _ in range(5):
        if MAX_NUMBER_WINDOWS_OTHER != -1:
            break
        time.sleep(1)
    if MAX_NUMBER_WINDOWS_OTHER == -1:
        print("Cannot send, try again")
        return False
    while not isFileTotallySent:
        mutex.acquire()
        while numberOfFilePartsOnAir < MAX_NUMBER_WINDOWS_OTHER:
            seq = 0
            for i, part in enumerate(FILE_TO_SEND):
                if not part["ACK"]:
                    if part["TIME"] == 0:
                        seq = i+1
                        break
                    timestamp = datetime.now()
                    if (timestamp - part["TIME"]).total_seconds() > 1:
                        seq = i+1
                        break
            if seq == 0:
                isFileTotallySent = True
                print()
                print("File Sent!")
                break
            sendFilePart(fileName, ip, seq)
            numberOfFilePartsOnAir += 1
        mutex.release()

        
def sendFilePart(fileName, ip, seq):
    mes = {}
    # print(FILE_TO_SEND)
    mes["NAME"] = fileName
    mes["name"] = USER_NAME
    mes["type"] = 4
    mes["SEQ"] = seq
    mes["BODY"] = FILE_TO_SEND[seq-1]["DATA"]
    mes = json.dumps(mes).encode(ENCODING)
    sendMessageToIpUdp(ip, mes)
    FILE_TO_SEND[seq-1]["TIME"] = datetime.now()
    print(".", end="")
    sys.stdout.flush()


## Recieve File
def writeFilePart(fileName, data, seq):
    try:
        f = open(fileName, "r+b")
        f.close()
    except:
        f = open(fileName, "w+b")
        f.close()
    with open(fileName, "r+b") as f:
        f.seek(1500*(seq - 1))
        f.write(base64.b64decode(data.encode(ENCODING)))



    






if __name__ == "__main__":
    discover = Thread(target = discover_thread, args = ())
    listen_tcp = Thread(target = listen_thread_tcp, args = ())
    listen_udp = Thread(target = listen_thread_udp, args = ())
    ui = Thread(target=main_thread, args=())
    print("Welcome to chatting app. To start chatting, you need to provide a name. Type your name. Your name cannot be changed later.")
    USER_NAME = ""
    while(USER_NAME == ""):
        USER_NAME = input("Enter a name: ")
    IP, IP_BASE = getIP()
    now = datetime.now()
    timestamp = int(datetime.timestamp(now))
    DISCOVER_MESSAGE_BYTES = json.dumps({"type":1, "name": USER_NAME, "IP":IP, "ID":timestamp}).encode(ENCODING)
    RESPONSE_MESSAGE_BYTES = json.dumps({"type":2, "name": USER_NAME, "IP":IP}).encode(ENCODING)
    ONLINE_USERS = {}
    discover.daemon = True
    listen_tcp.daemon = True
    listen_udp.daemon = True
    # # main_thread()
    listen_tcp.start()
    discover.start()
    # # discover_thread()
    listen_udp.start()
    ui.start()
    ui.join()
    if not ui.is_alive:
        sys.exit()


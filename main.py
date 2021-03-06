import json
import select
import socket
import sys
import threading
from datetime import datetime
from threading import Thread, Lock
from time import sleep
import multiprocessing

import cv2
import imutils
import pickle
import struct
from os import listdir

ip_address = ""
user_name = ""
port = 12345
streaming_port = 12346
room_users_dictionary = {}
rooms_dictionary = {}
discover_response_dictionary = {}
encoding = "utf-8"
host = False

# CLIENT
joined_room_name = ""
joined_room_ip = ""

DISCOVER_TYPE = 1
DISCOVER_RESPONSE_TYPE = 2
MESSAGE_TYPE = 3
JOIN_REQUEST_TYPE = 6
USER_LIST_REQUEST_TYPE = 4
USER_LIST_RESPONSE_TYPE = 5
EXIT_HOST_TYPE = 7

mutex = Lock()


def get_ip():
    global ip_address
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
    finally:
        s.close()


def create_message(message_type, body=""):
    global user_name
    global ip_address
    message = {}
    if message_type == DISCOVER_TYPE:
        curr_dt = datetime.now()
        timestamp = int(round(curr_dt.timestamp()))
        message = {"name": user_name, "IP": ip_address, "type": message_type, "ID": timestamp}
    elif message_type == DISCOVER_RESPONSE_TYPE:
        message = {"name": user_name, "IP": ip_address, "type": message_type}
    elif message_type == MESSAGE_TYPE:
        message = {"name": user_name, "type": message_type, "body": body}
    elif message_type == USER_LIST_REQUEST_TYPE:  # to get user list in the room
        message = {"name": user_name, "type": message_type, "IP": ip_address}
    elif message_type == USER_LIST_RESPONSE_TYPE:  # to send the user list
        message = {"name": user_name, "type": message_type, "users": room_users_dictionary}
    elif message_type == JOIN_REQUEST_TYPE:
        message = {"name": user_name, "IP": ip_address, "type": message_type}
    elif message_type == EXIT_HOST_TYPE:
        message = {"name": user_name, "IP": ip_address, "type": message_type}
    return json.dumps(message).encode(encoding=encoding)


def get_host_and_name():
    global user_name, host
    print("Welcome to video chatting app!")
    print("Do you want to be a host, or a watcher? Type host for host and watcher to be a watcher")
    user_type = ""
    while user_type != "host" and user_type != "watcher":
        user_type = input("Type host for host and watcher to be a watcher:")
    if user_type == "host":
        host = True
        while user_name == "":
            user_name = input("Please provide a room name:")
    else:
        while user_name == "":
            user_name = input("Enter your name:")


def discover_online_rooms():
    global rooms_dictionary
    mutex.acquire()
    rooms_dictionary = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for i in range(10):
            sock.sendto(create_message(1), ('<broadcast>', port))
    mutex.release()


def send_tcp_message_with_check(ip, message):
    try:
        send_tcp_message(ip, message, timeout=1)
        return True
    except:
        return False


def send_tcp_message(ip, message, timeout=0.2):
    global port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((ip, port))
        s.sendall(message)


def send_tcp_stream(ip, message, timeout=3):
    global streaming_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((ip, streaming_port))
        s.sendall(message)


def send_udp_message(ip, message):
    global port
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(message, (ip, port))


def print_online_devices():
    global room_users_dictionary
    mutex.acquire()
    if len(room_users_dictionary) == 0:
        print("There is no active user")
    else:
        print("Active Users:")
        for key in room_users_dictionary.keys():
            print(key)
    mutex.release()


def listen_host_udp():
    global room_users_dictionary
    global discover_response_dictionary
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("", port))
        s.setblocking(False)
        while True:
            result = select.select([s], [], [])
            json_msg = result[0][0].recv(10240)
            message = json.loads(json_msg.decode(encoding=encoding))
            if message["type"] == 1:
                if message["IP"] != ip_address:
                    has_sent = False
                    try:
                        timestamp = discover_response_dictionary[message["name"]]
                        if timestamp == message["ID"]:
                            has_sent = True
                    except:
                        has_sent = False
                    if not has_sent:
                        response = create_message(DISCOVER_RESPONSE_TYPE)
                        send_tcp_message(message["IP"], response)
                        discover_response_dictionary[message["name"]] = message["ID"]


def listen_host_tcp():
    global room_users_dictionary
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", port))
        s.listen()
        while True:
            conn, address = s.accept()
            with conn:
                output = conn.recv(10240)
                if output == "" or output is None:
                    print("There is a problem about your socket, you should restart your cmd or computer")
                    break
                response = json.loads(output.decode(encoding=encoding))
                if response["type"] == JOIN_REQUEST_TYPE:
                    mutex.acquire()
                    room_users_dictionary[response["name"]] = response["IP"]
                    mutex.release()
                    print(response["name"], " has joined your room!")
                elif response["type"] == DISCOVER_RESPONSE_TYPE:
                    rooms_dictionary[response["name"]] = response["IP"]
                elif response["type"] == USER_LIST_REQUEST_TYPE:
                    message = create_message(USER_LIST_RESPONSE_TYPE)
                    send_tcp_message(response["IP"], message)
                elif response["type"] == MESSAGE_TYPE:
                    print(response["name"] + ":   " + response["body"])


def listen_client_udp():
    pass


def list_client_tcp_video_stream():
    global room_users_dictionary, rooms_dictionary
    payload_size = struct.calcsize("Q")  # Q: unsigned long long integer(8 bytes)
    data = b""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", streaming_port))
        s.listen()
        while True:
            conn, address = s.accept()
            with conn:
                while len(data) < payload_size:
                    packet = conn.recv(4 * 1024)  # 4K, range(1024 byte to 64KB)
                    if not packet: break
                    data += packet  # append the data packet got from server into data variable
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]  # Actual frame data
                msg_size = struct.unpack("Q", packed_msg_size)[0]  # meassage size
                # print(msg_size)

                while len(data) < msg_size:
                    data += conn.recv(4 * 1024)  # will receive all frame data from client socket
                frame_data = data[:msg_size]  # recover actual frame data
                data = data[msg_size:]
                frame = pickle.loads(frame_data)  # de-serialize bytes into actual frame type
                cv2.imshow("RECEIVING VIDEO", frame)  # show video frame at client side
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):  # press q to exit video
                    break


def listen_client_tcp():
    global room_users_dictionary, rooms_dictionary
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", port))
        s.listen()
        while True:
            conn, address = s.accept()
            with conn:
                output = conn.recv(10240)
                if output == "" or output is None:
                    print("There is a problem about your socket, you should restart your cmd or computer")
                    break
                response = json.loads(output.decode(encoding=encoding))
                # print(response, "   TCP")
                if response["type"] == DISCOVER_RESPONSE_TYPE:
                    mutex.acquire()
                    rooms_dictionary[response["name"]] = response["IP"]
                    mutex.release()
                elif response["type"] == USER_LIST_RESPONSE_TYPE:
                    mutex.acquire()
                    room_users_dictionary = response["users"]
                    mutex.release()
                    show_room_participants()
                elif response["type"] == MESSAGE_TYPE:
                    print(response["name"] + ":   " + response["body"])
                elif response["type"] == EXIT_HOST_TYPE:
                    exit_room()


def show_online_rooms():
    global rooms_dictionary
    mutex.acquire()
    print(rooms_dictionary)
    if len(rooms_dictionary) == 0:
        print("There is no active room")
    else:
        print("Active Rooms:")
        for key in rooms_dictionary.keys():
            print(key)
    mutex.release()


def exit_room():
    global joined_room_ip, joined_room_name
    print("Room host seems disconnected! You are redirected to home!")
    joined_room_name = ""
    joined_room_ip = ""
    print("Here is the list of commands you can use:")
    print("rooms -> lists the avalible rooms")
    print("join <room_name>  -> join the room")


def join_room(room_name):
    global joined_room_ip, joined_room_name
    try:
        message = create_message(JOIN_REQUEST_TYPE)
        ip = rooms_dictionary[room_name]
        did_join = send_tcp_message_with_check(ip, message)
        if did_join:
            joined_room_name = room_name
            joined_room_ip = ip
            print("You have successfully joined ", room_name)
            print("Here is the list of commands you can use:")
            print("list  -> lists the online users in your room, use this only if you are in a room")
            print("send host <message> -> send a message to the host")
            print("send <user_name> <message> -> send a message to a specific user")
        else:
            print(room_name, " may no longer be online! Please try again.")
            rooms_dictionary.pop(room_name)
    except:
        print("No room named ", room_name, " is found!")


def show_room_participants():
    mutex.acquire()
    if len(room_users_dictionary) == 0:
        print("There is no active user in this room!")
    else:
        print("Joined Users:")
        for key in room_users_dictionary.keys():
            print(key)
    mutex.release()


def application_user_interface_for_client():
    global room_users_dictionary, joined_room_ip, user_name
    print("Welcome, ", user_name , "! Are you ready to join the rooms?")
    print("Here is the list of commands you can use:")
    print("rooms -> lists the avalible rooms")
    print("join <room_name>  -> join the room")
    while True:
        user_input = input()
        if user_input == "rooms":
            discover_online_rooms()
            print("Searching rooms....")
            sleep(1)
            show_online_rooms()
        elif user_input == "list":
            if joined_room_ip == "":
                print("You are not a member of any room!")
                continue
            message = create_message(USER_LIST_REQUEST_TYPE)
            did_sent = send_tcp_message_with_check(joined_room_ip, message)
            if not did_sent:
                exit_room()
        elif user_input.split()[0] == "join":
            try:
                join_room(user_input.split()[1])
            except:
                print("Please provide a room name!")
        elif user_input.split()[0] == "send":
            try:
                if user_input.split()[1] == "host":
                    ip = joined_room_ip
                    message = ' '.join(user_input.split()[2:])
                    mes = create_message(MESSAGE_TYPE, message)
                    did_sent_message = send_tcp_message_with_check(ip, message=mes)
                    if not did_sent_message:
                        exit_room()
                else:
                    try:
                        ip = room_users_dictionary[user_input.split()[1]]
                        message = ' '.join(user_input.split()[2:])
                        
                        mes = create_message(MESSAGE_TYPE, message)
                        did_sent_message = send_tcp_message_with_check(ip, message=mes)
                        if not did_sent_message:
                            print(user_input.split()[1], "seems disconnected. Please try again later.")
                            mutex.acquire()
                            room_users_dictionary.pop(user_input.split()[1])
                            mutex.release()
                    except:
                        print("No user found!")
            except:
                print("To send a message type \"send <username> <message>\" or \"send host <message>\"")
        else:
            print("No Valid Command")

        sleep(0.3)


def application_user_interface_for_host():
    global room_users_dictionary, user_name
    print("Welcome, welcome! Are you ready to be the coolest host?")
    print("Here is the list of commands you can use:")
    print("list -> lists the online users joined your room")
    print("send <user_name> <message> -> send a message to a specific user")
    print("stream -> start live video streaming")
    print("share <filename> -> start sharing video that is already in your directory")
    print("press \"q\" to end video streaming")
    print("exit -> to close the room")

    while True:
        user_input = input()
        if user_input == "list":
            show_room_participants()
        elif user_input.split()[0] == "send":
            try:
                ip = room_users_dictionary[user_input.split()[1]]
                message = ' '.join(user_input.split()[2:])
                mes = create_message(MESSAGE_TYPE, message)
                did_sent_message = send_tcp_message_with_check(ip, message=mes)
                if not did_sent_message:
                    print(user_input.split()[1], "seems disconnected. Please try again later.")
                    mutex.acquire()
                    room_users_dictionary.pop(user_input.split()[1])
                    mutex.release()
            except:
                print("Ups, no user found")
                continue
        elif user_input.split()[0] == "stream":
            ui = multiprocessing.Process(target=stream, args=(room_users_dictionary,))
            ui.start()
        elif user_input.split()[0] == "share":
            fileName = ""
            try:
                fileName = user_input.split()[1]
            except:
                print("Provide a file name!")
                continue
            if fileName in listdir():
                ui = multiprocessing.Process(target=stream, args=(room_users_dictionary,fileName,))
                ui.start()
            else:
                print("No file found!")

        elif user_input.split()[0] == "exit":
            for _, val in room_users_dictionary.items():
                message = create_message(EXIT_HOST_TYPE)
                send_tcp_message(val, message)
            exit(0)
        else:
            print("No Valid Command")

        sleep(0.3)


def stream(dict, fileName = None):
    if fileName:
        vid = cv2.VideoCapture(fileName)
    else:
        vid = cv2.VideoCapture(0)
    while vid.isOpened():
        img, frame = vid.read()
        frame = imutils.resize(frame, width=320)
        a = pickle.dumps(frame)  # serialize frame to bytes
        message = struct.pack("Q", len(a)) + a  # pack the serialized data
        # print(message)
        try:
            for ip in dict.values():
                send_tcp_stream(ip, message)

        except Exception as e:
            print(e)
            break

        cv2.imshow('TRANSMITTING VIDEO', frame)  # will show video frame on server side.
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            exit()


if __name__ == '__main__':
    get_ip()
    get_host_and_name()
    if host:
        listen_thread_udp = threading.Thread(target=listen_host_udp)
        listen_thread_tcp = threading.Thread(target=listen_host_tcp)
        listen_thread_tcp.daemon = True
        listen_thread_udp.daemon = True
        listen_thread_udp.start()
        listen_thread_tcp.start()
        application_user_interface_for_host()
    else:
        listen_thread_udp = threading.Thread(target=listen_client_udp)
        listen_thread_tcp = threading.Thread(target=listen_client_tcp)
        application_ui_thread = threading.Thread(target=application_user_interface_for_client)
        listen_thread_tcp.daemon = True
        listen_thread_udp.daemon = True
        listen_thread_udp.start()
        listen_thread_tcp.start()
        application_ui_thread.start()
        list_client_tcp_video_stream()




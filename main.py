import json
import socket
import select
from threading import Thread
from time import sleep
from datetime import datetime

ip_address = ""
my_name = ""
port = 12345
room_users_dictionary = {}
rooms_dictionary = {}
discover_response_dictionary = {}
encoding = "utf-8"
host = False


def get_ip():
    global ip_address
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
    finally:
        s.close()


def create_message(message_type, body=""):
    global my_name
    global ip_address
    message = {}
    if my_name == "":
        print("Enter your name: ")
        my_name = input()
    if message_type == 1:
        curr_dt = datetime.now()
        timestamp = int(round(curr_dt.timestamp()))
        message = {"name": my_name, "IP": ip_address, "type": message_type, "ID": timestamp}
    elif message_type == 2:
        message = {"name": my_name, "IP": ip_address, "type": message_type}
    elif message_type == 3:
        message = {"name": my_name, "type": message_type, "body": body}
    return json.dumps(message)


def type_check():
    global my_name, host
    if my_name == "":
        print("Enter your name: ")
    my_name = input()
    print("Do you want to be a host, or a watcher? Type host for host and watcher to be a watcher")
    user_type = ""
    while user_type != "host" or user_type != "watcher":
        user_type = input("Type host for host and watcher to be a watcher:")
    if user_type == "host":
        host = True
    else:
        discover_online_rooms()


def discover_online_rooms():
    global room_users_dictionary
    room_users_dictionary = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for i in range(10):
            sock.sendto(create_message(1).encode(encoding=encoding), ('<broadcast>', port))


def show_online_devices():
    global room_users_dictionary
    if len(room_users_dictionary) == 0:
        print("There is no active user")
    else:
        print("Active Users:")
        for key in room_users_dictionary.keys():
            print(key)


def listen_discover_message():
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
                    respond_message = create_message(2)
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as new_socket:
                        new_socket.connect((message["IP"], port))
                        new_socket.sendall(respond_message.encode(encoding=encoding))

                    # if not message["name"] in discover_response_dictionary.keys():
                    #     room_users_dictionary[message["name"]] = message["IP"]
                    #     discover_response_dictionary[message["name"]] = message["ID"]
                    #
                    # elif message["name"] in discover_response_dictionary.keys() and discover_response_dictionary[
                    #     message["name"]] != message["ID"]:
                    #     print(message["name"], "has changed id. Old ID: ",
                    #           discover_response_dictionary[message["name"]], 'new ID:', message["ID"])
                    #     room_users_dictionary[message["name"]] = message["IP"]
                    #     discover_response_dictionary[message["name"]] = message["ID"]
                    #     respond_message = create_message(2)
                    #     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as new_socket:
                    #         new_socket.connect((message["IP"], port))
                    #         new_socket.sendall(respond_message.encode(encoding=encoding))


def listen_message():
    global room_users_dictionary

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", port))
        s.listen()
        while True:
            conn, address = s.accept()
            with conn:
                output = conn.recv(10240)
                if output == "" or output is None:
                    print("There is a problem about your socket you should restart your cmd or computer")
                    break
                response = json.loads(output.decode(encoding=encoding))
                if response["type"] == 1:
                    if response["IP"] != ip_address:
                        room_users_dictionary[response["name"]] = response["IP"]
                    respond_message = create_message(2)
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as new_socket:
                        new_socket.connect((response["IP"], port))
                        new_socket.sendall(respond_message.encode(encoding=encoding))
                elif response["type"] == 2:
                    if response["IP"] != ip_address:
                        room_users_dictionary[response["name"]] = response["IP"]
                elif response["type"] == 3:
                    print(response["name"] + ":   " + response["body"])


def show_online_rooms():
    global rooms_dictionary
    if len(rooms_dictionary) == 0:
        print("There is no active room")
    else:
        print("Active Rooms:")
        for key in rooms_dictionary.keys():
            print(key)


# TODO
def join_room():
    pass


def application_user_interface_for_client():
    global room_users_dictionary
    while True:

        user_input = input()
        if user_input == "rooms":
            show_online_rooms()
        elif user_input == "list":
            show_online_devices()
        elif user_input.split()[0] == "join":
            join_room()
        elif user_input.split()[0] == "send":
            receiver = user_input.split()[1]
            if receiver in room_users_dictionary.keys():
                receiver_ip = room_users_dictionary.get(receiver)
                chat_message = " ".join(user_input.split()[2:])
                json_message = create_message(3, body=chat_message)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    try:
                        s.connect((receiver_ip, port))
                        s.sendall(json_message.encode(encoding=encoding))
                    except socket.error:
                        print("message cannot be sent! " + receiver + " is offline!")
                        room_users_dictionary.pop(receiver)
            else:
                print("No Such Active User!")
        else:
            print("No Valid Command")

        sleep(0.3)


def application_user_interface_for_host():
    global room_users_dictionary
    while True:
        user_input = input()
        if user_input == "list":
            show_online_devices()
        elif user_input.split()[0] == "send":
            receiver = user_input.split()[1]
            if receiver in room_users_dictionary.keys():
                receiver_ip = room_users_dictionary.get(receiver)
                chat_message = " ".join(user_input.split()[2:])
                json_message = create_message(3, body=chat_message)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    try:
                        s.connect((receiver_ip, port))
                        s.sendall(json_message.encode(encoding=encoding))
                    except socket.error:
                        print("message cannot be sent! " + receiver + " is offline!")
                        room_users_dictionary.pop(receiver)
            else:
                print("No Such Active User!")
        else:
            print("No Valid Command")

        sleep(0.3)


if __name__ == '__main__':
    get_ip()
    type_check()
    print(ip_address)
    application_ui_thread = Thread(target=application_user_interface_for_client)
    listen_thread = Thread(target=listen_message)
    discover_listen_thread = Thread(target=listen_discover_message)
    listen_thread.start()
    discover_listen_thread.start()
    application_ui_thread.start()

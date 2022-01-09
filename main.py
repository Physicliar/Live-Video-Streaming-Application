import json
import socket
import select
from threading import Thread
from time import sleep
from datetime import datetime

ip_address = ""
my_name = ""
port = 12345
ip_dictionary = {}
discover_response_dictionary = {}
encoding = "utf-8"


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


def discover_online_devices():
    global ip_dictionary
    global my_name
    ip_dictionary = {}
    if my_name == "":
        print("Enter your name: ")
    my_name = input()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for i in range(10):
            sock.sendto(create_message(1).encode(encoding=encoding), ('<broadcast>', port))


def show_online_devices():
    global ip_dictionary
    if len(ip_dictionary) == 0:
        print("There is no active user")
    else:
        print("Active Users:")
        for key in ip_dictionary.keys():
            print(key)


def listen_discover_message():
    global ip_dictionary
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
                    if not message["name"] in discover_response_dictionary.keys():
                        ip_dictionary[message["name"]] = message["IP"]
                        discover_response_dictionary[message["name"]] = message["ID"]
                        respond_message = create_message(2)
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as new_socket:
                            new_socket.connect((message["IP"], port))
                            new_socket.sendall(respond_message.encode(encoding=encoding))
                    elif message["name"] in discover_response_dictionary.keys() and discover_response_dictionary[
                        message["name"]] != message["ID"]:
                        print(message["name"], "has changed id. Old ID: ",
                              discover_response_dictionary[message["name"]], 'new ID:', message["ID"])
                        ip_dictionary[message["name"]] = message["IP"]
                        discover_response_dictionary[message["name"]] = message["ID"]
                        respond_message = create_message(2)
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as new_socket:
                            new_socket.connect((message["IP"], port))
                            new_socket.sendall(respond_message.encode(encoding=encoding))


def listen_message():
    global ip_dictionary

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
                        ip_dictionary[response["name"]] = response["IP"]
                    respond_message = create_message(2)
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as new_socket:
                        new_socket.connect((response["IP"], port))
                        new_socket.sendall(respond_message.encode(encoding=encoding))
                elif response["type"] == 2:
                    if response["IP"] != ip_address:
                        ip_dictionary[response["name"]] = response["IP"]
                elif response["type"] == 3:
                    print(response["name"] + ":   " + response["body"])


def application_user_interface():
    global ip_dictionary
    while True:

        user_input = input()
        if user_input == "list":
            show_online_devices()
        elif user_input.split()[0] == "send":
            receiver = user_input.split()[1]
            if receiver in ip_dictionary.keys():
                receiver_ip = ip_dictionary.get(receiver)
                chat_message = " ".join(user_input.split()[2:])
                json_message = create_message(3, body=chat_message)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    try:
                        s.connect((receiver_ip, port))
                        s.sendall(json_message.encode(encoding=encoding))
                    except socket.error:
                        print("message cannot be sent! " + receiver + " is offline!")
                        ip_dictionary.pop(receiver)
            else:
                print("No Such Active User!")
        else:
            print("No Valid Command")

        sleep(0.3)


if __name__ == '__main__':
    get_ip()
    print(ip_address)
    application_ui_thread = Thread(target=application_user_interface)
    listen_thread = Thread(target=listen_message)
    discover_listen_thread = Thread(target=listen_discover_message)
    listen_thread.start()
    discover_listen_thread.start()
    discover_online_devices()
    application_ui_thread.start()

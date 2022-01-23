# Video Sharing Program
This is a program that you can share pre recorded or live videos, or join
already existing rooms and watch the videos that are being shared, and
chat meanwhile. Welcome, and enjoy!

## How to run(Requirements)
Of course you need python3 :) at least 3.7
Install the requirements:
```bash
pip3 install -r requirements.txt
```
Just run the main.py
```bash
python3 main.py
```

## Usage

When you start the appication, you either be a host, or a watcher.

        Welcome to video chatting app!
        Do you want to be a host, or a watcher? Type host for host and watcher to be a watcher

If you type 'host', then you become the host, if the type watcher, then you continue as watcher.

### Host

If you select to be a host, that means you want to create a room and 
do video streaming or sharing. To finilize creating the room you must answer:

        Please provide a room name:

Hosts are able to:

* See the users that have joined their rooms.
* Chat with the users that have joined their rooms.
* Stream live or pre-recorded videos.

Here are the commands that are used for the features.
  
        list -> lists the online users joined your room

        send <user_name> <message> -> send a message to a specific user
        
        stream -> start live video streaming
        
        share <filename> -> start sharing video that is already in your directory
        
        press "q" to end video streaming
        
        exit -> to close the room

When a host exits, or connection is interrupted or lost, all of the users that have previously joined their room
are redirected to home

### Watcher

If you select to be a watcher, that means you can join an already existing room room and 
watch the video streaming or sharing. To finilize creating your account you must answer:

        Enter your name:

Watcher are able to:
* Before joining a room:
    * List the rooms available
    * Join one of the online rooms
        ```
        rooms -> lists the avalible rooms

        join <room_name>  -> join the room
        ```

* After joining a room:
    * List the users that are in the same room with you
    * Send messages to the host and the sers that are in the same room with you
        ```
        list  -> lists the online users in your room

        send host <message> -> send a message to the host

        send <user_name> <message> -> send a message to a specific user
        ```


When a host exits, or connection is interrupted or lost, you will be
are redirected to home


## Contributing

Öykü Yılmaz and Emre Demir


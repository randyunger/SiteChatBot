#!/usr/bin/env python
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, Namespace, emit, join_room, leave_room, \
    close_room, rooms, disconnect
from slackclient import SlackClient
import os
import time

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None

BOT_ID = os.environ.get("BOT_ID")
slack_token = os.environ.get('SLACK_BOT_TOKEN')
recent_msgs = set()
RECENT_MSGS_MAX_LEN = 50


def mk_slack_client():
    global slack_client
    slack_client = SlackClient(slack_token)
    slack_client.rtm_connect()
    return slack_client

slack_client = mk_slack_client()


class ServerState:
    def __init__(self):
        self.user_count = 0

    def inc(self):
        self.user_count += 1

    def dec(self):
        self.user_count -= 1

srvr_state = ServerState()

def extract_tokens(line):
    "Just extract the tokens, regardless of structure"
    if line and 'message' in line:
        message = line['message']
        if 'text' in message:
            text = message['text']
            print("--A text message!--" + text)
            channel = line.get('channel', None)
            typ = line.get('type', None)
            ts = line.get('ts', None)
            return text, channel, typ, ts
    elif line and 'text' in line:
        text = line['text']
        print("--A text message!--" + text)
        channel = line.get('channel', None)
        typ = line.get('type', None)
        ts = line.get('ts', None)
        return text, channel, typ, ts


def extract_message(json_msg):
    """Couldn't I wrap up a bunch of the state and functionality here into a class,
     so I wouldn't have use globals?"""
    # AT_BOT = "<@" + BOT_ID + ">"
    if json_msg and len(json_msg) > 0:
        for line in json_msg:
            line_str = line.__str__()
            print(line)
            global recent_msgs
            if not recent_msgs.__contains__(line_str):
                text, channel, typ, ts = extract_tokens(line)
                recent_msgs.add(line_str)
                "Truncate recent msgs if necessary"
                if recent_msgs.__len__() > RECENT_MSGS_MAX_LEN:
                    ix = RECENT_MSGS_MAX_LEN - recent_msgs.__len__()
                    new_recent_msgs = recent_msgs[ix:]
                    recent_msgs = new_recent_msgs
                return text, channel, typ
    return None, None, None


def handle_slack_line(jSlack):
    message, channel, type = extract_message(jSlack)
    # slack_client.api_call()
    if type == "message":
        print("Sending to visitor: " + message)
        socketio.emit('to_visitor',
                      {'data': message},
                      namespace='/chat')


READ_WEBSOCKET_DELAY = 1  # 1 sec delay


def background_thread():
    print("In bg thread")
    """Example of how to send server generated events to clients."""
    print("--listening for " + BOT_ID + "--")
    global slack_client
    slack_client.rtm_connect()
    print("--slack client connected--")
    while True:
        try:
            slack_line = slack_client.rtm_read()
            # slack_client.rtm_connect()
            if slack_line:
                handle_slack_line(slack_line)
        except ConnectionResetError:
            slack_client = mk_slack_client()
        socketio.sleep(READ_WEBSOCKET_DELAY)


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


class MyNamespace(Namespace):

    def on_to_host(self, message):
        msg_content = message['data']
        print("Visitor sent message: " + msg_content)
        slack_client.rtm_send_message("web_visitors", msg_content)
        # emit('to_visitor',
        #      {'data': message['data'], 'count': 0})

    # def on_my_broadcast_event(self, message):
    #     session['receive_count'] = session.get('receive_count', 0) + 1
    #     emit('my_response',
    #          {'data': message['data'], 'count': session['receive_count']},
    #          broadcast=True)
    #
    # def on_join(self, message):
    #     join_room(message['room'])
    #     session['receive_count'] = session.get('receive_count', 0) + 1
    #     emit('my_response',
    #          {'data': 'In rooms: ' + ', '.join(rooms()),
    #           'count': session['receive_count']})
    #
    # def on_leave(self, message):
    #     leave_room(message['room'])
    #     session['receive_count'] = session.get('receive_count', 0) + 1
    #     emit('my_response',
    #          {'data': 'In rooms: ' + ', '.join(rooms()),
    #           'count': session['receive_count']})
    #
    # def on_close_room(self, message):
    #     session['receive_count'] = session.get('receive_count', 0) + 1
    #     emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
    #                          'count': session['receive_count']},
    #          room=message['room'])
    #     close_room(message['room'])
    #
    # def on_my_room_event(self, message):
    #     session['receive_count'] = session.get('receive_count', 0) + 1
    #     emit('my_response',
    #          {'data': message['data'], 'count': session['receive_count']},
    #          room=message['room'])
    #
    # def on_disconnect_request(self):
    #     session['receive_count'] = session.get('receive_count', 0) + 1
    #     emit('my_response',
    #          {'data': 'Disconnected!', 'count': session['receive_count']})
    #     disconnect()
    #
    # def on_my_ping(self):
    #     emit('my_pong')
    #
    def on_connect(self):
        srvr_state.inc()
        print("User joined: Count: " + srvr_state.user_count.__str__())
        if srvr_state.user_count > 1:
            count_msg = "There's a new visitor on the site (" + srvr_state.user_count.__str__() + ")"
            print("Sending new visitor msg: " + count_msg)
            slack_client.rtm_send_message("web_visitors", count_msg)
        global thread
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)
        # emit('to_host', {'data': 'Connected', 'count': 0})

    def on_disconnect(self):
        srvr_state.dec()
        print("User left. Count: " + srvr_state.user_count.__str__())
        print('Client disconnected', request.sid)


socketio.on_namespace(MyNamespace('/chat'))


if __name__ == '__main__':
    socketio.run(app, debug=True)

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
slack_client = SlackClient(slack_token)
connected = slack_client.rtm_connect()

# def handle_command(msg, channel):
#     # response = "pong"
#     # slack_client.api_call("chat.postMessage", channel = channel, text=response, as_user=True)
#     # emit('to_visitor',
#     #     {'data': msg, 'count': 0})
#     print("Sending to visitor: " + msg)
#     socketio.emit('to_visitor',
#                   {'data': msg},
#                   namespace='/chat')

def extract_message(json_msg):
    AT_BOT = "<@" + BOT_ID + ">"
    if json_msg and len(json_msg) > 0:
        for line in json_msg:
            print(line)
            if line and 'message' in line:
                message = line['message']
                if 'text' in message:
                    text = message['text']
                    print("--A text message!--" + text)
                    out = text, line.get('channel', None), line.get('type', None)
                    return out
            elif line and 'text' in line:
                text = line['text']
                print("--A text message!--" + text)
                out = text, line.get('channel', None), line.get('type', None)
                return out
    return None, None, None

def handle_slack_line(jSlack):
    message, channel, type = extract_message(jSlack)
    # slack_client.api_call()
    if type == "message":
        print("Sending to visitor: " + message)
        socketio.emit('to_visitor',
                      {'data': message},
                      namespace='/chat')



# def parse_slack_output(slack_rtm_output):
#     AT_BOT = "<@" + BOT_ID + ">"
#     output_list = slack_rtm_output
#     if output_list and len(output_list) > 0:
#         for output in output_list:
#             print(output)
#             if output and 'message' in output:
#                 message = output['message']
#                 if 'text' in message:
#                     text = message['text']
#                     print("--A text message!--" + text)
#                     if AT_BOT in text:
#                         print("--A message for me!--")
#                         out = text.split(AT_BOT)[1].strip().lower(), output['channel']
#                         return out
#             if output and 'text' in output:
#                 text = output['text']
#                 print("--A text message!--" + text)
#                 if AT_BOT in text:
#                     print("--A message for me!--")
#                     out = text.split(AT_BOT)[1].strip().lower(), output['channel']
#                     return out
#     return None, None
#

def background_thread():
    print("In bg thread")
    """Example of how to send server generated events to clients."""
    READ_WEBSOCKET_DELAY = 1  # 1 sec delay
    if connected:
        print("--connected!--")
        print("--listening for " + BOT_ID + "--")
        while True:
            slack_line = slack_client.rtm_read()
            if slack_line:
                handle_slack_line(slack_line)

            socketio.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("connection failed")

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


class MyNamespace(Namespace):
    def on_to_host(self, message):
        msg_content = message['data']
        print("Visitor sent message: " + msg_content)
        slack_client.rtm_send_message("general", msg_content)
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
        global thread
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)
        # emit('my_response', {'data': 'Connected', 'count': 0})
    #
    # def on_disconnect(self):
    #     print('Client disconnected', request.sid)


socketio.on_namespace(MyNamespace('/chat'))


if __name__ == '__main__':
    socketio.run(app, debug=True)

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from slackclient import SlackClient
import os
import time

async_mode = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)

BOT_ID = os.environ.get("BOT_ID")
slack_token = os.environ.get('SLACK_BOT_TOKEN')
slack_client = SlackClient(slack_token)
connected = slack_client.rtm_connect()

# This loop never exits, can't start server
# @app.before_first_request
# def slack_hook():
#     READ_WEBSOCKET_DELAY = 1  # 1 sec delay
#     if connected:
#         print("--connected!--")
#         print("--listening for " + BOT_ID + "--")
#         while True:
#             command, channel = parse_slack_output(slack_client.rtm_read())
#             if command and channel:
#                 handle_command(command, channel)
#             time.sleep(READ_WEBSOCKET_DELAY)
#     else:
#         print("connection failed")


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

@app.route('/test')
def hello_world():
    return "Hello World"

@socketio.on('to_host', namespace='/chat')
def test_message(message):
    # session['receive_count'] = session.get('receive_count', 0) + 1
    print("Sending message to slack: " + message['data'])
    slack_client.rtm_send_message("general", message['data'])

    #Echo back to user
    emit('to_visitor',
         {'data': message['data'], 'count': 0}) #session['receive_count']})

def handle_command(command, channel):
    response = "pong"
    slack_client.api_call("chat.postMessage", channel = channel, text=response, as_user=True)

def parse_slack_output(slack_rtm_output):
    AT_BOT = "<@" + BOT_ID + ">"
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            print(output)
            if output and 'message' in output:
                message = output['message']
                if 'text' in message:
                    text = message['text']
                    print("--A text message!--" + text)
                    if AT_BOT in text:
                        print("--A message for me!--")
                        return text.split(AT_BOT)[1].strip().lower, output['channel']
    return None, None



if __name__ == '__main__':
    socketio.run(app, debug=True)

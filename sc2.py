from flask import Flask, render_template
from flask_socketio import SocketIO, emit

async_mode = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

@app.route('/test')
def hello_world():
    return "Hello World"

@socketio.on('to_host', namespace='/chat')
def test_message(message):
    # session['receive_count'] = session.get('receive_count', 0) + 1
    emit('to_visitor',
         {'data': message['data'], 'count': 0}) #session['receive_count']})

if __name__ == '__main__':
    socketio.run(app, debug=True)

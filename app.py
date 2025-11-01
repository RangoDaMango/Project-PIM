# 1️⃣ Monkey-patch **before** any other imports
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
# ⚡ Make sure to use eventlet explicitly
socketio = SocketIO(app, async_mode='eventlet')

# Store usernames and rooms temporarily (in-memory)
users = {}

@app.route('/')
def index():
    return render_template('chat.html')

@socketio.on('join')
def handle_join(data):
    username = data['username']
    room = data['room']
    users[request.sid] = {'username': username, 'room': room}

    join_room(room)
    emit('receive_message', {'message': f'{username} has joined the room.'}, room=room)

@socketio.on('send_message')
def handle_send_message(data):
    user = users.get(request.sid)
    if user:
        room = user['room']
        username = user['username']
        message = data['message']
        emit('receive_message', {'message': f'{username}: {message}'}, room=room)

@socketio.on('disconnect')
def handle_disconnect():
    user = users.pop(request.sid, None)
    if user:
        leave_room(user['room'])
        emit('receive_message', {'message': f'{user["username"]} has left the room.'}, room=user['room'])

if __name__ == '__main__':
    # ⚡ Use eventlet explicitly here too
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

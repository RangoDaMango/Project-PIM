# 1️⃣ Monkey-patch before any other imports
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# In-memory user tracking
# users = { sid: {"username": ..., "room": ...} }
users = {}

@app.route('/')
def index():
    return render_template('chat.html')

# 🟢 Handle when a user joins a room
@socketio.on('join')
def handle_join(data):
    username = data['username']
    room = data['room']

    users[request.sid] = {'username': username, 'room': room}
    join_room(room)

    emit('receive_message', {'message': f'{username} has joined the room.'}, room=room)
    emit_user_and_room_updates(room)

# 💬 Handle when a message is sent
@socketio.on('send_message')
def handle_send_message(data):
    user = users.get(request.sid)
    if user:
        room = user['room']
        username = user['username']
        message = data['message']
        emit('receive_message', {'message': f'{username}: {message}'}, room=room)

# 🔴 Handle when a user disconnects
@socketio.on('disconnect')
def handle_disconnect():
    user = users.pop(request.sid, None)
    if user:
        leave_room(user['room'])
        emit('receive_message', {'message': f'{user["username"]} has left the room.'}, room=user['room'])
        emit_user_and_room_updates(user['room'])

# 🧠 New: Send list of users in a room
@socketio.on('get_users')
def handle_get_users(data):
    room = data.get('room')
    room_users = [u['username'] for u in users.values() if u['room'] == room]
    emit('user_list', {'users': room_users})

# 🧠 New: Send list of all active rooms
@socketio.on('get_rooms')
def handle_get_rooms():
    all_rooms = sorted(set(u['room'] for u in users.values()))
    emit('room_list', {'rooms': all_rooms})

# 🧩 Helper to refresh both user and room lists after changes
def emit_user_and_room_updates(room):
    room_users = [u['username'] for u in users.values() if u['room'] == room]
    all_rooms = sorted(set(u['room'] for u in users.values()))
    emit('user_list', {'users': room_users}, room=request.sid)
    emit('room_list', {'rooms': all_rooms}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

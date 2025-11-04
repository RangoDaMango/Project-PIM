# 1️⃣ Monkey-patch before any other imports
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# In-memory user tracking
# users = { sid: {"username": ..., "room": ... or None} }
users = {}

@app.route('/')
def index():
    return render_template('chat.html')

# 🟢 Handle when a user joins a room
@socketio.on('join')
def handle_join(data):
    username = data['username']
    room = data['room']

    # Save the user's info
    users[request.sid] = {'username': username, 'room': room}
    join_room(room)

    # Announce to the room
    emit('receive_message', {
        'username': 'System',
        'message': f'{username} has joined the room.'
    }, room=room)

    emit_user_and_room_updates(room)
    emit_global_user_list()

# 💬 Handle when a message is sent
@socketio.on('send_message')
def handle_send_message(data):
    user = users.get(request.sid)
    if user:
        room = user['room']
        username = user['username']
        message = data['message']
        emit('receive_message', {
            'username': username,
            'message': message
        }, room=room)

# 🔴 Handle when a user disconnects
@socketio.on('disconnect')
def handle_disconnect():
    user = users.pop(request.sid, None)
    if user:
        leave_room(user['room'])
        emit('receive_message', {
            'username': 'System',
            'message': f'{user["username"]} has left the room.'
        }, room=user['room'])

        emit_user_and_room_updates(user['room'])
        emit_global_user_list()
    else:
        emit_global_user_list()

# 🧠 Send list of users in a specific room
@socketio.on('get_users')
def handle_get_users(data):
    room = data.get('room')
    room_users = [u['username'] for u in users.values() if u['room'] == room]
    emit('user_list', {'users': room_users})

# 🧠 Send list of all active rooms
@socketio.on('get_rooms')
def handle_get_rooms():
    all_rooms = sorted(set(u['room'] for u in users.values() if u['room']))
    emit('room_list', {'rooms': all_rooms})

# 🌍 Send list of all connected users (global list)
@socketio.on('get_global_users')
def handle_get_global_users():
    all_users = [u['username'] for u in users.values()]
    emit('global_user_list', {'users': all_users})

# 🧩 Helper functions
def emit_user_and_room_updates(room):
    """Refresh both user and room lists after any change."""
    room_users = [u['username'] for u in users.values() if u['room'] == room]
    all_rooms = sorted(set(u['room'] for u in users.values() if u['room']))
    emit('user_list', {'users': room_users}, room=request.sid)
    emit('room_list', {'rooms': all_rooms}, broadcast=True)

def emit_global_user_list():
    """Broadcast a fresh list of all users (for join screen)."""
    all_users = [u['username'] for u in users.values()]
    socketio.emit('global_user_list', {'users': all_users}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

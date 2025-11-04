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

# Optional admin list for restricted commands
admins = set()  # you can add your own sid after connecting

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

    emit('receive_message', {'username': 'System', 'message': f'{username} has joined the room.'}, room=room)
    emit_user_and_room_updates(room)


# 💬 Handle when a message is sent
@socketio.on('send_message')
def handle_send_message(data):
    user = users.get(request.sid)
    if not user:
        return

    room = user['room']
    username = user['username']
    message = data['message'].strip()

    # --- Command handling ---
    if message.startswith('/'):
        parts = message.split(' ', 2)
        command = parts[0].lower()

        # 🧩 /nick <newname>
        if command == '/nick' and len(parts) > 1:
            new_name = parts[1].strip()
            old_name = username
            users[request.sid]['username'] = new_name
            emit('receive_message', {'username': 'System', 'message': f'{old_name} is now known as {new_name}.'}, room=room)
            emit_user_and_room_updates(room)
            return

        # 🧩 /announce <message>
        elif command == '/announce' and len(parts) > 1:
            announcement = ' '.join(parts[1:]).strip()  # Join all words after the command
            emit('receive_message', {'username': 'System', 'message': f'📢 {announcement}'}, broadcast=True)
            return

        # 🧩 /shrug
        elif command == '/shrug':
            emit('receive_message', {'username': username, 'message': '¯\\_(ツ)_/¯'}, room=room)
            return

        # 🧩 /prank <targetName> <message>
        elif command == '/prank':
            # basic parsing
            if len(parts) < 3:
                emit('receive_message', {'username': 'System', 'message': 'Usage: /prank <name> <message>'}, room=request.sid)
                return

            target_name = parts[1].strip()
            prank_text = parts[2].strip()

            # broadcast message marked as prank
            emit('receive_message', {
                'username': target_name,
                'message': prank_text,
                'prank': True,
                'real_sender': username
            }, room=room)
            print(f"[PRANK] {username} pranked as {target_name} in {room}: {prank_text}")
            return

        # Unknown command
        else:
            emit('receive_message', {'username': 'System', 'message': f'Unknown command: {command}'}, room=request.sid)
            return

    # --- Normal chat message ---
    emit('receive_message', {'username': username, 'message': message}, room=room)


# 🔴 Handle when a user disconnects
@socketio.on('disconnect')
def handle_disconnect():
    user = users.pop(request.sid, None)
    if user:
        leave_room(user['room'])
        emit('receive_message', {'username': 'System', 'message': f'{user["username"]} has left the room.'}, room=user['room'])
        emit_user_and_room_updates(user['room'])


# 🧠 Send list of users in a room
@socketio.on('get_users')
def handle_get_users(data):
    room = data.get('room')
    room_users = [u['username'] for u in users.values() if u['room'] == room]
    emit('user_list', {'users': room_users})


# 🧠 Send list of all active rooms
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

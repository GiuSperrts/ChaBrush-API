# Created by: Giuseppe Alehandro Lemuel

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from cryptography.fernet import Fernet
import bcrypt
import os
import logging
from datetime import datetime
import threading
import time
from auto_fix import AutoFix

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('chabrush')

# Generate or load encryption key
key_file = 'secret.key'
if os.path.exists(key_file):
    with open(key_file, 'rb') as f:
        key = f.read()
else:
    key = Fernet.generate_key()
    with open(key_file, 'wb') as f:
        f.write(key)

cipher = Fernet(key)

# In-memory storage (use database in production)
users = {}
messages = {}
calls = {}
groups = {}
files = {}

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            logger.warning("Register: No JSON data provided")
            return jsonify({"error": "No data provided"}), 400
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        if not username or not password:
            logger.warning("Register: Missing username or password")
            return jsonify({"error": "Username and password required"}), 400
        if len(username) < 3 or len(password) < 6:
            logger.warning("Register: Username or password too short")
            return jsonify({"error": "Username must be at least 3 characters, password at least 6"}), 400
        if username in users:
            logger.warning(f"Register: Username {username} already exists")
            return jsonify({"error": "Username already taken"}), 400
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        users[username] = {"password": hashed_password, "online": True, "profile": {"bio": "", "avatar": ""}, "created_at": datetime.now().isoformat()}
        logger.info(f"User {username} registered successfully")
        return jsonify({"message": f"User {username} registered"})
    except Exception as e:
        logger.error(f"Register error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password or username not in users:
        return jsonify({"error": "Invalid credentials"}), 401
    if bcrypt.checkpw(password.encode('utf-8'), users[username]['password'].encode('utf-8')):
        users[username]['online'] = True
        return jsonify({"message": f"User {username} logged in"})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    data = request.get_json()
    username = data.get('username')
    if username in users:
        users[username]['online'] = False
        return jsonify({"message": f"User {username} logged out"})
    return jsonify({"error": "User not found"}), 404

@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify({"users": list(users.keys())})

@app.route('/api/messages/<username>', methods=['GET'])
def get_messages(username):
    if username not in messages:
        return jsonify({"messages": []})
    decrypted_messages = []
    for msg in messages[username]:
        try:
            decrypted = cipher.decrypt(msg['content'].encode()).decode()
            decrypted_messages.append({"from": msg['from'], "content": decrypted})
        except:
            decrypted_messages.append({"from": msg['from'], "content": "Decryption failed"})
    return jsonify({"messages": decrypted_messages})

@app.route('/api/send_message', methods=['POST'])
def send_message():
    try:
        data = request.get_json()
        if not data:
            logger.warning("Send message: No JSON data provided")
            return jsonify({"error": "No data provided"}), 400
        to_user = data.get('to', '').strip()
        from_user = data.get('from', '').strip()
        content = data.get('content', '').strip()
        if not all([to_user, from_user, content]):
            logger.warning("Send message: Missing fields")
            return jsonify({"error": "Missing fields"}), 400
        if to_user not in users or from_user not in users:
            logger.warning("Send message: Invalid users")
            return jsonify({"error": "Invalid users"}), 400
        encrypted_content = cipher.encrypt(content.encode()).decode()
        timestamp = datetime.now().isoformat()
        if to_user not in messages:
            messages[to_user] = []
        messages[to_user].append({"from": from_user, "content": encrypted_content, "timestamp": timestamp, "read": False, "reactions": []})
        logger.info(f"Message sent from {from_user} to {to_user}")
        socketio.emit('new_message', {"from": from_user, "content": content, "timestamp": timestamp}, room=to_user)
        return jsonify({"message": "Message sent"})
    except Exception as e:
        logger.error(f"Send message error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/start_call', methods=['POST'])
def start_call():
    data = request.get_json()
    caller = data.get('caller')
    callee = data.get('callee')
    if not all([caller, callee]):
        return jsonify({"error": "Missing caller or callee"}), 400
    call_id = f"{caller}_{callee}"
    calls[call_id] = {"status": "ringing", "caller": caller, "callee": callee}
    socketio.emit('call_incoming', {"call_id": call_id, "caller": caller}, room=callee)
    return jsonify({"call_id": call_id, "status": "ringing"})

@app.route('/api/answer_call', methods=['POST'])
def answer_call():
    data = request.get_json()
    call_id = data.get('call_id')
    if call_id not in calls:
        return jsonify({"error": "Call not found"}), 404
    calls[call_id]["status"] = "connected"
    socketio.emit('call_connected', {"call_id": call_id}, room=calls[call_id]["caller"])
    return jsonify({"status": "connected"})

@app.route('/api/end_call', methods=['POST'])
def end_call():
    data = request.get_json()
    call_id = data.get('call_id')
    if call_id in calls:
        socketio.emit('call_ended', {"call_id": call_id}, room=calls[call_id]["caller"])
        socketio.emit('call_ended', {"call_id": call_id}, room=calls[call_id]["callee"])
        del calls[call_id]
    return jsonify({"message": "Call ended"})

@app.route('/api/create_group', methods=['POST'])
def create_group():
    data = request.get_json()
    group_name = data.get('group_name')
    creator = data.get('creator')
    if not group_name or not creator or group_name in groups:
        return jsonify({"error": "Invalid group name or group already exists"}), 400
    groups[group_name] = {"creator": creator, "members": [creator], "messages": []}
    return jsonify({"message": f"Group {group_name} created"})

@app.route('/api/join_group', methods=['POST'])
def join_group():
    data = request.get_json()
    group_name = data.get('group_name')
    username = data.get('username')
    if group_name not in groups or username not in users:
        return jsonify({"error": "Group or user not found"}), 404
    if username not in groups[group_name]['members']:
        groups[group_name]['members'].append(username)
    return jsonify({"message": f"User {username} joined group {group_name}"})

@app.route('/api/send_group_message', methods=['POST'])
def send_group_message():
    data = request.get_json()
    group_name = data.get('group_name')
    from_user = data.get('from')
    content = data.get('content')
    if group_name not in groups or from_user not in groups[group_name]['members']:
        return jsonify({"error": "Group not found or user not in group"}), 404
    encrypted_content = cipher.encrypt(content.encode()).decode()
    groups[group_name]['messages'].append({"from": from_user, "content": encrypted_content})
    for member in groups[group_name]['members']:
        if member != from_user:
            socketio.emit('group_message', {"group": group_name, "from": from_user, "content": content}, room=member)
    return jsonify({"message": "Group message sent"})

@app.route('/api/get_group_messages/<group_name>', methods=['GET'])
def get_group_messages(group_name):
    if group_name not in groups:
        return jsonify({"messages": []})
    decrypted_messages = []
    for msg in groups[group_name]['messages']:
        try:
            decrypted = cipher.decrypt(msg['content'].encode()).decode()
            decrypted_messages.append({"from": msg['from'], "content": decrypted})
        except:
            decrypted_messages.append({"from": msg['from'], "content": "Decryption failed"})
    return jsonify({"messages": decrypted_messages})

@app.route('/api/upload_file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    username = request.form.get('username')
    if not username or username not in users:
        return jsonify({"error": "Invalid user"}), 400
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    file_id = f"{username}_{file.filename}"
    files[file_id] = {"filename": file.filename, "data": file.read(), "uploader": username}
    return jsonify({"message": "File uploaded", "file_id": file_id})

@app.route('/api/download_file/<file_id>', methods=['GET'])
def download_file(file_id):
    if file_id not in files:
        return jsonify({"error": "File not found"}), 404
    file_data = files[file_id]
    return file_data['data'], 200, {'Content-Type': 'application/octet-stream', 'Content-Disposition': f'attachment; filename={file_data["filename"]}'}

@app.route('/api/delete_message', methods=['POST'])
def delete_message():
    data = request.get_json()
    username = data.get('username')
    message_index = data.get('message_index')
    if username not in messages or message_index >= len(messages[username]):
        return jsonify({"error": "Message not found"}), 404
    del messages[username][message_index]
    return jsonify({"message": "Message deleted"})

@app.route('/api/edit_message', methods=['POST'])
def edit_message():
    try:
        data = request.get_json()
        if not data:
            logger.warning("Edit message: No JSON data provided")
            return jsonify({"error": "No data provided"}), 400
        username = data.get('username', '').strip()
        message_index = int(data.get('message_index', -1))
        new_content = data.get('new_content', '').strip()
        if not username or message_index < 0 or not new_content:
            logger.warning("Edit message: Invalid data")
            return jsonify({"error": "Invalid data"}), 400
        if username not in messages or message_index >= len(messages[username]):
            logger.warning("Edit message: Message not found")
            return jsonify({"error": "Message not found"}), 404
        encrypted_content = cipher.encrypt(new_content.encode()).decode()
        messages[username][message_index]['content'] = encrypted_content
        messages[username][message_index]['edited'] = True
        logger.info(f"Message edited for {username} at index {message_index}")
        return jsonify({"message": "Message edited"})
    except Exception as e:
        logger.error(f"Edit message error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/react_message', methods=['POST'])
def react_message():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        username = data.get('username', '').strip()
        message_index = int(data.get('message_index', -1))
        reaction = data.get('reaction', '').strip()
        if not username or message_index < 0 or not reaction:
            return jsonify({"error": "Invalid data"}), 400
        if username not in messages or message_index >= len(messages[username]):
            return jsonify({"error": "Message not found"}), 404
        if reaction not in messages[username][message_index]['reactions']:
            messages[username][message_index]['reactions'].append(reaction)
        logger.info(f"Reaction added to message for {username}")
        return jsonify({"message": "Reaction added"})
    except Exception as e:
        logger.error(f"React message error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/mark_read', methods=['POST'])
def mark_read():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        username = data.get('username', '').strip()
        message_index = int(data.get('message_index', -1))
        if not username or message_index < 0:
            return jsonify({"error": "Invalid data"}), 400
        if username not in messages or message_index >= len(messages[username]):
            return jsonify({"error": "Message not found"}), 404
        messages[username][message_index]['read'] = True
        logger.info(f"Message marked as read for {username}")
        return jsonify({"message": "Message marked as read"})
    except Exception as e:
        logger.error(f"Mark read error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/user_profile/<username>', methods=['GET', 'POST'])
def user_profile(username):
    if request.method == 'GET':
        if username not in users:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"profile": users[username]['profile']})
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400
            bio = data.get('bio', '').strip()
            avatar = data.get('avatar', '').strip()
            users[username]['profile'] = {"bio": bio, "avatar": avatar}
            logger.info(f"Profile updated for {username}")
            return jsonify({"message": "Profile updated"})
        except Exception as e:
            logger.error(f"Update profile error: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

@app.route('/api/batch_send', methods=['POST'])
def batch_send():
    try:
        data = request.get_json()
        if not data or 'messages' not in data:
            return jsonify({"error": "No messages provided"}), 400
        results = []
        for msg in data['messages']:
            to_user = msg.get('to', '').strip()
            from_user = msg.get('from', '').strip()
            content = msg.get('content', '').strip()
            if not all([to_user, from_user, content]):
                results.append({"error": "Missing fields for message"})
                continue
            if to_user not in users or from_user not in users:
                results.append({"error": "Invalid users"})
                continue
            encrypted_content = cipher.encrypt(content.encode()).decode()
            timestamp = datetime.now().isoformat()
            if to_user not in messages:
                messages[to_user] = []
            messages[to_user].append({"from": from_user, "content": encrypted_content, "timestamp": timestamp, "read": False, "reactions": []})
            socketio.emit('new_message', {"from": from_user, "content": content, "timestamp": timestamp}, room=to_user)
            results.append({"message": "Sent"})
        logger.info(f"Batch send completed with {len(results)} results")
        return jsonify({"results": results})
    except Exception as e:
        logger.error(f"Batch send error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@socketio.on('join')
def on_join(data):
    username = data['username']
    join_room(username)
    emit('status', {'msg': f'{username} has entered the room.'})

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    leave_room(username)
    emit('status', {'msg': f'{username} has left the room.'})

@socketio.on('typing')
def on_typing(data):
    username = data['username']
    room = data.get('room', username)
    emit('user_typing', {'username': username}, room=room, skip_sid=True)

@socketio.on('stop_typing')
def on_stop_typing(data):
    username = data['username']
    room = data.get('room', username)
    emit('user_stop_typing', {'username': username}, room=room, skip_sid=True)

@socketio.on('send_message')
def handle_send_message(data):
    from_user = data['from']
    to_user = data['to']
    content = data['content']
    encrypted_content = cipher.encrypt(content.encode()).decode()
    if to_user not in messages:
        messages[to_user] = []
    messages[to_user].append({"from": from_user, "content": encrypted_content})
    emit('new_message', {"from": from_user, "content": content}, room=to_user)

@socketio.on('join_group')
def on_join_group(data):
    username = data['username']
    group_name = data['group_name']
    if group_name in groups and username in groups[group_name]['members']:
        join_room(group_name)
        emit('status', {'msg': f'{username} joined group {group_name}'}, room=group_name)

@socketio.on('leave_group')
def on_leave_group(data):
    username = data['username']
    group_name = data['group_name']
    leave_room(group_name)
    emit('status', {'msg': f'{username} left group {group_name}'}, room=group_name)

# Initialize auto-fix system
auto_fixer = AutoFix()

def perform_startup_checks():
    """Perform comprehensive health checks before starting the application"""
    logger.info("Performing startup health checks...")
    
    # Run auto-fix routine
    try:
        auto_fixer.auto_fix()
        logger.info("Startup checks completed successfully")
    except Exception as e:
        logger.critical(f"Critical failure during startup checks: {str(e)}")
        # Send emergency report for startup failure
        auto_fixer.send_emergency_report(
            "CRITICAL STARTUP FAILURE",
            f"Application failed startup checks: {str(e)}"
        )
        # Exit with error code to prevent startup
        exit(1)

# Perform startup checks before starting the app
perform_startup_checks()

def start_auto_fix_monitoring():
    """Start the auto-fix monitoring in a separate thread"""
    def monitor():
        while True:
            try:
                auto_fixer.auto_fix()
                time.sleep(3600)  # Check every hour
            except Exception as e:
                logger.error(f"Auto-fix monitoring error: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    logger.info("Auto-fix monitoring started")

# Start auto-fix monitoring when app starts
start_auto_fix_monitoring()

if __name__ == '__main__':
    socketio.run(app, debug=True)

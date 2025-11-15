# Chat App API - Advanced Features

Created by: Giuseppe Alehandro Lemuel

This is a comprehensive Flask-based API for a secure, real-time chat application with advanced features like encrypted messaging, voice calls, group chats, file sharing, user profiles, message reactions, read receipts, and batch operations. Built with simplicity for clients while handling complex backend data processing.

## Features

- **User Management**: Registration, login, logout, profiles with bio and avatar
- **Encrypted Messaging**: Real-time messaging with timestamps, read receipts, reactions, editing/deletion
- **Voice/Video Calls**: Start, answer, and end calls with status tracking
- **Group Chats**: Create and join groups, send group messages
- **File Sharing**: Upload and download files securely
- **Advanced Features**: Message reactions, read receipts, batch sending, user profiles
- **Real-time**: SocketIO for instant updates
- **Security**: End-to-end encryption, password hashing, comprehensive logging
- **Data Processing**: Timestamps, validation, error handling, logging for all operations

## Installation

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the API:
   ```
   python3 app.py
   ```

The API will be available at http://127.0.0.1:5000 (or configured port)

3. For frontend, serve `chat_app/` directory (e.g., `python -m http.server 8000`)

## API Endpoints

### Authentication & User Management

- **POST /api/register** - Register new user (username, password) with validation
- **POST /api/login** - Login user
- **POST /api/logout** - Logout user
- **GET /api/users** - Get all users
- **GET /api/user_profile/<username>** - Get user profile (bio, avatar)
- **POST /api/user_profile/<username>** - Update user profile

### Messaging

- **POST /api/send_message** - Send encrypted message with timestamp
- **POST /api/batch_send** - Send multiple messages at once (client simplification)
- **GET /api/messages/<username>** - Get decrypted messages with metadata
- **POST /api/edit_message** - Edit message (marks as edited)
- **POST /api/delete_message** - Delete message
- **POST /api/react_message** - Add reaction to message
- **POST /api/mark_read** - Mark message as read

### Calls

- **POST /api/start_call** - Start call with timestamp
- **POST /api/answer_call** - Answer call
- **POST /api/end_call** - End call

### Groups

- **POST /api/create_group** - Create group
- **POST /api/join_group** - Join group
- **POST /api/send_group_message** - Send group message
- **GET /api/get_group_messages/<group_name>** - Get group messages

### Files

- **POST /api/upload_file** - Upload file
- **GET /api/download_file/<file_id>** - Download file

## Real-time Events (SocketIO)

- **join/leave**: Room management
- **new_message**: Message reception with timestamp
- **call_incoming/connected/ended**: Call events
- **typing/stop_typing**: Typing indicators
- **group_message**: Group chat updates
- **status**: General notifications

## Usage Guide

### For Developers
- All endpoints return JSON with proper error handling
- Messages encrypted on send, decrypted on receive
- Comprehensive logging for data processing monitoring
- Batch endpoints reduce client complexity

### For Users
1. Register with strong credentials
2. Update profile with bio/avatar
3. Chat with reactions and read receipts
4. Create/join groups for team communication
5. Share files securely
6. Make calls with real-time status

## Security & Data Processing

- **Encryption**: Fernet symmetric for messages
- **Hashing**: bcrypt for passwords
- **Logging**: All operations logged with timestamps
- **Validation**: Input sanitization and length checks
- **Error Handling**: Try/catch with detailed logging
- **CORS**: Enabled for frontend integration

## Testing

Run tests:
```
python3 -m pytest test_app.py -v
```

## Auto-Fix System

The API includes an intelligent auto-fix system that automatically monitors and maintains the application:

### Features
- **Dependency Management**: Automatically installs missing dependencies
- **Syntax Checking**: Validates Python code syntax
- **Health Monitoring**: Checks app import and startup health
- **Test Execution**: Runs test suite automatically
- **Memory Monitoring**: Tracks memory usage and logs warnings
- **Backup System**: Creates automatic backups of critical files
- **Update Checking**: Monitors for outdated packages
- **Logging**: Comprehensive logging of all auto-fix operations

### How It Works
- Runs automatically when the app starts
- Monitors in the background every hour
- Logs all activities to `auto_fix.log`
- Creates backups in `backups/` directory
- Fixes common issues without human intervention

### Manual Auto-Fix
Run the auto-fix system manually:
```bash
python3 auto_fix.py
```

## Credits

- **Creator**: Giuseppe Alehandro Lemuel
- **Libraries**: Flask, Flask-SocketIO, Cryptography, bcrypt, Werkzeug, Flask-CORS, pytest, requests, schedule, psutil
- **Inspiration**: Modern chat apps like Discord, Slack, WhatsApp with self-healing systems

## License

Open-source. Modify and use freely.

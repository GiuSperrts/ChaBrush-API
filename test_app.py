import pytest
from app import app
import io

@pytest.fixture
def client():
    app.config['TESTING'] = True
    # Clear global data to ensure test isolation
    from app import users, messages, calls, groups, files
    users.clear()
    messages.clear()
    calls.clear()
    groups.clear()
    files.clear()
    with app.test_client() as client:
        yield client

def test_register_user(client):
    response = client.post('/api/register', json={"username": "testuser", "password": "password123"})
    assert response.status_code == 200
    assert "User testuser registered" in response.get_json()["message"]

def test_register_duplicate_user(client):
    client.post('/api/register', json={"username": "testuser", "password": "password123"})
    response = client.post('/api/register', json={"username": "testuser", "password": "password123"})
    assert response.status_code == 400

def test_get_users(client):
    client.post('/api/register', json={"username": "user1", "password": "password123"})
    response = client.get('/api/users')
    assert response.status_code == 200
    assert "user1" in response.get_json()["users"]

def test_send_message(client):
    client.post('/api/register', json={"username": "sender", "password": "password"})
    client.post('/api/register', json={"username": "receiver", "password": "password"})
    response = client.post('/api/send_message', json={"from": "sender", "to": "receiver", "content": "Hello"})
    assert response.status_code == 200
    assert response.get_json() == {"message": "Message sent"}

def test_get_messages(client):
    client.post('/api/register', json={"username": "sender", "password": "password"})
    client.post('/api/register', json={"username": "receiver", "password": "password"})
    client.post('/api/send_message', json={"from": "sender", "to": "receiver", "content": "Hello"})
    response = client.get('/api/messages/receiver')
    assert response.status_code == 200
    messages = response.get_json()["messages"]
    assert len(messages) >= 1
    assert any(msg["from"] == "sender" and msg["content"] == "Hello" for msg in messages)

def test_start_call(client):
    client.post('/api/register', json={"username": "caller", "password": "password"})
    client.post('/api/register', json={"username": "callee", "password": "password"})
    response = client.post('/api/start_call', json={"caller": "caller", "callee": "callee"})
    assert response.status_code == 200
    data = response.get_json()
    assert "call_id" in data
    assert data["status"] == "ringing"

def test_answer_call(client):
    client.post('/api/register', json={"username": "caller", "password": "password"})
    client.post('/api/register', json={"username": "callee", "password": "password"})
    call_response = client.post('/api/start_call', json={"caller": "caller", "callee": "callee"})
    call_id = call_response.get_json()["call_id"]
    response = client.post('/api/answer_call', json={"call_id": call_id})
    assert response.status_code == 200
    assert response.get_json() == {"status": "connected"}

def test_end_call(client):
    client.post('/api/register', json={"username": "caller", "password": "password"})
    client.post('/api/register', json={"username": "callee", "password": "password"})
    call_response = client.post('/api/start_call', json={"caller": "caller", "callee": "callee"})
    call_id = call_response.get_json()["call_id"]
    response = client.post('/api/end_call', json={"call_id": call_id})
    assert response.status_code == 200
    assert response.get_json() == {"message": "Call ended"}

def test_edit_message(client):
    client.post('/api/register', json={"username": "sender", "password": "password"})
    client.post('/api/register', json={"username": "receiver", "password": "password"})
    client.post('/api/send_message', json={"from": "sender", "to": "receiver", "content": "Hello"})
    response = client.post('/api/edit_message', json={"username": "receiver", "message_index": 0, "new_content": "Hello edited"})
    assert response.status_code == 200
    assert "Message edited" in response.get_json()["message"]

def test_delete_message(client):
    client.post('/api/register', json={"username": "sender", "password": "password"})
    client.post('/api/register', json={"username": "receiver", "password": "password"})
    client.post('/api/send_message', json={"from": "sender", "to": "receiver", "content": "Hello"})
    response = client.post('/api/delete_message', json={"username": "receiver", "message_index": 0})
    assert response.status_code == 200
    assert "Message deleted" in response.get_json()["message"]

def test_react_message(client):
    client.post('/api/register', json={"username": "sender", "password": "password"})
    client.post('/api/register', json={"username": "receiver", "password": "password"})
    client.post('/api/send_message', json={"from": "sender", "to": "receiver", "content": "Hello"})
    response = client.post('/api/react_message', json={"username": "receiver", "message_index": 0, "reaction": "👍"})
    assert response.status_code == 200
    assert "Reaction added" in response.get_json()["message"]

def test_mark_read(client):
    client.post('/api/register', json={"username": "sender", "password": "password"})
    client.post('/api/register', json={"username": "receiver", "password": "password"})
    client.post('/api/send_message', json={"from": "sender", "to": "receiver", "content": "Hello"})
    response = client.post('/api/mark_read', json={"username": "receiver", "message_index": 0})
    assert response.status_code == 200
    assert "Message marked as read" in response.get_json()["message"]

def test_user_profile(client):
    client.post('/api/register', json={"username": "testuser", "password": "password"})
    # Test GET profile
    response = client.get('/api/user_profile/testuser')
    assert response.status_code == 200
    assert "profile" in response.get_json()
    # Test POST profile
    response = client.post('/api/user_profile/testuser', json={"bio": "Test bio", "avatar": "test.jpg"})
    assert response.status_code == 200
    assert "Profile updated" in response.get_json()["message"]

def test_batch_send(client):
    client.post('/api/register', json={"username": "sender", "password": "password"})
    client.post('/api/register', json={"username": "receiver", "password": "password"})
    messages = [
        {"from": "sender", "to": "receiver", "content": "Message 1"},
        {"from": "sender", "to": "receiver", "content": "Message 2"}
    ]
    response = client.post('/api/batch_send', json={"messages": messages})
    assert response.status_code == 200
    results = response.get_json()["results"]
    assert len(results) == 2
    assert all("Sent" in result.get("message", "") for result in results)

def test_create_group(client):
    client.post('/api/register', json={"username": "creator", "password": "password"})
    response = client.post('/api/create_group', json={"group_name": "testgroup", "creator": "creator"})
    assert response.status_code == 200
    assert "Group testgroup created" in response.get_json()["message"]

def test_join_group(client):
    client.post('/api/register', json={"username": "creator", "password": "password"})
    client.post('/api/register', json={"username": "member", "password": "password"})
    client.post('/api/create_group', json={"group_name": "testgroup", "creator": "creator"})
    response = client.post('/api/join_group', json={"group_name": "testgroup", "username": "member"})
    assert response.status_code == 200
    assert "joined group testgroup" in response.get_json()["message"]

def test_send_group_message(client):
    client.post('/api/register', json={"username": "sender", "password": "password"})
    client.post('/api/create_group', json={"group_name": "testgroup", "creator": "sender"})
    response = client.post('/api/send_group_message', json={"group_name": "testgroup", "from": "sender", "content": "Group hello"})
    assert response.status_code == 200
    assert "Group message sent" in response.get_json()["message"]

def test_get_group_messages(client):
    client.post('/api/register', json={"username": "sender", "password": "password"})
    client.post('/api/create_group', json={"group_name": "testgroup", "creator": "sender"})
    client.post('/api/send_group_message', json={"group_name": "testgroup", "from": "sender", "content": "Group hello"})
    response = client.get('/api/get_group_messages/testgroup')
    assert response.status_code == 200
    messages = response.get_json()["messages"]
    assert len(messages) >= 1

def test_upload_download_file(client):
    client.post('/api/register', json={"username": "uploader", "password": "password"})
    # Create a test file
    test_file_content = b"Test file content"
    file_obj = io.BytesIO(test_file_content)
    file_obj.name = 'test.txt'
    response = client.post('/api/upload_file',
                          data={"username": "uploader", "file": (file_obj, 'test.txt')})
    assert response.status_code == 200
    file_id = response.get_json()["file_id"]
    # Download the file
    response = client.get(f'/api/download_file/{file_id}')
    assert response.status_code == 200
    assert response.data == test_file_content

def test_logout(client):
    client.post('/api/register', json={"username": "testuser", "password": "password"})
    response = client.post('/api/logout', json={"username": "testuser"})
    assert response.status_code == 200
    assert "logged out" in response.get_json()["message"]

def test_login_logout_flow(client):
    # Register
    client.post('/api/register', json={"username": "flowuser", "password": "password"})
    # Login
    response = client.post('/api/login', json={"username": "flowuser", "password": "password"})
    assert response.status_code == 200
    assert "logged in" in response.get_json()["message"]
    # Logout
    response = client.post('/api/logout', json={"username": "flowuser"})
    assert response.status_code == 200
    assert "logged out" in response.get_json()["message"]

def test_message_encryption(client):
    client.post('/api/register', json={"username": "alice", "password": "password"})
    client.post('/api/register', json={"username": "bob", "password": "password"})
    client.post('/api/send_message', json={"from": "alice", "to": "bob", "content": "Secret message"})
    response = client.get('/api/messages/bob')
    assert response.status_code == 200
    messages = response.get_json()["messages"]
    assert len(messages) >= 1
    # Verify message is decrypted properly
    assert any("Secret message" in msg["content"] for msg in messages)

def test_validation_errors(client):
    # Test short username
    response = client.post('/api/register', json={"username": "ab", "password": "password"})
    assert response.status_code == 400
    # Test short password
    response = client.post('/api/register', json={"username": "testuser", "password": "123"})
    assert response.status_code == 400
    # Test missing fields
    response = client.post('/api/send_message', json={"from": "test"})
    assert response.status_code == 400

def test_duplicate_registration(client):
    client.post('/api/register', json={"username": "duplicate", "password": "password"})
    response = client.post('/api/register', json={"username": "duplicate", "password": "password"})
    assert response.status_code == 400

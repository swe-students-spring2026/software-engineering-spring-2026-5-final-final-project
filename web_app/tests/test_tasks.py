import pytest
import mongomock
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash
from app import app
import app as app_module
from routes.auth import auth_bp
from routes.tasks import tasks_bp, to_object_id, parse_datetime_local_to_utc


@pytest.fixture
def client():
    app.config['TESTING'] = True
    
    mock_db = mongomock.MongoClient().db
    
    tasks_bp.db = mock_db
    auth_bp.db = mock_db
    app_module.db = mock_db
    
    user_id_str = "507f1f77bcf86cd799439011"
    mock_db.users.insert_one({
        "_id": ObjectId(user_id_str),
        "username": "testuser",
        "password": generate_password_hash("secret123", method='pbkdf2:sha256'),
        "email": "testuser@example.com"
    })

    mock_db.tasks.insert_one({
        "_id": ObjectId("607f1f77bcf86cd799439011"),
        "user_id": user_id_str,
        "title": "Existing Test Task",
        "completed": False
    })

    with app.test_client() as client:
        client.post('/login', data={'username': 'testuser', 'password': 'secret123'})
        yield client

def test_to_object_id_valid():
    """Test that a valid 24-character hex string converts to an ObjectId"""
    result = to_object_id("607f1f77bcf86cd799439011")
    assert isinstance(result, ObjectId)

def test_to_object_id_invalid():
    """Test that an invalid string gracefully returns None (Invalid input)"""
    result = to_object_id("invalid-id-string")
    assert result is None

def test_parse_datetime_valid():
    """Test that a standard datetime string converts correctly to UTC"""
    result = parse_datetime_local_to_utc("2026-05-04T15:30")
    assert result is not None
    assert result.tzinfo is not None 
def test_parse_datetime_empty():
    """Test that missing datetime input returns None"""
    assert parse_datetime_local_to_utc("") is None


def test_show_tasks(client):
    """Test that the index route successfully loads the tasks"""
    response = client.get('/')
    assert response.status_code == 200
    
def test_create_task_page_loads(client):
    """Test that the create task form loads on a GET request"""
    response = client.get('/tasks/create')
    assert response.status_code == 200

def test_create_task_post(client):
    """Test successfully creating a new task and inserting it into the mock DB"""
    response = client.post('/tasks/create', data={
        'title': 'Learn Pytest',
        'next_reminder_at': '2026-05-10T10:00',
        'reminder_enabled': 'on',
        'reminder_repeat': 'on',
        'repeat_every': '1',
        'repeat_unit': 'days'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    saved_task = tasks_bp.db.tasks.find_one({"title": "Learn Pytest"})
    assert saved_task is not None
    assert saved_task["reminder_enabled"] is True
    assert saved_task["repeat_every"] == 1

def test_delete_task_success(client):
    """Test deleting an existing task successfully"""
    response = client.post('/tasks/607f1f77bcf86cd799439011/delete', follow_redirects=True)
    assert response.status_code == 200
    
    deleted_task = tasks_bp.db.tasks.find_one({"_id": ObjectId("607f1f77bcf86cd799439011")})
    assert deleted_task is None

def test_delete_task_invalid_id(client):
    """Test that submitting an incorrectly formatted ID returns a 400 Error"""
    response = client.post('/tasks/not-a-real-id/delete')
    assert response.status_code == 400
    assert b"Invalid task id" in response.data

def test_delete_task_not_found(client):
    """Test that submitting a valid ID that doesn't exist in the DB returns a 404 Error"""
    response = client.post('/tasks/507f1f77bcf86cd799439022/delete')
    assert response.status_code == 404
    assert b"Task not found" in response.data

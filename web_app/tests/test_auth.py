import pytest
import mongomock
from werkzeug.security import generate_password_hash
from app import app  
import app as app_module  # ADD THIS: Import the module to overwrite its variables
from routes.auth import auth_bp

@pytest.fixture
def client():
    app.config['TESTING'] = True
    mock_db = mongomock.MongoClient().db
    
    auth_bp.db = mock_db
    app_module.db = mock_db 
    
    mock_db.users.insert_one({
        "username": "testuser",
        "password": generate_password_hash("secret123", method='pbkdf2:sha256'),
        "email": "testuser@example.com"
    })

    with app.test_client() as client:
        yield client


def test_register_page_loads(client):
    """Test that the registration page successfully loads on a GET request"""
    response = client.get('/register')
    assert response.status_code == 200

def test_register_new_user(client):
    """Test successful registration of a new user via POST"""
    response = client.post('/register', data={
        'username': 'newuser',
        'password': 'newpassword',
        'email': 'new@example.com'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Login" in response.data  # Redirected to login page
    
    saved_user = auth_bp.db.users.find_one({"username": "newuser"})
    assert saved_user is not None

def test_register_existing_user(client):
    """Test registration fails if the username is already taken (invalid input)"""
    response = client.post('/register', data={
        'username': 'testuser', 
        'password': 'somepassword',
        'email': 'duplicate@example.com'
    }, follow_redirects=False)
    
    assert response.status_code == 302  # Redirect back to register
    assert response.headers['Location'] == '/register'
    """Test that the login page successfully loads on a GET request"""
    response = client.get('/login')
    assert response.status_code == 200

def test_login_success(client):
    """Test successful login with correct credentials"""
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'secret123'
    }, follow_redirects=True)
    
    assert response.status_code == 200

def test_login_failure(client):
    """Test failed login with incorrect password (invalid input)"""
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'wrongpassword'
    }, follow_redirects=False)
    
    assert response.status_code == 302  # Redirect back to login
    assert response.headers['Location'] == '/login'

def test_logout(client):
    """Test logging out an authenticated user"""
    client.post('/login', data={'username': 'testuser', 'password': 'secret123'})
    
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
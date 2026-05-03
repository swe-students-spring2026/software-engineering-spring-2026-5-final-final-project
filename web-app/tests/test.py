import app
def client(): 
    app.app.config["TESTING"] = True 
    with app.app.test_client() as client: 
         yield client


def test_register_empty_fields(client):
    response=client.post("/register",data={
        "username":"",
        "email":"",
        "password":""
    })
    assert response.status_code==302
    assert "/register" in response.location
def test_register_username_exists(client,monkeypatch):
     test_user={
          "_id":"userId123",
          "username":"rehan",
          "email":"rehang2005@gmail.com",
          "password":"Rehan123@2005"
     }
     monkeypatch.setattr(
          "app.find_user_by_username",lambda username:test_user
     )
     response=client.post("/register",data={
          "username":"rehan",
          "email":"rehang2005@gmail.com",
          "password":"Rehan123@2005"
     })
     assert response.status_code==302
     assert "/register" in response.location
def test_register_new_username(client,monkeypatch):
     test_user={
          "_id":"userId123",
          "username":"rehan",
          "email":"rehang2005@gmail.com",
          "password":"Rehan123@2005"
     }
     monkeypatch.setattr(
          "app.find_user_by_username",lambda username:None
     )
     
     monkeypatch.setattr(
          "app.insert_user",
          lambda username, email, hashed_password:"userid123"
     )
     monkeypatch.setattr(
          "app.find_user_by_id",lambda user_id: test_user
     )
     response=client.post("/register",data={
          "username":"rehan",
          "email":"rehang2005@gmail.com",
          "password":"Rehan123@2005"
     })
     assert response.status_code==302
     assert "/dashboard" in response.location
def test_login(client):
     response=client.get("/login")
     assert response.status_code == 200
def test_login_username_not_found(client,monkeypatch):
     test_user={
          "_id":"userId123",
          "username":"rehan",
          "email":"rehang2005@gmail.com",
          "password":"Rehan123@2005"
     }
     monkeypatch.setattr(
          "app.find_user_by_username",lambda username:None
     )
     response=client.post("/login",data={
          "username":"rehan",
          "email":"rehang2005@gmail.com",
          "password":"Rehan123@2005"
     })
     assert response.status_code==302
     assert "/login" in response.location
def test_login_wrong_password(client,monkeypatch):
     test_user={
          "_id":"userId123",
          "username":"rehan",
          "email":"rehang2005@gmail.com",
          "password":"Rehan123@2005"
     }
     monkeypatch.setattr(
          "app.find_user_by_username",lambda username:test_user
     )
     monkeypatch.setattr(
          "app.bcrypt.check_password_hash",lambda hashed_password, password:False 
     )
     response=client.post("/login",data={
          "username":"rehan",
          "password":"pass123"
     })
     assert response.status_code == 302
     assert "/login" in response.location
def test_login_successful(client,monkeypatch):
     test_user={
          "_id":"userId123",
          "username":"rehan",
          "email":"rehang2005@gmail.com",
          "password":"Rehan123@2005"
     }
     monkeypatch.setattr(
          "app.find_user_by_username",lambda username:test_user
     )
     monkeypatch.setattr(
          "app.bcrypt.check_password_hash",lambda hashed_password, password:True
     )
     response=client.post("/login",data={
          "username":"rehan",
          "password":"Rehan123@2005"
     })
     assert response.status_code == 302
     assert "/dashboard" in response.location

def test_register(client):
     response=client.get("/register")
     assert response.status_code==200

def test_register_empty_fields(client):
    response=client.post("/register",data={
        "username":"",
        "email":"",
        "password":""
    })
    assert "/register" in response.location
def test_register_username_exists(client,monkeypatch):
     monkeypatch.setattr(
          "app.find_user_by_username",lambda username:{"username":username}
     )
     response=client.post("/register",data={
          "username":"rehan",
          "email":"rehang2005@gmail.com",
          "password":"Rehan123@2005"
     })
     assert response.status_code==302
     assert "/register" in response.location
def test_register_new_username(client,monkeypatch):
     fakeUser={
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
          "app.find_user_by_id",lambda user_id: fakeUser
     )
     response=client.post("/register",data=fakeUser)
     assert response.status_code==302
     assert "/dashboard" in response.location

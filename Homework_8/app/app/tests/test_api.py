from fastapi.testclient import TestClient
from sqlmodel import Session
from unittest.mock import patch, MagicMock
from models.user import User
from models.event import Event
from api import app
from auth.authenticate import authenticate
from decimal import Decimal
from services.crud import event as EventService
import io

client = TestClient(app)

def test_home_request(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_get_users(client: TestClient):
    response = client.get("/api/users/")
    assert response.status_code == 200
    assert response.json() == []    

def test_signup_web(client: TestClient):    
    app.dependency_overrides.pop(authenticate, None)
    user = {
        "username": "test_user@gmail.com",
        "password": "password"
    }
    response = client.post("/auth/signup", data = user)   
    print(response.text)
    assert response.status_code == 200
    assert f"Created new user: {user['username']}. Please, login" in response.text

def test_login_web(client: TestClient, session: Session):
    user = User(
        email = "test_user@gmail.com", 
        password = "test_user@gmail.com")
    session.add(user)
    session.commit()
    app.dependency_overrides.pop(authenticate, None) 
    user_login = {
        "username": user.email,
        "password": user.password
    }
    response = client.post("/auth/login", data = user_login)    
    print(response.text)
    assert response.status_code == 200

    
def test_get_events(client: TestClient):
    response = client.get("/api/events/")
    assert response.status_code == 200
    assert response.json() == []


def test_signup_success(client: TestClient):
    new_user = {"email": "test_user@test.com", "password": "test_user"}
    response = client.post("/api/users/signup", json=new_user)
    
    assert response.status_code == 201
    assert response.json() == {"message": "User successfully registered"}

def test_signup_duplicate_email(client: TestClient):
    new_user = {"email": "test_user@test.com", "password": "test_user"}
    client.post("/api/users/signup", json = new_user)
    response = client.post("/api/users/signup", json = new_user)    
    assert response.status_code == 409
    assert response.json() == {"detail": "User with this email already exists"}

def test_signin_success(client: TestClient):
    new_user = {"email": "test_user@test.com", "password": "test_user"}
    client.post("/api/users/signup", json = new_user)
    response = client.post("/api/users/signin", json = new_user)    
    assert response.status_code == 200
    assert response.json()["message"] == "User signed in successfully"

def test_signin_wrong_password(client: TestClient):
    new_user = {"email": "test_user@test.com", "password": "test_user"}
    test_user = {"email": "test_user@test.com", "password": "test_user2"}
    client.post("/api/users/signup", json = new_user)    
    response = client.post("/api/users/signin", json = test_user)    
    assert response.status_code == 403
    assert response.json()["detail"] == "Wrong credentials passed" 

def test_signin_non_existent_user(client: TestClient):
    user = {"email": "test_user1@gmail.com", "password": "test_user1@gmail.com"}
    response = client.post("/api/users/signin", json = user)    
    assert response.status_code == 404
    assert response.json()["detail"] == "User does not exist"


def test_get_balance(client: TestClient):
    """Check that new user has 0.0 balance"""
    new_user = {"email": "test_user@test.com", "password": "test_user"}
    response = client.post("/api/users/signup", json=new_user)
    user_data = client.get(f"/api/users/email/{new_user['email']}")
    assert user_data.status_code == 200
    user_id = user_data.json()["id"]
    response = client.get(f"/api/wallets/{user_id}")
    assert response.status_code == 200
    balance = Decimal(str(response.json()))
    assert balance == Decimal("0.0")

def test_topup_balance(client: TestClient):
    new_user = {"email": "test_user@test.com", "password": "test_user"}
    response = client.post("/api/users/signup", json=new_user)
    user_data = client.get(f"/api/users/email/{new_user['email']}")
    assert user_data.status_code == 200
    user_id = user_data.json()["id"]
    topup_amount = Decimal("10.0")
    response = client.get(f"/api/wallets/{user_id}")
    balance_before = Decimal(str(response.json()))
    topup_data = {
        "user_id": user_id, 
        "amount": float(topup_amount)}
    response_topup = client.post("/api/wallets/topup", params=topup_data)    
    assert response_topup.status_code == 200
    assert response_topup.json()["message"] == "Topup made successfully"
    response_after = client.get(f"/api/wallets/{user_id}")
    balance_after = Decimal(str(response_after.json()))
    assert balance_after == balance_before + topup_amount

def test_retrieve_wallet_not_found(client: TestClient):
    user_id = 123
    user_data = client.get(f"/api/users/user/{user_id}")
    assert user_data.status_code == 404
    assert user_data.json()["detail"] == "User_ID doesn't exist"
    response = client.get(f"/api/wallets/{user_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == f"Wallet for user {user_id} not found"

def test_get_user_by_id(client: TestClient):
    new_user = {"email": "test_user@test.com", "password": "test_user"}
    response = client.post("/api/users/signup", json=new_user)
    user_data = client.get(f"/api/users/email/{new_user['email']}")
    assert user_data.status_code == 200
    user_id = user_data.json()["id"]    
    response = client.get(f"/api/users/user/{user_id}")
    assert response.status_code == 200
    assert response.json()["email"] == new_user['email']


def test_upload_image(client: TestClient):
    new_user = {"email": "test_user@test.com", "password": "test_user"}
    response = client.post("/api/users/signup", json=new_user)
    user_data = client.get(f"/api/users/email/{new_user['email']}")
    assert user_data.status_code == 200
    user_id = user_data.json()["id"] 
    client.post("/api/wallets/topup", params={"user_id": user_id, "amount": 10.0})
    file_name = "test_photo.jpg"
    file_content = b"test_image_data"
    file_obj = io.BytesIO(file_content)
    file_data = {"file": (file_name, io.BytesIO(file_content), "image/jpeg")}
    with patch("services.rm.rm.send_task") as mock_send:
        mock_send.return_value = True            
        response = client.post(
            "/api/events/upload_image/",
            params={"creator_id": user_id},
            files=file_data
        )
        assert response.status_code == 200
        assert "event_id" in response.json()
        assert mock_send.called 

def test_upload_image_invalid_extension(client):
    user_id = 1
    file_obj = io.BytesIO(b"this is a text file")
    response = client.post(
        "/api/events/upload_image/",
        params={"creator_id": user_id},
        files={"file": ("test.txt", file_obj, "text/plain")}
    )    
    assert response.status_code == 400
    assert response.json()["detail"] == "File must be an image"


def test_ml_workflow_billing_and_history(client):
    new_user = {"email": "test_user@test.com", "password": "test_user"}
    client.post("/api/users/signup", json=new_user)
    user_id = client.get(f"/api/users/email/{new_user["email"]}").json()["id"]
    client.post("/api/wallets/topup", params={"user_id": user_id, "amount": 10.0})
    balance_before = Decimal(str(client.get(f"/api/wallets/{user_id}").json()))
    with patch("services.rm.rm.send_task") as mock_rm:
        file_data = {"file": ("test.jpg", io.BytesIO(b"binarydata"), "image/jpeg")}
        response = client.post(
            "/api/events/upload_image/", 
            params={"creator_id": user_id}, 
            files=file_data
        )    
    assert response.status_code == 200
    event_id = response.json()["event_id"]
    balance_after = Decimal(str(client.get(f"/api/wallets/{user_id}").json()))
    assert balance_after == balance_before - Decimal("0.01")
    event_resp = client.get(f"/api/events/{event_id}") 
    assert event_resp.status_code == 200
    assert event_resp.json()["creator_id"] == user_id
    history_resp = client.get(f"/api/transactions/{user_id}")
    if history_resp.status_code == 200:
        assert len(history_resp.json()) >= 2  

def test_ml_upload_fails_with_zero_balance(client):
    new_user = {"email": "test_user@test.com", "password": "test_user"}
    client.post("/api/users/signup", json=new_user)
    user_data = client.get(f"/api/users/email/{new_user["email"]}").json()
    user_id = user_data["id"]
    balance_resp = client.get(f"/api/wallets/{user_id}")
    assert Decimal(str(balance_resp.json())) == Decimal("0.0")
    with patch("services.rm.rm.send_task") as mock_rm:
        file_data = {"file": ("test.jpg", io.BytesIO(b"binarydata"), "image/jpeg")}
        response = client.post(
            "/api/events/upload_image/", 
            params={"creator_id": user_id}, 
            files=file_data
        )    
    assert response.status_code == 400 
    assert ("Insufficient funds" in response.json()["detail"] 
    or "balance" in response.json()["detail"].lower())
    assert not mock_rm.called



"""
def test_get_event(client: TestClient):
    event_data = {
        "id": 1,
        "title": "title",
        "image": "img",
        "description": "description",
        "creator_id": 1, 
        "status": "Success",
        "prediction":"Kolibri"
    }
    
    response = client.get("/api/events/1/")
    
    print(response.json())
    
    assert response.status_code == 200
    assert response.json() == event_data

def test_get_transactions(client: TestClient):
    response = client.get("/api/transactions/")
    assert response.status_code == 200
    assert response.json() == [] 
"""

"""
def test_clear_events(client: TestClient):
    response = client.delete("/api/events/")
    
    assert response.status_code == 200
    assert response.json() == {"message": "Events deleted successfully"}
 

def test_delete_event(client: TestClient):
    response = client.get("/api/events/")
    
    assert response.status_code == 200
    assert response.json() == []
"""

import json
from datetime import datetime, timedelta, timezone

import jwt

from backend.app.config import JWT_SECRET_KEY, DATASET_DIR


# 1. Create a JWT token for a logged-in user
def create_access_token(username: str) -> str:

    # Token expires after 30 minutes
    expiry = datetime.now(timezone.utc) + timedelta(minutes=30)

    # Information stored inside the token
    payload = {
        "sub": username,
        "exp": expiry
    }

    # Sign the token using our secret key
    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm="HS256"
    )

    return token


# 2. Verify a JWT token
def verify_access_token(token: str) -> dict:

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=["HS256"]
        )

        return payload

    except jwt.InvalidTokenError:
        raise ValueError("Invalid or expired token")


# 3. Authenticate a user using username and password
def authenticate_user(username: str, password: str):

    users_file = DATASET_DIR / "users_seed.json"

    with open(users_file, "r", encoding="utf-8") as file:
        users = json.load(file)

    for user in users:
        if (
            user["username"] == username
            and user["password"] == password
        ):
            return {
                "username": user["username"],
                "name": user["display_name"],
                "role": user["role"],
                "matters": user["matters"]
            }

    return None


# 4. Retrieve a user's profile using their username
def get_user_by_username(username: str):

    users_file = DATASET_DIR / "users_seed.json"

    with open(users_file, "r", encoding="utf-8") as file:
        users = json.load(file)

    for user in users:
        if user["username"] == username:
            return {
                "username": user["username"],
                "name": user["display_name"],
                "role": user["role"],
                "matters": user["matters"]
            }

    return None

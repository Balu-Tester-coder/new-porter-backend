from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, Query, APIRouter
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from bson.objectid import ObjectId
from pydantic import BaseModel, Field
from urllib.parse import quote_plus
import secrets
from enum import Enum
from jose import jwt, JWTError
import os
from dotenv import load_dotenv
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import re

# Load environment variables from .env
load_dotenv()

router = APIRouter(tags=["Login"], prefix="/login")

# Manually generated client ID and secret for testing
client_id = "0dca7914-3cbc-4bdf-98c4-acff6b81ab0a"
client_secret = "1eomsgiNL0S0UwH2Eqbvw5TK1SJ15r9oLxn0o4fkZ0A"

# Database setup
username_name = quote_plus(str("bala"))
password_password = quote_plus(str("bala123"))

DATABASE_URL = f"mongodb+srv://bala:bala123@cluster0.0z8bodb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Initialize client
client = MongoClient(DATABASE_URL)

# Specify your database name
DATABASE_NAME = "Attendence"
db = client[DATABASE_NAME]
users_collection = db['users']

# Try to get SECRET_KEY from environment variable
SECRET_KEY = os.environ.get("SECRET_KEY")

# If SECRET_KEY is not set, generate a new one
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    print(f"Generated SECRET_KEY: {SECRET_KEY}")

# Authentication setup
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 18000000

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login/login")

pwd_context = CryptContext(schemes=["bcrypt"], default="bcrypt")

class User(BaseModel):
    username: str
    email: str
    password: str
    employee_id: Optional[int] = None
    is_active: Optional[bool] = False

class UserInDB(User):
    hashed_password: str

# Helper function to get user from database with improved robustness
def get_user(username: str):
    if not username:
        return None
        
    # Normalize the username: lowercase and strip whitespace
    normalized_username = username.lower().strip()
    
    try:
        # Try direct lookup first
        user = users_collection.find_one({"username": normalized_username})
        
        # If not found, try case-insensitive regex search as fallback
        if not user:
            regex_pattern = re.compile(f"^{re.escape(normalized_username)}$", re.IGNORECASE)
            user = users_collection.find_one({"username": regex_pattern})
            
        return user
    except Exception as e:
        print(f"Error in get_user: {e}")
        return None

# Helper function to authenticate user
def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not pwd_context.verify(password, user["hashed_password"]):
        return False
    return user

# Helper function to create access token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/register/")
async def register(user: User):
    # Normalize username
    normalized_username = user.username.lower().strip()
    
    # Check if user already exists (case insensitive)
    existing_user = get_user(normalized_username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Hash the password
    hashed_password = pwd_context.hash(user.password)
    
    # Create user document including employee_id field
    user_data = {
        "username": normalized_username,
        "email": user.email,
        "hashed_password": hashed_password,
        
        "is_active": False  # Initialize as inactive
    }
    
    # Add employee_id field if provided
    if user.employee_id is not None:
        user_data["employee_id"] = user.employee_id
    
    # Insert new user
    users_collection.insert_one(user_data)
    
    return {"msg": "User registered successfully"}

@router.post("/login/")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Normalize username
    username = form_data.username.lower().strip()
    
    # Authenticate user
    user = authenticate_user(username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Set user to active
    users_collection.update_one(
        {"username": username},
        {"$set": {"is_active": True}}
    )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout/")
async def logout(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exception
    
    # Set user to inactive
    result = users_collection.update_one(
        {"username": username},
        {"$set": {"is_active": False}}
    )
    
    if result.modified_count == 0:
        return {"msg": "User not found or already logged out"}
    
    return {"msg": "User logged out successfully"}

@router.get("/users/me")
async def read_users_me(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    user = get_user(username)
    
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Prepare response with basic user info
    response = {
        "username": user["username"],
        "email": user["email"],
        "is_active": user.get("is_active", False),
        
    }
    
    # Add employee_id to response if it exists
    if "employee_id" in user:
        response["employee_id"] = user["employee_id"]
    
    return response

# Add a debug endpoint to check if a user exists
@router.get("/check-user/{username}")
async def check_user_exists(username: str):
    user = get_user(username)
    if user:
        return {"exists": True, "username": user["username"], "is_active": user.get("is_active", False)}
    else:
        return {"exists": False}
    



@router.get("/allUsers")
def get_all_users():
    users = list(users_collection.find({})) # Convert Cursor to list
    for user in users:
        user["_id"] = str(user["_id"])
    return {"tasks": users}
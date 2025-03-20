from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query, Path, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson.objectid import ObjectId
from pydantic import BaseModel
from datetime import datetime
from urllib.parse import quote_plus
from typing import List, Optional, Dict
import shutil
import os
import uuid
from fastapi.staticfiles import StaticFiles

# Create 'uploads' directory if it doesn't exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Database and CORS setup
username_name = quote_plus("bala")
password_password = quote_plus("bala123")
DATABASE_URL = f"mongodb+srv://{username_name}:{password_password}@cluster0.0z8bodb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(DATABASE_URL)
db = client.Calender
stores_collection = db.stories


router = APIRouter(tags=["Calender"], prefix="/calender")

# Mount static files for serving uploaded files
router.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# APIRouter setup
router = APIRouter(tags=["Calender"], prefix="/calender")

class StoriesIn(BaseModel):
    title: str

@router.post("/")
async def create_story(title: str = Form(...), file: UploadFile = File(...)):
    try:
        # Generate a unique filename
        file_location = f"uploads/{quote_plus(file.filename)}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        image_url = f"http://localhost:8000/uploads/{quote_plus(file.filename)}"
        
        # Prepare document for MongoDB
        story_doc = {
            "title": title,
            "image": image_url,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Insert into database
        result = stores_collection.insert_one(story_doc)
        
        story_doc["_id"] = str(result.inserted_id)
        
        return {"message": "Story uploaded successfully", "data": story_doc}
        
       

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload story: {str(e)}")





@router.get("/")
def get_stories(year: int = Query(None, description="Filter by year")):
    try:
        # Define the query
        query = {}
        if year:
            query = {
                "created_at": {
                    "$gte": f"{year}-01-01T00:00:00",
                    "$lt": f"{year + 1}-01-01T00:00:00"
                }
            }

        # Find documents based on the query
        stories = list(stores_collection.find(query))

        # Convert ObjectId to string and format date
        for story in stories:
            story["_id"] = str(story["_id"])
            story["created_at"] = datetime.fromisoformat(story["created_at"]).strftime('%Y-%m-%d')

        # Get distinct years from the collection for the dropdown
        distinct_years = stores_collection.distinct("created_at")
        years = sorted({datetime.fromisoformat(date).year for date in distinct_years})

        return {"data": stories, "years": years}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stories: {str(e)}")
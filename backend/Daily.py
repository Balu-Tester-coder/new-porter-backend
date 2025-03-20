from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from bson.objectid import ObjectId
from pydantic import BaseModel, Field
from urllib.parse import quote_plus
from enum import Enum

# Database setup
username_name = quote_plus("bala")
password_password = quote_plus("bala123")
DATABASE_URL = f"mongodb+srv://{username_name}:{password_password}@cluster0.0z8bodb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(DATABASE_URL)
db = client["TitleDB"]
collection = db["titles"]

router = APIRouter(tags=["Daily"], prefix="/daily")

class LanguageEnum(int, Enum):
    ENGLISH = 1
    TELUGU = 2
    HINDI = 3
    TAMIL = 4

class Title(BaseModel):
    id: str
    text: str
    language_id: LanguageEnum
    created_at: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    daily: bool = False
    weekly: bool = False
    monthly: bool = False
    date_specific: bool = False
    weekdays: Optional[List[int]] = None
    specific_date: Optional[datetime] = None

class TitleCreate(BaseModel):
    text: str
    language_id: LanguageEnum
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    daily: bool = False
    weekly: bool = False
    monthly: bool = False
    date_specific: bool = False
    weekdays: Optional[List[int]] = None
    specific_date: Optional[datetime] = None

def create_title_from_document(title: dict) -> Title:
    language_id = title.get("language_id")
    if language_id:
        language_id = LanguageEnum(language_id)
    else:
        language_id = None
    
    return Title(
        id=str(title["_id"]),
        text=title["text"],
        language_id=language_id,
        created_at=title["created_at"],
        start_time=title.get("start_time"),
        end_time=title.get("end_time"),
        daily=title.get("daily", False),
        weekly=title.get("weekly", False),
        monthly=title.get("monthly", False),
        date_specific=title.get("date_specific", False),
        weekdays=title.get("weekdays"),
        specific_date=title.get("specific_date")
    )

@router.post("/titles/recurring", response_model=Title)
def create_recurring_title(
    title: TitleCreate,
    frequency: str = Query(..., enum=["daily", "weekly", "monthly", "date_specific"]),
):
    new_title = title.dict()
    new_title["created_at"] = datetime.now()

    new_title["text"] = title.text 
    new_title["start_time"] = title.start_time
    new_title["end_time"] = title.end_time
    new_title["specific_date"] = title.specific_date

    new_title["daily"] = False
    new_title["weekly"] = False
    new_title["monthly"] = False
    new_title["date_specific"] = False  
    
    if frequency == "daily":
        new_title["daily"] = True
    elif frequency == "weekly":
        new_title["weekly"] = True
    elif frequency == "monthly":
        new_title["monthly"] = True
    elif frequency == "date_specific":
        new_title["date_specific"] = True  
        new_title["specific_date"] = title.specific_date

    try:
        result = collection.insert_one(new_title)
        new_title["id"] = str(result.inserted_id)
        return create_title_from_document(new_title)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create title.")

@router.get("/titles/", response_model=List[Title])
def get_titles(
    frequency: Optional[str] = Query(None, enum=["all", "daily", "weekly", "monthly", "date_specific"]),
    date: Optional[str] = None,  # For date-specific titles
    language_id: Optional[LanguageEnum] = Query(None),  # For filtering by language
):
    query = {}
    today = datetime.now()

    if frequency == "all":
        titles = list(collection.find({"language_id": language_id}))  # Retrieve all documents language_id wise
    else:
        if frequency == "daily":
            query["daily"] = True
        elif frequency == "weekly":
            query["weekly"] = True
        elif frequency == "monthly":
            query["monthly"] = True
        elif frequency == "date_specific":
            if date:
                try:
                    date_obj = datetime.strptime(date, "%Y-%m-%d")
                    date_obj_end = date_obj + timedelta(days=1)
                    query = {
                        "$and": [
                            {"date_specific": True},
                            {
                                "created_at": {
                                    "$gte": date_obj,
                                    "$lt": date_obj_end
                                }
                            }
                        ]
                    }
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
            else:
                # If no date is provided, return titles from the last day where date_specific is True
                yesterday = today - timedelta(days=1)
                query = {
                    "$and": [
                        {"date_specific": True},
                        {
                            "created_at": {
                                "$gte": yesterday,
                                "$lt": today
                            }
                        }
                    ]
                }

        if language_id:
            query["language_id"] = language_id

        titles = list(collection.find(query))  # Fetch results based on query

    return [create_title_from_document(title) for title in titles]


@router.delete("/titles/{title_id}", response_model=dict)
def delete_title(title_id: str):
    """
    Delete a title by its ID.
    """
    if not ObjectId.is_valid(title_id):
        raise HTTPException(status_code=400, detail="Invalid title ID format.")
    
    result = collection.delete_one({"_id": ObjectId(title_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Title not found.")
    
    return {"message": "Title deleted successfully."}



@router.put("/titles/{title_id}", response_model=Title)
def update_title(title_id: str, title_data: TitleCreate):
    """
    Update a title by its ID.
    """
    if not ObjectId.is_valid(title_id):
        raise HTTPException(status_code=400, detail="Invalid title ID format.")
    
    update_data = {k: v for k, v in title_data.dict().items() if v is not None}
    
    result = collection.update_one({"_id": ObjectId(title_id)}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Title not found.")
    
    updated_title = collection.find_one({"_id": ObjectId(title_id)})
    return create_title_from_document(updated_title)

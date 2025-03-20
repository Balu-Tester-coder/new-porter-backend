from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId, errors
from typing import List, Optional
from datetime import datetime
from pymongo import MongoClient
from urllib.parse import quote_plus
from enum import Enum
import os
from uuid import uuid4
from pathlib import Path

# MongoDB Configuration
username = quote_plus("bala")
password = quote_plus("bala123")
DATABASE_URL = f"mongodb+srv://{username}:{password}@cluster0.0z8bodb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "Dashboard"
COLLECTION_NAME = "statistics"

# Initialize MongoDB connection
client = MongoClient(DATABASE_URL)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]





# Create router
router = APIRouter(tags=["Dashboard"], prefix="/dashboard")

# Enums
class Status(str, Enum):
    REJECTED = "rejected"
    DRAFT = "draft"
    PUBLISHED = "published"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class RejectReason(str, Enum):
    DUPLICATE = "Duplicate"
    IRRELEVANT = "Irrelevant"
    INACCURATE = "Inaccurate"
    VIOLATES_GUIDELINES = "Violates Guidelines"
    COPYRIGHT_ISSUE = "Copyright Issue"
    LOW_QUALITY = "Low Quality"
    SENSITIVE_CONTENT = "Sensitive Content"
    ADVERTISEMENT = "Advertisement"
    LACKS_VERIFIABLE_SOURCE = "Lacks Verifiable Source"
    SPAM = "Spam"

# Models
class DashboardItemBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    status: Status = Field(default=Status.DRAFT)
    priority: Priority = Field(default=Priority.MEDIUM)
    reject_reason: Optional[List[RejectReason]] = None

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "examples": [
                {
                    "title": "Sample Task",
                    "description": "This is a sample task description",
                    "status": "draft",
                    "priority": "medium",
                    
                },
                {
                    "title": "Rejected Task",
                    "description": "This task was rejected due to duplication",
                    "status": "rejected",
                    "priority": "high",
                    "reject_reason": "duplicate",
                     
                }
            ]
        }
class DashboardItemCreate(DashboardItemBase):
   pass
class DashboardItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    status: Optional[Status] = None
    priority: Optional[Priority] = None
    reject_reason: Optional[List[RejectReason]] = None
    

class DashboardItemDB(DashboardItemBase):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
   
    

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "title": "Sample Task",
                "description": "This is a sample task description",
                "status": "draft",
                "priority": "medium",
                "reject_reason": None,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
               
            }
        }

@router.post("/", response_model=DashboardItemDB)
async def create_dashboard_item(item: DashboardItemCreate):
    # Validate created_by against employee collection
   

    item_dict = item.dict()
    item_dict["_id"] = ObjectId()
    item_dict["created_at"] = datetime.utcnow()
    item_dict["updated_at"] = datetime.utcnow()
    
    result = collection.insert_one(item_dict)
    created_item = collection.find_one({"_id": result.inserted_id})
    created_item["_id"] = str(created_item["_id"])
    return DashboardItemDB(**created_item)



        
        
    
    
    
    
    
    
    
    
    
    
    
    
    
    
@router.get("/{item_id}", response_model=DashboardItemDB)
async def get_dashboard_item(item_id: str):
    try:
        item = collection.find_one({"_id": ObjectId(item_id)})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        item["_id"] = str(item["_id"])
        return DashboardItemDB(**item)
    except errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid item ID format")


@router.put("/{item_id}", response_model=DashboardItemDB)
async def update_dashboard_item(item_id: str, item: DashboardItemUpdate):
    # Validate updated_by against employee collection
   
    try:
        update_data = {k: v for k, v in item.dict(exclude_unset=True).items() if v is not None}
        print('Update Data:', update_data)  # Verify update data here
        update_data["updated_at"] = datetime.utcnow()
        
        result = collection.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        
        updated_item = collection.find_one({"_id": ObjectId(item_id)})
        updated_item["_id"] = str(updated_item["_id"])
        return DashboardItemDB(**updated_item)
    except errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid item ID format")

@router.delete("/{item_id}", status_code=204)
async def delete_dashboard_item(item_id: str):
    try:
        result = collection.delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
    except errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid item ID format")

# File Upload Configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".pdf"}

@router.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_extension = Path(file.filename).suffix
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        unique_filename = f"{uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        
        return {"filename": unique_filename, "filepath": str(file_path), "content_type": file.content_type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")



@router.get("/dashboard/reject-reasons", response_model=List[str])
async def get_reject_reasons():
    return [reason.value for reason in RejectReason]






@router.get("/", response_model=List[DashboardItemDB])
async def get_all_dashboards(
    status: Optional[Status] = None,
    priority: Optional[Priority] = None
):
    filter_item = {}

    if status:
        filter_item["status"] = status.value  # Convert Enum to string
    if priority:
        filter_item["priority"] = priority.value  # Convert Enum to string

    dashboards = collection.find(filter_item)
    result = []
    
    for item in dashboards:
        item["_id"] = str(item["_id"])
        result.append(DashboardItemDB(**item))
    
    return result

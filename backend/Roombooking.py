from fastapi import FastAPI, HTTPException, UploadFile, File, Depends,APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from bson import ObjectId
from typing import List, Optional, Any, Annotated
from datetime import datetime
from pymongo import MongoClient
from urllib.parse import quote_plus
from enum import Enum
import os
from uuid import uuid4
from pathlib import Path
# MongoDB Configuration remains the same
username = quote_plus("bala")
password = quote_plus("bala123")
DATABASE_URL = f"mongodb+srv://{username}:{password}@cluster0.0z8bodb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "Reporter"
COLLECTION_NAME = "Bookings"

# Initialize FastAPI and MongoDB

client = MongoClient(DATABASE_URL)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]



router = APIRouter(tags=["Roombooking"], prefix="/roombooking")




# UPLOAD_DIR = Path("uploads")
# UPLOAD_DIR.mkdir(exist_ok=True)
# Fixed PyObjectId class
class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value, handler):
        if not isinstance(value, (str, ObjectId)):
            raise ValueError("Invalid ObjectId")
        
        if isinstance(value, str) and not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId format")
            
        return str(value) if isinstance(value, ObjectId) else value

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")
        return field_schema

# Rest of the models and routes remain the same as in the previous version...


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    

class BookingBase(BaseModel):
    room_number: int
    check_in: datetime
    check_out: datetime
    customer_name: str
    customer_email: str
    customer_phone: int
    amount: int
    aadhar_number: int
    image_url: Optional[str] = None  # New field for image URL
    status: Optional[BookingStatus] = None


model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class BookingDB(BookingBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class BookingResponse(BookingBase):
    id: str

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class BookingUpdate(BaseModel):
    room_number: Optional[int] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[int] = None
    amount: Optional[int] = None
    status: Optional[str] = None
    aadhar_number: Optional[int] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)










# @app.post("/upload-image/")
# async def upload_image(file: UploadFile = File(...)):
#     try:
#         # Generate a unique file name
#         file_extension = file.filename.split(".")[-1]
#         if file_extension not in {"jpg", "jpeg", "png", "gif"}:
#             raise HTTPException(status_code=400, detail="Unsupported file type")
        
#         unique_filename = f"{uuid4()}.{file_extension}"
#         file_path = UPLOAD_DIR / unique_filename

#         # Save file
#         with open(file_path, "wb") as f:
#             f.write(await file.read())

#         # Generate file URL (in production, this would be a public URL)
#         file_url = f"/uploads/{unique_filename}"

#         return {"file_url": file_url}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
# # Routes remain the same as in previous version


@router.post("/booking", response_model=BookingResponse)
async def create_booking(booking: BookingBase):
    try:
        if booking.check_out <= booking.check_in:
            raise HTTPException(
                status_code=400,
                detail="Check-out date must be after check-in date"
            )

        existing_booking = collection.find_one({
            "room_number": booking.room_number,
            "check_out": {"$gt": booking.check_in},
            "check_in": {"$lt": booking.check_out},
        })
        if existing_booking:
            raise HTTPException(
                status_code=400,
                detail="Room is not available for these dates"
            )

        booking_dict = booking.model_dump()  # Changed from dict() to model_dump()
        booking_dict["created_at"] = datetime.utcnow()
        booking_dict["updated_at"] = datetime.utcnow()

        result = collection.insert_one(booking_dict)
        created_booking = collection.find_one({"_id": result.inserted_id})
        
        if created_booking is None:
            raise HTTPException(
                status_code=404,
                detail="Created booking not found"
            )
            
        return BookingDB(**created_booking)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/booking/{booking_id}", response_model=BookingResponse)
async def get_booking(booking_id: str):
    try:
        if not ObjectId.is_valid(booking_id):
            raise HTTPException(status_code=400, detail="Invalid booking ID format")

        booking = collection.find_one({"_id": ObjectId(booking_id)})
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        return BookingDB(**booking)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/bookings", response_model=List[BookingResponse])
async def list_bookings():
    try:
        bookings = list(collection.find())
        return [BookingDB(**booking) for booking in bookings]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/booking/{booking_id}", response_model=BookingResponse)
async def update_booking(booking_id: str, booking_update: BookingUpdate):
    try:
        if not ObjectId.is_valid(booking_id):
            raise HTTPException(status_code=400, detail="Invalid booking ID format")

        update_data = {k: v for k, v in booking_update.model_dump().items() if v is not None}  # Changed from dict() to model_dump()
        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_data["updated_at"] = datetime.utcnow()

        result = collection.update_one(
            {"_id": ObjectId(booking_id)},
            {"$set": update_data}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Booking not found")

        updated_booking = collection.find_one({"_id": ObjectId(booking_id)})
        return BookingDB(**updated_booking)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/booking/{booking_id}")
async def delete_booking(booking_id: str):
    try:
        if not ObjectId.is_valid(booking_id):
            raise HTTPException(status_code=400, detail="Invalid booking ID format")

        result = collection.delete_one({"_id": ObjectId(booking_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Booking not found")

        return {"message": "Booking deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
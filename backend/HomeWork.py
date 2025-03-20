from typing import Optional, List, Dict
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
from bson.objectid import ObjectId
from pydantic import BaseModel, Field
from urllib.parse import quote_plus
from enum import Enum
import uuid
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database and CORS setup
username_name = quote_plus("bala")
password_password = quote_plus("bala123")
DATABASE_URL = f"mongodb+srv://{username_name}:{password_password}@cluster0.0z8bodb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

router = APIRouter(tags=["HomeWork"], prefix="/HomeWork")

# Database connection with error handling
try:
    client = MongoClient(DATABASE_URL)
    db = client.Portal
    collection = db.Booking
    # Test connection
    client.admin.command('ping')
    logger.info("Connected to MongoDB successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    raise

# Predefined price list
PRICE_LIST = {
    "table": 500,
    "chair": 200,
    "sofa": 1000,
    "bed": 1500,
    "cupboard": 1200
}

# Enum for Vehicle Type
class VehicleType(str, Enum):
    MINI_TRUCK = "mini_truck"
    BIG_TRUCK = "big_truck"

# Enum for Booking Status
class BookingStatus(str, Enum):
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'

# Enum for Work Status
class WorkStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"

# Enum for Confirmation Status
class ConfirmationStatus(str, Enum):
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"

# Generate unique booking ID
def generate_booking_id():
    return str(uuid.uuid4().int)[-6:]

# Schema for Item Details
class ItemDetails(BaseModel):
    item_names_and_quantity: Dict[str, int] = Field(..., description="Dictionary of item names and their quantities")

# Schema for Booking Details
class BookingDetails(BaseModel):
    items: List[ItemDetails] = Field(..., description="List of items to be moved")
    vehicle_type: VehicleType = Field(..., description="Type of vehicle required for transport")
    no_of_workers: int = Field(..., description="Number of workers required for the job")
    preferred_date: Optional[datetime] = Field(None, description="Preferred date for the service")
    preferred_time_slot: Optional[str] = Field(None, description="Preferred time slot for the service")

# Schema for Customer Details
class CustomerDetails(BaseModel):
    name: str = Field(..., description="Customer's full name")
    mobile: str = Field(..., min_length=10, max_length=15, description="Customer's mobile number")
    area: str = Field(..., description="Area where the service is required")
    street: str = Field(..., description="Street where the service is required")
    booking_details: BookingDetails

# Schema for Booking Request
class BookingRequest(BaseModel):
    customer: CustomerDetails

# Schema for Booking Confirmation Response
class BookingConfirmationResponse(BaseModel):
    booking_id: str = Field(..., description="Unique ID for the booking")
    confirmation_status: ConfirmationStatus = Field(..., description="Status of the booking confirmation")
    estimated_arrival_time: Optional[datetime] = Field(None, description="Estimated time for workers to arrive")
    total_amount: float = Field(..., description="Total amount for the booking")
    message: str = Field(..., description="Custom message to the customer")

# Schema for Booking Update
class BookingUpdate(BaseModel):
    confirmation_status: Optional[ConfirmationStatus] = None
    estimated_arrival_time: Optional[datetime] = None
    assigned_workers: Optional[List[str]] = None
    work_status: Optional[WorkStatus] = None

# Function to calculate total price based on selected items and quantity
def calculate_total_amount(items: List[ItemDetails]) -> float:
    total_amount = 0
    for item_detail in items:
        for item, quantity in item_detail.item_names_and_quantity.items():
            if item.lower() not in PRICE_LIST:
                raise HTTPException(status_code=400, detail=f"Invalid item '{item}'")
            price_per_item = PRICE_LIST.get(item.lower())
            total_amount += quantity * price_per_item
    return total_amount

def calculate_estimated_arrival(preferred_date=None, preferred_time_slot=None):
    if preferred_date and preferred_time_slot:
        # Use customer's preferred date and time if provided
        time_parts = preferred_time_slot.split('-')[0].strip()  # Get start time
        hour, minute = map(int, time_parts.split(':'))
        return preferred_date.replace(hour=hour, minute=minute)
    else:
        # Default: 2 hours from now
        return datetime.utcnow() + timedelta(hours=2)

# API to handle booking request
@router.post("/booking", response_model=BookingConfirmationResponse)
async def create_booking(request: BookingRequest):
    try:
        booking_id = generate_booking_id()
        total_amount = calculate_total_amount(request.customer.booking_details.items)
        
        # Calculate estimated arrival time
        estimated_arrival_time = calculate_estimated_arrival(
            request.customer.booking_details.preferred_date,
            request.customer.booking_details.preferred_time_slot
        )

        # Save to MongoDB
        booking_data = {
            "booking_id": booking_id,
            "customer_name": request.customer.name,
            "mobile": request.customer.mobile,
            "area": request.customer.area,
            "street": request.customer.street,
            "vehicle_type": request.customer.booking_details.vehicle_type,
            "no_of_workers": request.customer.booking_details.no_of_workers,
            "items": [item.dict() for item in request.customer.booking_details.items],
            "total_amount": total_amount,
            "confirmation_status": ConfirmationStatus.CONFIRMED.value,
            "preferred_date": request.customer.booking_details.preferred_date,
            "preferred_time_slot": request.customer.booking_details.preferred_time_slot,
            "estimated_arrival_time": estimated_arrival_time,
            "work_status": WorkStatus.PROCESSING.value,
            "assigned_workers": [],
            "created_at": datetime.utcnow()
        }
        
        result = collection.insert_one(booking_data)
        logger.info(f"Booking created with ID: {booking_id}")

        return BookingConfirmationResponse(
            booking_id=booking_id,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            estimated_arrival_time=estimated_arrival_time,
            total_amount=total_amount,
            message=f"Your booking is confirmed. Estimated arrival: {estimated_arrival_time.strftime('%Y-%m-%d %H:%M')}. Total amount: ₹{total_amount}"
        )
    except Exception as e:
        logger.error(f"Error creating booking: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create booking: {str(e)}")

# Get all bookings with optional filters
@router.get("/bookings")
async def get_all_bookings(
    status: Optional[ConfirmationStatus] = None,
    area: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    work_status: Optional[WorkStatus] = None
):
    try:
        # Build query based on filters
        query = {}
        if status:
            query["confirmation_status"] = status
            
        if work_status:
            query["work_status"] = work_status
        
        if area:
            query["area"] = area
            
        # Date range filter
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = datetime.strptime(date_from, "%Y-%m-%d")
            if date_to:
                date_query["$lte"] = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            if date_query:
                query["created_at"] = date_query
                
        result = list(collection.find(query))
        
        # Convert ObjectId to string for JSON serialization
        for doc in result:
            doc['_id'] = str(doc['_id'])
            
        return result
    except Exception as e:
        logger.error(f"Error retrieving bookings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve bookings: {str(e)}")

# Get booking by ID
@router.get("/booking/{booking_id}")
async def get_booking_by_id(booking_id: str):
    try:
        booking = collection.find_one({"booking_id": booking_id})
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
            
        booking['_id'] = str(booking['_id'])
        return booking
    except Exception as e:
        logger.error(f"Error retrieving booking {booking_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve booking: {str(e)}")

# Update booking status
@router.put("/booking/{booking_id}")
async def update_booking(booking_id: str, booking_update: BookingUpdate):
    try:
        # Check if booking exists
        booking = collection.find_one({"booking_id": booking_id})
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
            
        # Build update data
        update_data = {k: v for k, v in booking_update.dict().items() if v is not None}
        update_data["updated_at"] = datetime.utcnow()
        
        # Update booking
        result = collection.update_one(
            {"booking_id": booking_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            return {"message": "No changes made to booking"}
            
        # Return updated booking
        updated_booking = collection.find_one({"booking_id": booking_id})
        updated_booking['_id'] = str(updated_booking['_id'])
        
        return updated_booking
    except Exception as e:
        logger.error(f"Error updating booking {booking_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update booking: {str(e)}")

# Cancel booking
@router.put("/booking/{booking_id}/cancel")
async def cancel_booking(booking_id: str):
    try:
        # Check if booking exists
        booking = collection.find_one({"booking_id": booking_id})
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
            
        # Can only cancel bookings that are not completed or already cancelled
        if booking.get("confirmation_status") in [ConfirmationStatus.COMPLETED.value, ConfirmationStatus.CANCELLED.value]:
            raise HTTPException(status_code=400, detail="Cannot cancel a booking that is already completed or cancelled")
            
        # Update booking status
        result = collection.update_one(
            {"booking_id": booking_id},
            {"$set": {
                "confirmation_status": ConfirmationStatus.CANCELLED.value,
                "updated_at": datetime.utcnow()
            }}
        )
        
        return {"message": "Booking cancelled successfully"}
    except Exception as e:
        logger.error(f"Error cancelling booking {booking_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel booking: {str(e)}")

# Legacy endpoint for backward compatibility
@router.get("/")
def get_all():
    try:
        result = list(collection.find({}))
        for doc in result:
            doc['_id'] = str(doc['_id'])
        return result
    except Exception as e:
        logger.error(f"Error in get_all: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    



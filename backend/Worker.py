from typing import Optional, List, Dict
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from pymongo import MongoClient
from bson.objectid import ObjectId
from pydantic import BaseModel, Field, validator
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
# Worker/Driver Router
router = APIRouter(tags=["Workers"], prefix="/workers")

# Database connection with error handling
try:
    client = MongoClient(DATABASE_URL)
    db = client.Portal
    # Test connection
    client.admin.command('ping')
    logger.info("Connected to MongoDB successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    raise

# Enums for worker status and type
class WorkerStatus(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ON_LEAVE = "on_leave"

class WorkerType(str, Enum):
    DRIVER = "driver"
    LOADER = "loader"
    SUPERVISOR = "supervisor"

# Worker skills
class WorkerSkill(str, Enum):
    FURNITURE_ASSEMBLY = "furniture_assembly"
    HEAVY_LIFTING = "heavy_lifting"
    PACKING = "packing"
    DRIVING = "driving"
    FRAGILE_ITEMS = "fragile_items"

# Time slot model
class TimeSlot(BaseModel):
    start: str
    end: str
    
    @validator('start', 'end')
    def validate_time_format(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
            return v
        except ValueError:
            raise ValueError("Time must be in format HH:MM")

# Worker schemas
class WorkerBase(BaseModel):
    name: str
    mobile: str
    worker_type: WorkerType
    skills: List[WorkerSkill] = []
    area_assigned: str
    status: WorkerStatus = WorkerStatus.AVAILABLE
    rating: float = 0.0
    
class WorkerCreate(WorkerBase):
    pass
    
class WorkerUpdate(BaseModel):
    name: Optional[str] = None
    mobile: Optional[str] = None
    worker_type: Optional[WorkerType] = None
    skills: Optional[List[WorkerSkill]] = None
    area_assigned: Optional[str] = None
    status: Optional[WorkerStatus] = None
    rating: Optional[float] = None
    
    @validator('rating')
    def validate_rating(cls, v):
        if v is not None and (v < 0 or v > 5):
            raise ValueError("Rating must be between 0 and 5")
        return v

class Worker(WorkerBase):
    id: str
    completed_jobs: int = 0
    current_booking_id: Optional[str] = None
    available_time_slots: List[TimeSlot] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# Worker schedule model
class WorkerSchedule(BaseModel):
    worker_id: str
    date: datetime
    time_slots: List[TimeSlot]

# Simple function to create a worker ID
def generate_worker_id():
    return str(uuid.uuid4())[:8]

# CRUD operations for workers
@router.post("/", response_model=Worker)
async def create_worker(worker: WorkerCreate):
    try:
        # Check if worker with same mobile already exists
        existing_worker = db.workers.find_one({"mobile": worker.mobile})
        if existing_worker:
            raise HTTPException(status_code=400, detail="Worker with this mobile already exists")
        
        # Create new worker
        worker_data = worker.dict()
        worker_data.update({
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_jobs": 0,
            "current_booking_id": None,
            "available_time_slots": [
                {"start": "09:00", "end": "13:00"},
                {"start": "14:00", "end": "18:00"}
            ]
        })
        
        result = db.workers.insert_one(worker_data)
        worker_data["id"] = str(result.inserted_id)
        
        logger.info(f"Worker created with ID: {worker_data['id']}")
        return worker_data
    except Exception as e:
        logger.error(f"Error creating worker: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create worker: {str(e)}")

@router.get("/", response_model=List[Worker])
async def get_all_workers(
    status: Optional[WorkerStatus] = None,
    worker_type: Optional[WorkerType] = None,
    area: Optional[str] = None,
    skill: Optional[WorkerSkill] = None
):
    try:
        # Build query based on filters
        query = {}
        if status:
            query["status"] = status
        if worker_type:
            query["worker_type"] = worker_type
        if area:
            query["area_assigned"] = area
        if skill:
            query["skills"] = skill
        
        workers = list(db.workers.find(query))
        for worker in workers:
            worker["id"] = str(worker.pop("_id"))
        
        return workers
    except Exception as e:
        logger.error(f"Error retrieving workers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve workers: {str(e)}")

@router.get("/{worker_id}", response_model=Worker)
async def get_worker(worker_id: str):
    try:
        worker = db.workers.find_one({"_id": ObjectId(worker_id)})
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")
        
        worker["id"] = str(worker.pop("_id"))
        return worker
    except Exception as e:
        logger.error(f"Error retrieving worker {worker_id}: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Worker not found: {str(e)}")

@router.put("/{worker_id}", response_model=Worker)
async def update_worker(worker_id: str, worker_update: WorkerUpdate):
    try:
        update_data = {k: v for k, v in worker_update.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No update data provided")
        
        update_data["updated_at"] = datetime.utcnow()
        
        result = db.workers.update_one(
            {"_id": ObjectId(worker_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Worker not found")
        
        updated_worker = db.workers.find_one({"_id": ObjectId(worker_id)})
        updated_worker["id"] = str(updated_worker.pop("_id"))
        
        return updated_worker
    except Exception as e:
        logger.error(f"Error updating worker {worker_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update worker: {str(e)}")

@router.delete("/{worker_id}")
async def delete_worker(worker_id: str):
    try:
        # Check if worker has current bookings
        worker = db.workers.find_one({"_id": ObjectId(worker_id)})
        if worker and worker.get("current_booking_id"):
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete worker with active bookings. Reassign bookings first."
            )
        
        result = db.workers.delete_one({"_id": ObjectId(worker_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Worker not found")
        
        return {"message": "Worker deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting worker {worker_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete worker: {str(e)}")

# Worker assignment to booking
@router.post("/assign")
async def assign_workers(booking_id: str, worker_ids: List[str]):
    try:
        # Check if booking exists
        booking = db.Booking.find_one({"booking_id": booking_id})
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Check if workers exist and are available
        for worker_id in worker_ids:
            try:
                worker = db.workers.find_one({"_id": ObjectId(worker_id)})
                if not worker:
                    raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")
                
                if worker.get("status") != WorkerStatus.AVAILABLE:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Worker {worker_id} is not available. Current status: {worker.get('status')}"
                    )
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid worker ID: {worker_id}")
        
        # Update booking with assigned workers
        db.Booking.update_one(
            {"booking_id": booking_id},
            {"$set": {
                "assigned_workers": worker_ids,
                "confirmation_status": "in_progress"
            }}
        )
        
        # Update workers' status and current booking
        for worker_id in worker_ids:
            db.workers.update_one(
                {"_id": ObjectId(worker_id)},
                {"$set": {
                    "status": WorkerStatus.BUSY,
                    "current_booking_id": booking_id
                }}
            )
        
        return {"message": f"Workers assigned to booking {booking_id}"}
    except Exception as e:
        logger.error(f"Error assigning workers to booking {booking_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to assign workers: {str(e)}")

# Complete a booking
@router.post("/complete-booking/{booking_id}")
async def complete_booking(booking_id: str):
    try:
        # Check if booking exists
        booking = db.Booking.find_one({"booking_id": booking_id})
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Update booking status
        db.Booking.update_one(
            {"booking_id": booking_id},
            {"$set": {
                "confirmation_status": "completed",
                "work_status": "completed",
                "completed_at": datetime.utcnow()
            }}
        )
        
        # Update all assigned workers
        worker_ids = booking.get("assigned_workers", [])
        for worker_id in worker_ids:
            db.workers.update_one(
                {"_id": ObjectId(worker_id)},
                {
                    "$set": {
                        "status": WorkerStatus.AVAILABLE,
                        "current_booking_id": None
                    },
                    "$inc": {"completed_jobs": 1}
                }
            )
        
        return {"message": f"Booking {booking_id} marked as completed"}
    except Exception as e:
        logger.error(f"Error completing booking {booking_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to complete booking: {str(e)}")






@router.post("/schedule")
async def update_worker_schedule(schedule: WorkerSchedule):
    try:
        # Check if worker exists
        worker = db.workers.find_one({"_id": ObjectId(schedule.worker_id)})
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")
        
        # Check if a schedule already exists for this date
        existing_schedule = db.worker_schedules.find_one({
            "worker_id": schedule.worker_id,
            "date": schedule.date
        })
        
        if existing_schedule:
            # Update existing schedule
            db.worker_schedules.update_one(
                {"_id": existing_schedule["_id"]},
                {"$set": {
                    "time_slots": [slot.dict() for slot in schedule.time_slots],
                    "updated_at": datetime.utcnow()
                }}
            )
        else:
            # Create new schedule
            db.worker_schedules.insert_one({
                "worker_id": schedule.worker_id,
                "date": schedule.date,
                "time_slots": [slot.dict() for slot in schedule.time_slots],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
        
        return {"message": "Worker schedule updated successfully"}
    except Exception as e:
        logger.error(f"Error updating worker schedule: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update worker schedule: {str(e)}")
    
    


@router.get("/available/{area}", response_model=List[Worker])
async def get_available_workers_by_area(
    area: str,
    worker_type: Optional[WorkerType] = None,
    skill: Optional[WorkerSkill] = None
):
    try:
        # Build query for available workers in the specified area
        query = {
            "area_assigned": area,
            "status": WorkerStatus.AVAILABLE
        }
        
        # Add optional filters
        if worker_type:
            query["worker_type"] = worker_type
        if skill:
            query["skills"] = skill
        
        workers = list(db.workers.find(query))
        if not workers:
            logger.info(f"No available workers found in area: {area}")
            return []
            
        # Transform ObjectId to string for serialization
        for worker in workers:
            worker["id"] = str(worker.pop("_id"))
        
        logger.info(f"Found {len(workers)} available workers in area: {area}")
        return workers
    except Exception as e:
        logger.error(f"Error retrieving available workers in area {area}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve available workers: {str(e)}")
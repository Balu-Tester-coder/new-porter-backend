from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
from bson.objectid import ObjectId
from pydantic import BaseModel, Field
from urllib.parse import quote_plus
from enum import Enum


# Database and CORS setup
username_name = quote_plus("bala")
password_password = quote_plus("bala123")
DATABASE_URL = f"mongodb+srv://{username_name}:{password_password}@cluster0.0z8bodb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

router = APIRouter(tags=["EmployeeAttendence"], prefix="/Attendence")

client = MongoClient(DATABASE_URL)
db = client.Attendence
employee_collection = db.Employee
attendence_collection = db.attendence
leave_collection = db.leave
overtime_collection = db.overTime


db = client.Dashboard
collection = db.details



class OverTimeEnum(str, Enum):
    APPROVED = 'approved'
    REJECTED = 'rejected'
    PENDING = 'pending'

class StatusEnum(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    ON_LEAVE = 'onleave'

class LeaveStatusEnum(str, Enum):
    APPROVED = 'approved'
    REJECTED = 'rejected'
    PENDING = 'pending'
    

class LeaveEnum(str, Enum):
    SICK = "sick"
    VACATION = 'vacation'

class EmployeeInfo(BaseModel):
    employee_id: Optional[int]
    name: str
    department: str
    position: str
    email: str
    phone: str
    status: StatusEnum
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class Attendence(BaseModel):
    employee_id: int
    date: str
    checkin_time: str
    checkout_time: str
    total_hours: float
    status: StatusEnum
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class LeaveCollection(BaseModel):
    employee_id: int
    start_date: str
    end_date: str
    leave_type: LeaveEnum
    status: LeaveStatusEnum
    reason: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class OverTime(BaseModel):
    employee_id: int
    date: str
    start_time: str
    end_time: str
    total_hours: float
    status: OverTimeEnum
    created_at: datetime
    updated_at: datetime

def get_next_employee_id():
    last_employee = employee_collection.find_one(sort=[("employee_id", -1)])
    if last_employee:
        return int(last_employee.get("employee_id", 0)) + 1
    else:
        return 1
    
    
    
@router.post('/create-employee')
def create_employee(payload: EmployeeInfo):
    if employee_collection.find_one({"email": payload.email}):
        raise HTTPException(status_code=409, detail="Employee already exists")

    try:
        payload.employee_id = get_next_employee_id()
        payload.created_at = datetime.utcnow()
        payload.updated_at = datetime.utcnow()
        new_employee = employee_collection.insert_one(payload.model_dump())

        if new_employee.inserted_id:
            return {"message": "Employee created successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to create employee")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@router.get("/leaves/{employee_id}")
def get_leaves(employee_id: int):
    if employee_id == 1:
        result = list(leave_collection.find({"employee_id": 1}, {"_id": 0}))
    elif employee_id == 2:
        result = list(leave_collection.find({"employee_id": 2}, {"_id": 0}))
    elif employee_id == 3:
        result = list(leave_collection.find({"employee_id": {"$in": [1, 2, 3]}}, {"_id": 0}))
    else:
        raise HTTPException(status_code=404, detail="Employee not found")

    return result



@router.get('/')
def get_employees():
    result = list(employee_collection.find({}, {"_id": 0}))  # Exclude _id from the result
    return result


@router.post('/apply-leave')
def apply_leave(payload: LeaveCollection):
    try:
        if not employee_collection.find_one({"employee_id": payload.employee_id}):
            raise HTTPException(status_code=404, detail="Employee not found")

        # Check if a leave already exists for the same period
        if leave_collection.find_one({
            "employee_id": payload.employee_id,
            "start_date": {"$lte": payload.end_date},
            "end_date": {"$gte": payload.start_date}
        }):
            raise HTTPException(status_code=409, detail="Leave already applied for this period")

        # Set default values
        payload.status = LeaveStatusEnum.PENDING
        payload.created_at = datetime.utcnow()
        payload.updated_at = datetime.utcnow()

        # Insert the leave request into the database
        result = leave_collection.insert_one(payload.model_dump())

        if result.inserted_id:
            return {"message": "Leave applied successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to apply leave")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

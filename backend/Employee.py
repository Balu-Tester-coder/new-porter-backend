from typing import List, Annotated, Optional
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Query,APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson.objectid import ObjectId
from pydantic import BaseModel, Field
from urllib.parse import quote_plus
from enum import Enum





# Enhanced Enums for dropdown options
class PaymentMethod(str, Enum):
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    CHECK = "check"
    PAYPAL = "paypal"
    WIRE = "wire"

class Department(str, Enum):
    ENGINEERING = "Engineering"
    MARKETING = "Marketing"
    SALES = "Sales"
    HR = "HR"
    FINANCE = "Finance"
    OPERATIONS = "Operations"
    IT = "IT"

class PaymentType(str, Enum):
    SALARY = "salary"
    BONUS = "bonus"
    COMMISSION = "commission"
    REIMBURSEMENT = "reimbursement"

class PaymentStatus(str, Enum):
    PAID = "paid"
    PENDING = "pending"
    FAILED = "failed"

# Database and CORS setup
username_name = quote_plus("bala")
password_password = quote_plus("bala123")
DATABASE_URL = f"mongodb+srv://{username_name}:{password_password}@cluster0.0z8bodb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

router = APIRouter(tags=["Employee"], prefix="/employee")


client = MongoClient(DATABASE_URL)
db = client.employee_payments
collection = db.payments


# Pydantic models
class PaymentBase(BaseModel):
    employee_id: str = Field(..., description="Unique employee identifier")
    employee_name: str = Field(..., description="Full name of employee")
    department: Department = Field(..., description="Department of employee")
    payment_type: PaymentType = Field(..., description="Type of payment")
    amount: float = Field(..., ge=0, description="Payment amount")
    payment_date: datetime = Field(default_factory=datetime.now, description="Date of payment")
    payment_status: PaymentStatus = Field(..., description="Status of payment")
    payment_method: PaymentMethod = Field(..., description="Method of payment")
    currency: str = Field(default="USD", description="Currency of payment")
    notes: Optional[str] = Field(default=None, description="Additional notes")

# Endpoints for dropdown options
@router.get("/options/departments", response_model=List[str])
async def get_departments():
    """Get list of all departments for dropdown"""
    return [dept.value for dept in Department]

@router.get("/options/payment-methods", response_model=List[str])
async def get_payment_methods():
    """Get list of all payment methods for dropdown"""
    return [method.value for method in PaymentMethod]

@router.get("/options/payment-types", response_model=List[str])
async def get_payment_types():
    """Get list of all payment types for dropdown"""
    return [p_type.value for p_type in PaymentType]

@router.get("/options/payment-status", response_model=List[str])
async def get_payment_status():
    """Get list of all payment status options for dropdown"""
    return [status.value for status in PaymentStatus]

# Enhanced search parameters
class SearchParams(BaseModel):
    search_text: Optional[str] = None
    department: Optional[Department] = None
    payment_method: Optional[PaymentMethod] = None
    payment_type: Optional[PaymentType] = None
    payment_status: Optional[PaymentStatus] = None

# Enhanced search endpoint
@router.get("/employees/search")
async def search_employees(
    search_text: Optional[str] = Query(None, description="Search by employee name"),
    department: Optional[Department] = Query(None, description="Filter by department"),
    payment_method: Optional[PaymentMethod] = Query(None, description="Filter by payment method"),
    payment_type: Optional[PaymentType] = Query(None, description="Filter by payment type"),
    payment_status: Optional[PaymentStatus] = Query(None, description="Filter by payment status")
):
    query = {}
    
    if search_text:
        query["employee_name"] = {"$regex": search_text, "$options": "i"}
    
    if department:
        query["department"] = department
        
    if payment_method:
        query["payment_method"] = payment_method
        
    if payment_type:
        query["payment_type"] = payment_type
        
    if payment_status:
        query["payment_status"] = payment_status

    # Get unique employees matching the criteria
    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": "$employee_id",
            "employee_name": {"$first": "$employee_name"},
            "department": {"$first": "$department"},
            "payment_type": {"$first": "$payment_type"},
            "latest_payment": {"$max": "$payment_date"},
            "total_payments": {"$sum": "$amount"}
        }},
        {"$sort": {"employee_name": 1}}
    ]
    
    results = list(collection.aggregate(pipeline))
    return results

# Example combined search with all filters
@router.get("/employees/combined-search")
async def combined_search(
    search_text: Optional[str] = Query(None),
    department: Optional[Department] = Query(None),
    payment_method: Optional[PaymentMethod] = Query(None),
    payment_type: Optional[PaymentType] = Query(None),
    payment_status: Optional[PaymentStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    query = {}
    
    if search_text:
        query["employee_name"] = {"$regex": search_text, "$options": "i"}
    if department:
        query["department"] = department
    if payment_method:
        query["payment_method"] = payment_method
    if payment_type:
        query["payment_type"] = payment_type
    if payment_status:
        query["payment_status"] = payment_status

    # Add pagination
    skip = (page - 1) * page_size
    
    # Get total count
    total_count = collection.count_documents(query)
    
    # Get paginated results with sorting
    results = list(collection.find(query)
                  .sort("employee_name", 1)
                  .skip(skip)
                  .limit(page_size))
    
    # Convert ObjectId to string
    for result in results:
        result["_id"] = str(result["_id"])
    
    return {
        # "total": total_count,
        # "page": page,
        # "page_size": page_size,
        # "total_pages": (total_count + page_size - 1) // page_size,
        "results": results
    }
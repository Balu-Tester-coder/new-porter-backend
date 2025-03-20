from typing import Optional, List
from datetime import datetime
from fastapi import FastAPI, HTTPException, APIRouter, Depends
from pymongo import MongoClient, ReturnDocument
from bson.objectid import ObjectId
from pydantic import BaseModel, Field, validator
from urllib.parse import quote_plus
from enum import Enum
from fastapi.responses import JSONResponse


router = APIRouter(tags=["Tasks"], prefix="/tasks")

# Database setup
username = "bala"
password = "bala123"
escaped_username = quote_plus(username)
escaped_password = quote_plus(password)
DATABASE_URL = f"mongodb+srv://{escaped_username}:{escaped_password}@cluster0.0z8bodb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(DATABASE_URL)

db = client.Attendence
tasks_collection = db.tasks
employee_collection = db.Employee
users_collection = db.users


class TaskStatus(str, Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    ARCHIVED = "archived"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EmployeeStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    ON_LEAVE = "on_leave"


class ContentStatusEnum(str, Enum):
    APPROVED = 'approved'
    REJECTED = 'rejected'
    PENDING = 'pending'


# New model for tracking content status changes

class ContentStatusChange(BaseModel):
    status: ContentStatusEnum
    changed_by: int
    changed_at: datetime
    comment: Optional[str] = None


# Define a model for reassignment tracking

class ReassignmentRecord(BaseModel):
    type: str = "reassignment"
    previous_employee_id: Optional[int]
    new_employee_id: int
    changed_by: int  # Who made the reassignment (admin_id or 0 for system)
    changed_at: datetime
    comment: Optional[str] = None


class TaskBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    status: Optional[TaskStatus] = TaskStatus.BACKLOG
    content_status: Optional[ContentStatusEnum] = ContentStatusEnum.PENDING
    due_date: Optional[datetime] = None
    employee_id:  Optional[int] = None
    dependencies: List[str] = []
    estimated_hours: float = Field(..., gt=0)
    logged_hours: float = 0.0
    
    # Tracking fields
    last_modified_by: Optional[int] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    completed_by: Optional[int] = None
    completed_at: Optional[datetime] = None
    status_history: List[ContentStatusChange] = Field(default_factory=list)
    reassignment_history: List[ReassignmentRecord] = Field(default_factory=list)


class TaskCreate(TaskBase):
    pass


class Task(TaskBase):
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    @validator('id', pre=True)
    def convert_objectid_to_str(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        return v

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Utility functions


def validate_object_id(task_id: str):
    try:
        return ObjectId(task_id)
    except:
        raise HTTPException(400, "Invalid task ID format")


def get_employee_task_count(employee_id: int) -> int:
    return tasks_collection.count_documents({
        "employee_id": employee_id,
        "status": {"$nin": [TaskStatus.DONE, TaskStatus.ARCHIVED]}
    })



# API Endpoints
@router.post("/", response_model=Task)
def create_task(task: TaskCreate):
    task_data = task.dict()

    # Validate employee existence and status
    # employee = employee_collection.find_one({"employee_id": task.employee_id})
    # if not employee or employee["status"] != EmployeeStatus.PRESENT:
    #     raise HTTPException(400, "Invalid or inactive employee")
        
    # Ensure content_status is set, default to PENDING if not provided
    if "content_status" not in task_data or task_data["content_status"] is None:
        task_data["content_status"] = ContentStatusEnum.PENDING
        
    task_data.update({
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })
    
    result = tasks_collection.insert_one(task_data)
    new_task = tasks_collection.find_one({"_id": result.inserted_id})

    if new_task:
        new_task['id'] = str(new_task['_id'])
        return Task(**new_task)
    else:
        raise HTTPException(status_code=500, detail="Failed to create task")


@router.get("/employee/{employee_id}")
def get_employee_tasks(employee_id: int):
    """
    Get all tasks assigned to a specific employee, but only if the user is active.
    
    Args:
    - employee_id (int): The ID of the employee whose tasks to retrieve
    
    Returns:
    - dict: A dictionary containing a list of tasks assigned to the employee
    
    Raises:
    - 404: If employee is not found
    - 403: If user is not active
    """
    try:
        # Check if employee exists
        employee = employee_collection.find_one({"employee_id": employee_id})
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Check if user is active in the users collection
        user = users_collection.find_one({"employee_id": employee_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user is active
        if not user.get("is_active"):
            raise HTTPException(status_code=403, detail="User is not active")
        
        # Get all tasks assigned to this employee
        tasks = list(tasks_collection.find({"employee_id": employee_id}))
        
        # Convert ObjectId to string for each task
        for task in tasks:
            task["_id"] = str(task["_id"])
        
        return {"tasks": tasks}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "trace": traceback.format_exc()
            }
        )
    
 


@router.get("/employee-zero")
def get_task_employee_zero():
    # Find tasks where employee_id = 0 or content_status is REJECTED or PENDING
    query = {
        "$or": [
            {"employee_id": 0},
            {"content_status": {"$in": [ContentStatusEnum.REJECTED.value, ContentStatusEnum.PENDING.value]}}
        ]
    }
    
    tasks = list(tasks_collection.find(query))
    # Convert ObjectId to string for JSON compatibility
    tasks = [{**task, "_id": str(task["_id"])} for task in tasks]
    # Return tasks or an empty list
    return {"tasks": tasks}


@router.put("/{task_id}/assignone/{employee_id}", response_model=Task)
def assign_task(
    task_id: str, 
    employee_id: int,
    admin_id: Optional[int] = None,
    comment: Optional[str] = None
):
    """
    Assign a task to an employee
    
    Args:
    - task_id (str): The ID of the task to be assigned
    - employee_id (int): The ID of the employee to assign the task to
    - admin_id (Optional[int]): The ID of the admin making the assignment
    - comment (Optional[str]): Optional comment about the assignment
    
    Returns:
    - Task: The updated task document
    
    Raises:
    - 404: If task or employee not found
    - 400: If employee is inactive or has reached max capacity
    """
    try:
        # Validate task ID format
        task_oid = validate_object_id(task_id)
        
        # Get the task document
        task = tasks_collection.find_one({"_id": task_oid})
        if not task:
            raise HTTPException(404, "Task not found")
        
        # Check if task is already completed
        if task.get("status") in [TaskStatus.DONE.value, TaskStatus.ARCHIVED.value]:
            raise HTTPException(400, "Cannot assign completed or archived tasks")
        
        # Validate target employee
        employee = employee_collection.find_one({"employee_id": employee_id})
        if not employee:
            raise HTTPException(404, "Employee not found")
        if employee["status"] != EmployeeStatus.PRESENT:
            raise HTTPException(400, "Employee is not active")

        # Get the person making the change (admin or system)
        changed_by = admin_id if admin_id else 0  # 0 can represent system/automatic assignment
        
        # Create history record for this assignment
        current_time = datetime.utcnow()
        assignment_record = {
            "type": "assignment",
            "previous_employee_id": task.get("employee_id"),
            "new_employee_id": employee_id,
            "changed_by": changed_by,
            "changed_at": current_time,
            "comment": comment
        }
        
        # Prepare update data
        update_data = {
            "employee_id": employee_id,
            "status": TaskStatus.TODO.value,  # Set status to TODO when assigned
            "updated_at": current_time,
            "last_modified_by": changed_by
        }
        
        # Add the assignment record to history
        update_operations = {
            "$set": update_data,
            "$push": {"reassignment_history": assignment_record}
        }
        
        # Perform the assignment with history updates
        updated_task = tasks_collection.find_one_and_update(
            {"_id": task_oid},
            update_operations,
            return_document=ReturnDocument.AFTER
        )

        if not updated_task:
            raise HTTPException(500, "Failed to assign task")

        updated_task["id"] = str(updated_task["_id"])
        return Task(**updated_task)

    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        raise HTTPException(500, detail={
            "error": str(e),
            "trace": traceback.format_exc()
        })
    
    
    



@router.put("/{task_id}/complete", response_model=Task)
def complete_task(
    task_id: str,
    task_update: dict
):
    """
    Update a task's status and content status by an employee
    
    Args:
    - task_id (str): The ID of the task to be updated
    - task_update (dict): Dictionary containing the fields to update
    
    Returns:
    - Task: The updated task document
    
    Raises:
    - 404: If task not found
    - 403: If employee is not assigned to this task
    - 400: If task is already completed or archived
    """
    try:
        # Validate task ID format
        task_oid = validate_object_id(task_id)
        
        # Extract required fields
        employee_id = task_update.get("employee_id")
        status = task_update.get("status")
        content_status = task_update.get("content_status")
        comment = task_update.get("comment", "")
        
        if not employee_id or not status or not content_status:
            raise HTTPException(400, "Missing required fields: employee_id, status, or content_status")
            
        # Get the task document
        task = tasks_collection.find_one({"_id": task_oid})
        if not task:
            raise HTTPException(404, "Task not found")
        
        # Check if the task is already completed or archived
        if task.get("status") in [TaskStatus.DONE.value, TaskStatus.ARCHIVED.value]:
            raise HTTPException(400, "Task is already completed or archived")
        
        # Verify that the employee is assigned to this task
        if task.get("employee_id") != employee_id:
            raise HTTPException(403, "You are not assigned to this task")
        
        # Create content status change record
        current_time = datetime.utcnow()
        status_change = {
            "status": content_status,
            "changed_by": employee_id,
            "changed_at": current_time,
            "comment": comment
        }
        
        # Check if the task is being marked as done
        is_completed = status == TaskStatus.DONE.value
        
        # Prepare update data - only include fields that should be updated
        update_data = {
            "status": status,
            "content_status": content_status,
            "updated_at": current_time,
            "last_modified_by": employee_id
        }
        
        # If task is being marked as done, add completion info
        if is_completed:
            update_data.update({
                "completed_by": employee_id,
                "completed_at": current_time
            })
        
        # Add the status change record to history
        update_operations = {
            "$set": update_data,
            "$push": {"status_history": status_change}
        }
        
        # Perform the update with history updates
        updated_task = tasks_collection.find_one_and_update(
            {"_id": task_oid},
            update_operations,
            return_document=ReturnDocument.AFTER
        )
        
        if not updated_task:
            raise HTTPException(500, "Failed to update task")
        
        updated_task["id"] = str(updated_task["_id"])
        return Task(**updated_task)
    
    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        raise HTTPException(500, detail={
            "error": str(e),
            "trace": traceback.format_exc()
        })


@router.get("/employees", response_model=List[dict])
def get_all_employees():
    """
    Get a list of all active employees
    
    Returns:
    - List[dict]: A list of employee dictionaries with id and name
    """
    try:
        # Only fetch active employees
        employees = list(employee_collection.find(
            {"status": EmployeeStatus.PRESENT}, 
            {"_id": 0, "employee_id": 1, "name": 1}
        ))
        
        if not employees:
            return []
            
        return employees
        
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "trace": traceback.format_exc()
            }
        )
    
    



@router.get("/dashboard/daily", response_model=dict)
def get_daily_task_stats(date: Optional[str] = None):
    """
    Get daily task statistics for dashboard including pending and completed task counts.
    
    Query parameters:
    - date: Optional - Date in YYYY-MM-DD format to get statistics for a specific day
           If not provided, returns statistics for today
    
    Returns:
    - dict: Daily task statistics with counts of pending and completed tasks
    """
    try:
        # Handle date parameter
        if date:
            # For a specific date
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(400, "Invalid date format. Please use YYYY-MM-DD")
        else:
            # Default to today
            target_date = datetime.now()
        
        # Set start and end of the target day
        start_datetime = datetime.combine(target_date.date(), datetime.min.time())
        end_datetime = datetime.combine(target_date.date(), datetime.max.time())
        
        # Query for tasks created within the date range
        date_filter = {
            "created_at": {
                "$gte": start_datetime,
                "$lte": end_datetime
            }
        }
        
        # Get total tasks created on that day
        total_tasks = tasks_collection.count_documents(date_filter)
        
        # Get pending tasks (not done or archived)
        pending_filter = {
            **date_filter,
            "status": {"$nin": [TaskStatus.DONE.value, TaskStatus.ARCHIVED.value]}
        }
        pending_tasks = tasks_collection.count_documents(pending_filter)
        
        # Get completed tasks
        completed_filter = {
            **date_filter,
            "status": TaskStatus.DONE.value
        }
        completed_tasks = tasks_collection.count_documents(completed_filter)
        
        # Get status breakdown
        status_breakdown = {}
        for status in TaskStatus:
            status_filter = {
                **date_filter,
                "status": status.value
            }
            status_breakdown[status.value] = tasks_collection.count_documents(status_filter)
        
        # Get content status breakdown
        content_status_breakdown = {}
        for content_status in ContentStatusEnum:
            content_status_filter = {
                **date_filter,
                "content_status": content_status.value
            }
            content_status_breakdown[content_status.value] = tasks_collection.count_documents(content_status_filter)
        
        # Format the response
        return {
            "date": target_date.strftime("%Y-%m-%d"),
            "status": {
                "total_tasks": total_tasks,
                "pending_tasks": pending_tasks,
                "completed_tasks": completed_tasks,
                "status_breakdown": status_breakdown,
                "content_status_breakdown": content_status_breakdown
            }
        }
    
    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "trace": traceback.format_exc()
            }
        )
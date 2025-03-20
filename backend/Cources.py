from fastapi import FastAPI, HTTPException, status,APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from urllib.parse import quote_plus
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from bson import ObjectId

# Initialize FastAPI app


router = APIRouter(tags=["Cources"], prefix="/cources")


# MongoDB Atlas connection
username_name = quote_plus("bala")
password_password = quote_plus("bala123")
DATABASE_URL = f"mongodb+srv://{username_name}:{password_password}@cluster0.0z8bodb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "Courses"

# Initialize MongoDB client
client = MongoClient(DATABASE_URL)
db = client[DATABASE_NAME]
courses_collection = db["courses"]
enrollments_collection = db["enrollment"]

cart_collection=db["cartColl"]







# Pydantic models for request/response
class CourseBase(BaseModel):
    title: str
    description: str
    instructor: str
    duration_weeks: int
    price: float
    max_students: int = Field(gt=0)
    
class CourseCreate(CourseBase):
    pass

class Course(CourseBase):
    id: str
    current_enrollments: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True

class EnrollmentBase(BaseModel):
    student_name: str
    student_email: str
    course_id: str
    
class EnrollmentCreate(EnrollmentBase):
    pass

class Enrollment(EnrollmentBase):
    id: str
    enrollment_date: datetime
    status: str = "active"
    
    class Config:
        from_attributes = True

# Helper function to convert MongoDB _id to string
def convert_object_id(obj):
    obj["id"] = str(obj.pop("_id"))
    return obj

# Course endpoints
@router.post("/courses/", response_model=Course, status_code=status.HTTP_201_CREATED)
def create_course(course: CourseCreate):
    course_dict = course.dict()
    course_dict["created_at"] = datetime.utcnow()
    course_dict["current_enrollments"] = 0
    
    result = courses_collection.insert_one(course_dict)
    
    if result.inserted_id:
        course_dict["id"] = str(result.inserted_id)
        return course_dict
    raise HTTPException(status_code=400, detail="Failed to create course")




@router.post('/cart/', response_model=Course)
def add_to_cart(course: CourseCreate):
    # Create the course first
    course_dict = course.dict()
    course_dict["created_at"] = datetime.utcnow()  # Add created_at field
    course_dict["current_enrollments"] = 0  # Initialize current enrollments to 0
    
    # Insert the course into the courses collection
    result = courses_collection.insert_one(course_dict)
    
    if result.inserted_id:
        course_dict["id"] = str(result.inserted_id)
        
        # Add the course to the cart collection
        cart_result = cart_collection.insert_one(course_dict)
        
        if cart_result.inserted_id:
            # Return the course data, now in the cart collection as well
            return course_dict
        
    raise HTTPException(status_code=400, detail="Failed to add course to cart")



@router.get('/cart/', response_model=List[Course])
def get_cart_items():
    # Fetch all items from the cart collection
    cart_items = cart_collection.find()
    
    # Convert MongoDB cursor to list and serialize the objects
    return [course for course in cart_items]




# @app.delete('/cart/{course_id}', status_code=status.HTTP_200_OK)
# def delete_cart_item(course_id: str):
#     # Attempt to delete the item with the given ID
#     result = cart_collection.delete_one({"_id": ObjectId(course_id)})
    
#     if result.deleted_count == 1:
#         # Return a success message if deletion was successful
#         return {"message": f"Course with ID {course_id} has been deleted"}
    
#     raise HTTPException(status_code=404, detail="Course not found in cart")




@router.get("/courses/", response_model=List[Course])
def get_courses():
    courses = []
    cursor = courses_collection.find()
    for document in cursor:
        courses.append(convert_object_id(document))
    return courses

@router.get("/courses/{course_id}", response_model=Course)
def get_course(course_id: str):
    try:
        course = courses_collection.find_one({"_id": ObjectId(course_id)})
        if course:
            return convert_object_id(course)
        raise HTTPException(status_code=404, detail="Course not found")
    except:
        raise HTTPException(status_code=400, detail="Invalid course ID")

# Enrollment endpoints
@router.post("/enrollments/", response_model=Enrollment, status_code=status.HTTP_201_CREATED)
def create_enrollment(enrollment: EnrollmentCreate):
    # Check if course exists and has available spots
    course = courses_collection.find_one({"_id": ObjectId(enrollment.course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if course["current_enrollments"] >= course["max_students"]:
        raise HTTPException(status_code=400, detail="Course is full")
    
    # Check if student is already enrolled
    existing_enrollment = enrollments_collection.find_one({
        "student_email": enrollment.student_email,
        "course_id": enrollment.course_id
    })
    if existing_enrollment:
        raise HTTPException(status_code=400, detail="Student already enrolled in this course")
    
    # Create enrollment
    enrollment_dict = enrollment.dict()
    enrollment_dict["enrollment_date"] = datetime.utcnow()
    enrollment_dict["status"] = "active"
    
    result = enrollments_collection.insert_one(enrollment_dict)
    
    if result.inserted_id:
        # Update course enrollment count
        courses_collection.update_one(
            {"_id": ObjectId(enrollment.course_id)},
            {"$inc": {"current_enrollments": 1}}
        )
        
        enrollment_dict["id"] = str(result.inserted_id)
        return enrollment_dict
    
    raise HTTPException(status_code=400, detail="Failed to create enrollment")

@router.get("/enrollments/", response_model=List[Enrollment])
def get_enrollments(course_id: Optional[str] = None):
    query = {}
    if course_id:
        query["course_id"] = course_id
        
    enrollments = []
    cursor = enrollments_collection.find(query)
    for document in cursor:
        enrollments.append(convert_object_id(document))
    return enrollments

@router.get("/enrollments/{enrollment_id}", response_model=Enrollment)
def get_enrollment(enrollment_id: str):
    try:
        enrollment = enrollments_collection.find_one({"_id": ObjectId(enrollment_id)})
        if enrollment:
            return convert_object_id(enrollment)
        raise HTTPException(status_code=404, detail="Enrollment not found")
    except:
        raise HTTPException(status_code=400, detail="Invalid enrollment ID")
    
    
    

@router.delete('/cart/{course_id}', status_code=status.HTTP_200_OK)
def delete_cart_item(course_id: str):
    # Attempt to delete the item with the given ID
    result = cart_collection.delete_one({"_id": ObjectId(course_id)})
    
    if result.deleted_count == 1:
        # Return a success message if deletion was successful
        return {"message": f"Course with ID {course_id} has been deleted"}
    
    raise HTTPException(status_code=404, detail="Course not found in cart")


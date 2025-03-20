from typing import Optional, Dict, List
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
db = client["Quiz"]
collection = db["quiz"]

router = APIRouter(tags=["Quiz"], prefix="/quiz")

# Define the CreateQuiz model
class CreateQuiz(BaseModel):
    question: str
    options: Dict[str, str]
    answer: Optional[str] = None
    is_correct: Optional[bool] = False

# Define the response model for quiz creation
class QuizResponse(BaseModel):
    id: str
    question: str
    options: Dict[str, str]
    answer: str
    is_correct: bool

# Define the response model for fetching quizzes
class QuizListResponse(BaseModel):
    quizzes: List[QuizResponse]

# Create a new quiz
@router.post('/', response_model=QuizResponse)
async def create_quiz(new_quiz: CreateQuiz):
    try:
        # Insert the new quiz into the database
        result = collection.insert_one(new_quiz.dict())
        
        # Get the inserted quiz's ID
        quiz_id = str(result.inserted_id)
        
        # Fetch the newly created quiz from the database
        created_quiz = collection.find_one({"_id": ObjectId(quiz_id)})
        
        # Convert the quiz to a response model
        quiz_response = QuizResponse(
            id=quiz_id,
            question=created_quiz["question"],
            options=created_quiz["options"],
            answer=created_quiz["answer"],
            is_correct=created_quiz["is_correct"]
        )
        
        return JSONResponse(content=quiz_response.dict(), status_code=201)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create quiz: {str(e)}")

# Fetch all quizzes
@router.get('/', response_model=QuizListResponse)
async def get_all_quizzes():
    try:
        # Fetch all quizzes from the database
        quizzes = collection.find()
        
        # Convert quizzes to response model
        quiz_responses = []
        for quiz in quizzes:
            quiz_response = QuizResponse(
                id=str(quiz["_id"]),
                question=quiz["question"],
                options=quiz["options"],
                answer=quiz["answer"],
                is_correct=quiz["is_correct"]
            )
            quiz_responses.append(quiz_response)
        
        return JSONResponse(content=QuizListResponse(quizzes=quiz_responses).dict(), status_code=200)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch quizzes: {str(e)}")

# Fetch a quiz by ID
@router.get('/{quiz_id}', response_model=QuizResponse)
async def get_quiz(quiz_id: str):
    try:
        # Fetch the quiz from the database
        quiz = collection.find_one({"_id": ObjectId(quiz_id)})
        
        if quiz is None:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        # Convert the quiz to a response model
        quiz_response = QuizResponse(
            id=quiz_id,
            question=quiz["question"],
            options=quiz["options"],
            answer=quiz["answer"],
            is_correct=quiz["is_correct"]
        )
        
        return JSONResponse(content=quiz_response.dict(), status_code=200)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch quiz: {str(e)}")

# Example usage:
# GET /quiz
# Returns all quizzes

# GET /quiz/{quiz_id}
# Returns a quiz by ID

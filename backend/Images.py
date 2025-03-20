from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query,Path,APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson.objectid import ObjectId
from pydantic import BaseModel
from datetime import datetime
from urllib.parse import quote_plus
from typing import List, Optional, Dict
from enum import Enum
import shutil
import os
import uuid
from fastapi.staticfiles import StaticFiles

# Database configuration remains the same
username_name = quote_plus("bala")
password_password = quote_plus("bala123")
DATABASE_URL = f"mongodb+srv://{username_name}:{password_password}@cluster0.0z8bodb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

router = APIRouter(tags=["Images"], prefix="/images")
router.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
# MongoDB connection
client = MongoClient(DATABASE_URL)
db = client.Library

collection1 = db.visuals
collection2 = db.category



# class LanguageEnum(IntEnum):
#     ENGLISH = 1
#     TELUGU = 2
#     HINDI = 3
#     TAMIL = 4

class LanguageEnum(str, Enum):
    TELUGU = "Telugu"
    HINDI = "Hindi"
    TAMIL = "Tamil"

# Modified upload endpoint to handle category references
@router.post("/upload/")
async def create_visual(
    category_name: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        # First, find the existing category
        category = collection2.find_one({"category": category_name})
        if not category:
            raise HTTPException(status_code=404, detail=f"Category '{category_name}' not found")

        file_location = f"uploads/{quote_plus(file.filename)}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        image_url = f"http://localhost:8000/uploads/{quote_plus(file.filename)}"
        
        # Generate visual_id
        visual_id = str(uuid.uuid4())
        
        # Insert visual with category reference
        visual_doc = {
            "visual_id": visual_id,
            "category_id": category["category_id"],  # Reference to category
            "category_name": category_name,
            "title": title,
            "description": description,
            "image_url": image_url,
            "uploaded_date": datetime.now().isoformat()
        }
        
        collection1.insert_one(visual_doc)
        return {
            "message": "Image uploaded successfully", 
            "visual_id": visual_id,
            "category_id": category["category_id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/coverPage/")
async def create_category(
    category: str = Form(...),
    language: str = Form(...),
    local_name: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        # Check if category already exists
        existing_category = collection2.find_one({"category": category, "language": language})
        if existing_category:
            raise HTTPException(status_code=400, detail=f"Category '{category}' already exists for language '{language}'")

        file_location = f"uploads/{file.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        image_url = f"http://localhost:8000/uploads/{file.filename}"
        
        # Generate category_id
        category_id = str(uuid.uuid4())
        
        category_doc = {
            "category_id": category_id,
            "category": category,
            "local_name": local_name,
            "language": language,
            "image_url": image_url,
            "uploaded_date": datetime.now().isoformat()
        }
        
        collection2.insert_one(category_doc)
        return {"message": "Category created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# Modified get images endpoint to include category information
@router.get("/images/", response_model=List[dict])
async def get_images(category_name: Optional[str] = Query(None, description="Filter by category or get all")):
    try:
        query = {"category_name": category_name} if category_name else {}

        images = list(collection1.find(query))
        if not images:
            return []

        result = [
            {
                "id": str(image["_id"]),
                "visual_id": image.get("visual_id", ""),
            "language": image.get("language", ""),
                
                "category_id": image.get("category_id", ""),
                "title": image.get("title", ""),
                "description": image.get("description", ""),
                "category_name": image.get("category_name", ""),
                "image_url": image.get("image_url", ""),
                "uploaded_date": image.get("uploaded_date", ""),
            }
            for image in images
        ]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching images: {str(e)}")

# Other endpoints remain the same...

@router.get("/images/", response_model=List[dict])
async def get_images(category_name: Optional[str] = Query(None, description="Filter by category or get all")):
    try:
        query = {"category_name": category_name} if category_name else {}

        images = list(collection1.find(query))
        if not images:
            return []

        result = [
            {
                "id": str(image["_id"]),
                "visual_id": image.get("visual_id", ""),
                "title": image.get("title", ""),
                "description": image.get("description", ""),
                "category_name": image.get("category_name", ""),
                "image_url": image.get("image_url", ""),
                "uploaded_date": image.get("uploaded_date", ""),
                "language": image.get("language", ""),
                
            }
            for image in images
        ]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching images: {str(e)}")

@router.get("/languages", response_model=List[str])
async def get_languages():
    return [lang.value for lang in LanguageEnum]

@router.get("/categories/", response_model=List[str])
async def get_categories_language_wise(language: str = Query(..., description="Filter categories by language")):
    try:
        categories = collection2.find({"language": language}, {"_id": 0, "category": 1})
        return [category["category"] for category in categories]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")
    
    
# # GET API: Fetch Only Category Names
# @app.get("/category-names/", response_model=List[str])
# async def get_category_names():
#     try:
#         # Find distinct category names
#         category_names = collection.distinct("category_name")

#         if not category_names:
#             raise HTTPException(status_code=404, detail="No categories found")

#         return category_names

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")




@router.get("/coverpage/", response_model=List[dict])
async def get_images(language: Optional[str] = Query(None, description="Filter by category or get all categories")):
    try:
        query_filter = {} if not language else {"language": language}
        
        categories = list(collection2.find(query_filter))
        
        result = []
        
        for category in categories:
            item_count = collection1.count_documents({"category_name": category["category"]})
            
            category_images = list(collection1.find(
                {"category_name": category["category"]},
                {
                    "_id": 0,
                    "visual_id": 1,
                    "title": 1,
                    "language": 1,
                    "description": 1,
                    "image_url": 1,
                    "uploaded_date": 1
                }
            ))
            
            category_data = {
                "_id": str(category["_id"]),  # Add this line to include MongoDB _id
                "category_id": category.get("category_id"),
                "category": category.get("category"),
                "local_name": category.get("local_name"),
                "language": category.get("language"),
                "cover_image": category.get("image_url"),
                "item_count": item_count,
                "images": category_images
            }
            
            result.append(category_data)
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")
    
    
    
    

@router.put("/category/{category_id}")
async def update_category(
    category_id: str,
    category: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    local_name: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    try:
        # Check if category exists
        existing_category = collection2.find_one({"category_id": category_id})
        if not existing_category:
            raise HTTPException(status_code=404, detail=f"Category with ID '{category_id}' not found")

        # If updating category name or language, check for duplicates
        if category or language:
            query = {
                "category_id": {"$ne": category_id},  # Exclude current category
                "category": category if category else existing_category["category"],
                "language": language if language else existing_category["language"]
            }
            if collection2.find_one(query):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Category already exists with this name and language combination"
                )

        # Prepare update document
        update_doc = {}
        
        if category:
            update_doc["category"] = category
        if language:
            update_doc["language"] = language
        if local_name:
            update_doc["local_name"] = local_name

        # Handle file upload if provided
        if file:
            # Delete old file if it exists
            old_file_path = existing_category["image_url"].replace("http://localhost:8000/uploads/", "uploads/")
            if os.path.exists(old_file_path):
                os.remove(old_file_path)

            # Save new file
            file_location = f"uploads/{file.filename}"
            with open(file_location, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            image_url = f"http://localhost:8000/uploads/{file.filename}"
            update_doc["image_url"] = image_url

        # Update timestamp
        update_doc["updated_date"] = datetime.now().isoformat()

        # Update the document
        result = collection2.update_one(
            {"category_id": category_id},
            {"$set": update_doc}
        )

        if result.modified_count == 0:
            return {"message": "No changes were made"}
            
        return {"message": "Category updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
    
    



@router.put("/visual/{visual_id}")
async def update_visual(
    visual_id: str,
    category_name: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    try:
        # First, check if the visual exists
        existing_visual = collection1.find_one({"visual_id": visual_id})
        if not existing_visual:
            raise HTTPException(status_code=404, detail=f"Visual with ID '{visual_id}' not found")

        # Prepare update document
        update_doc = {}

        # Update category if provided
        if category_name:
            category = collection2.find_one({"category": category_name})
            if not category:
                raise HTTPException(status_code=404, detail=f"Category '{category_name}' not found")
            update_doc["category_id"] = category["category_id"]
            update_doc["category_name"] = category_name

        # Update other fields if provided
        if title:
            update_doc["title"] = title
        if description:
            update_doc["description"] = description

        # Handle file upload if provided
        if file:
            # Delete old file if it exists
            old_file_path = existing_visual["image_url"].replace("http://localhost:8000/uploads/", "uploads/")
            if os.path.exists(old_file_path):
                os.remove(old_file_path)

            # Save new file
            file_location = f"uploads/{quote_plus(file.filename)}"
            with open(file_location, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            image_url = f"http://localhost:8000/uploads/{quote_plus(file.filename)}"
            update_doc["image_url"] = image_url

        # Update timestamp
        update_doc["updated_date"] = datetime.now().isoformat()

        # Update the document
        result = collection1.update_one(
            {"visual_id": visual_id},
            {"$set": update_doc}
        )

        if result.modified_count == 0:
            return {"message": "No changes were made"}
        
        return {"message": "Visual updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
    
    



from bson import ObjectId

@router.delete("/visual/{visual_id}")
async def delete_visual(visual_id: str = Path(..., description="The ID of the visual to delete")):
    try:
        # Convert visual_id to ObjectId
        object_id = ObjectId(visual_id)
        
        # Find the visual first
        visual = collection1.find_one({"_id": object_id})
        if not visual:
            raise HTTPException(status_code=404, detail=f"Visual with ID '{visual_id}' not found")

        # Delete the associated file
        if "image_url" in visual:
            file_path = visual["image_url"].replace("http://localhost:8000/uploads/", "uploads/")
            if os.path.exists(file_path):
                os.remove(file_path)

        # Delete the database record
        result = collection1.delete_one({"_id": object_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=500, detail="Failed to delete visual from database")

        return {"message": "Visual deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")






@router.delete("/category/{category_id}")
async def delete_category(category_id: str = Path(..., description="The ID of the category to delete")):
    try:
        object_id = ObjectId(category_id)
        category = collection2.find_one({"_id": object_id})
        if not category:
            raise HTTPException(status_code=404, detail=f"Category with ID '{category_id}' not found")

        # Check if any visuals are associated with this category
        visuals_count = collection1.count_documents({"category_id": category_id})
        if visuals_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete category: {visuals_count} visual(s) are still associated with this category."
            )

        # Delete category cover image
        if "image_url" in category:
            file_path = category["image_url"].replace("http://localhost:8000/uploads/", "uploads/")
            if os.path.exists(file_path):
                os.remove(file_path)

        # Delete category record
        result = collection2.delete_one({"_id": object_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=500, detail="Failed to delete category from database")

        return {"message": "Category deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
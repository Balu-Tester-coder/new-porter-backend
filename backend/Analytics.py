from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from pymongo import MongoClient
from urllib.parse import quote_plus  # Added missing import
from bson import ObjectId

# Initialize FastAPI app
app = FastAPI(title="Learning Management System API")

# MongoDB Atlas connection
username_name = quote_plus("bala")
password_password = quote_plus("bala123")
DATABASE_URL = f"mongodb+srv://{username_name}:{password_password}@cluster0.0z8bodb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "retail_analytics"

# Initialize MongoDB client
client = MongoClient(DATABASE_URL)
database = client[DATABASE_NAME]

# Pydantic models
class Product(BaseModel):
    name: str
    category: str
    price: float
    stock: int
    supplier: str
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # Add configuration for ObjectId handling
    class Config:
        json_encoders = {
            ObjectId: str
        }
        arbitrary_types_allowed = True

class Order(BaseModel):
    customer_id: str
    products: List[str]  # List of product IDs
    total_amount: float
    status: str
    order_date: datetime = Field(default_factory=datetime.utcnow)
    
    # Add configuration for ObjectId handling
    class Config:
        json_encoders = {
            ObjectId: str
        }
        arbitrary_types_allowed = True

@app.post("/products/", response_model=Product)
def create_product(product: Product):
    """Create a new product in the database."""
    product_dict = product.dict()
    result = database.products.insert_one(product_dict)
    created_product = database.products.find_one({"_id": result.inserted_id})
    # Convert ObjectId to string for the _id field
    if created_product:
        created_product["_id"] = str(created_product["_id"])
    return created_product


@app.get("/products")
def get_category_wise_no_of_stocks(category: Optional[str] = None):
    if category is None:
        # Group all categories and return stock count
        pipeline = [
            {
                "$group": {
                    "_id": "$category",
                    "noofStocksCategoryWise": {
                        "$sum": "$stock"
                    }
                }
            }
        ]
    else:
        # Filter by the specified category and group
        pipeline = [
            {
                "$match": {"category": category}
            },
            {
                "$group": {
                    "_id": "$category",
                    "noofStocksCategoryWise": {
                        "$sum": "$stock"
                    }
                }
            }
        ]

    result = list(database.products.aggregate(pipeline))
    return result
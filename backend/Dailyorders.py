from typing import List, Annotated, Optional
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Query,APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson.objectid import ObjectId
from pydantic import BaseModel, Field
from urllib.parse import quote_plus


# Database configuration
username_name = quote_plus("bala")
password_password = quote_plus("bala123")
DATABASE_URL = f"mongodb+srv://{username_name}:{password_password}@cluster0.0z8bodb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

router = APIRouter(tags=["Dailyorders"], prefix="/dailyorders")

# MongoDB connection
client = MongoClient(DATABASE_URL)
db = client.Products
collection = db.orders





# Pydantic models for response data
class ProductDetail(BaseModel):
    productId: str
    productName: str
    quantity: int
    revenue: float
    averagePrice: float
    orderCount: int

class DailyMetrics(BaseModel):
    totalRevenue: float
    totalOrders: int
    uniqueProducts: int
    averageRevenuePerProduct: float

class DailyOrderResponse(BaseModel):
    date: str
    dailyMetrics: DailyMetrics
    #products: List[ProductDetail]
    
    
    
@router.get("/api/daily-orders", response_model=List[dict])
async def get_daily_orders(start_date: Optional[datetime] = Query(None)):
    try:
        # Build date filter if a date is provided
        date_filter = {}
        if start_date:
            date_filter = {
                "orderDate": {"$eq": start_date}
            }

        # Aggregation pipeline
        pipeline = [
            *([{"$match": date_filter}] if date_filter else []),
            {"$unwind": "$items"},
            {
                "$group": {
                    "_id": {
                        "date": {
                            "$dateToString": {"format": "%Y-%m-%d", "date": "$orderDate"}
                        },
                        "productId": "$items.productId",
                        "productName": "$items.name"
                    },
                    "totalQuantity": {"$sum": "$items.quantity"},
                    "totalRevenue": {"$sum": {"$multiply": ["$items.price", "$items.quantity"]}},
                    "averagePrice": {"$avg": "$items.price"},
                    "numberOfOrders": {"$sum": 1}
                }
            },
            {
                "$group": {
                    "_id": "$_id.date",
                    "items": {
                        "$push": {
                            "productId": "$_id.productId",
                            "productName": "$_id.productName",
                            "quantity": "$totalQuantity",
                            "revenue": "$totalRevenue",
                            "averagePrice": "$averagePrice",
                            "orderCount": "$numberOfOrders"
                        }
                    },
                    "dailyTotalRevenue": {"$sum": "$totalRevenue"},
                    "dailyTotalOrders": {"$sum": "$numberOfOrders"},
                    "uniqueProducts": {"$sum": 1}
                }
            },
            {
                "$addFields": {
                    "averageRevenuePerProduct": {
                        "$cond": {
                            "if": {"$eq": ["$uniqueProducts", 0]},
                            "then": 0,
                            "else": {"$divide": ["$dailyTotalRevenue", "$uniqueProducts"]}
                        }
                    }
                }
            },
            {"$sort": {"_id": 1}},
            {
                "$project": {
                    "_id": 0,
                    "date": "$_id",
                    "dailyMetrics": {
                        "totalRevenue": {"$round": ["$dailyTotalRevenue", 2]},
                        "totalOrders": "$dailyTotalOrders",
                        "uniqueProducts": "$uniqueProducts",
                        "averageRevenuePerProduct": {"$round": ["$averageRevenuePerProduct", 2]}
                    }
                }
            }
        ]

        # Execute aggregation
        results = list(collection.aggregate(pipeline))

        return results if results else []  # Return empty list instead of 404

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Optional: Add an endpoint for getting orders for a specific date
@router.get("/api/daily-orders/{date}")
async def get_daily_orders_by_date(date: str):
    try:
        # Convert string date to datetime for comparison
        target_date = datetime.strptime(date, "%Y-%m-%d")
        next_date = datetime(target_date.year, target_date.month, target_date.day + 1)

        # Define the pipeline
        pipeline = [
            {
                "$match": {
                    "orderDate": {"$gte": target_date, "$lt": next_date}
                }
            },
            { "$unwind": "$items" },
            {
                "$group": {
                    "_id": "$items.productId",
                    "productName": { "$first": "$items.name" },
                    "totalQuantitySold": { "$sum": "$items.quantity" },
                    "totalRevenue": { "$sum": { "$multiply": ["$items.price", "$items.quantity"] } },
                    "ordersCount": { "$sum": 1 }
                }
            },
            {
                "$addFields": {
                    "averageOrderValue": { "$divide": ["$totalRevenue", "$ordersCount"] }
                }
            },
            { "$sort": { "totalRevenue": -1 } },
            {
                "$project": {
                    "_id": 1,
                    "productName": 1,
                    "totalQuantitySold": 1,
                    "totalRevenue": 1,
                    "averageOrderValue": 1
                }
            }
        ]

        # Execute the pipeline
        results = list(collection.aggregate(pipeline))

        if not results:
            return JSONResponse(
                status_code=404,
                content={"message": f"No orders found for date {date}"}
            )

        return {"date": date, "orders": results}  # Return structured response

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Please use YYYY-MM-DD"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching orders: {str(e)}"
        )
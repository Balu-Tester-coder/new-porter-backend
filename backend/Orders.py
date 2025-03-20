from fastapi import FastAPI, Query, HTTPException, Depends, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient, ReturnDocument
from bson.objectid import ObjectId
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ValidationError
from enum import Enum
import re
from urllib.parse import quote_plus

# Initialize FastAPI app

router = APIRouter(tags=["Orders"], prefix="/orders")

# MongoDB Connection Setup
username_name = quote_plus("bala")
password_password = quote_plus("bala123")
DATABASE_URL = f"mongodb+srv://{username_name}:{password_password}@cluster0.0z8bodb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# MongoDB client setup
client = MongoClient(DATABASE_URL)
db = client.Flipkart
collection_products = db.Products
collection_orders = db.orders
collection_customers = db.customers
collection_product_counter = db.product_counter 
collection_customers_counter = db.customers_counter
cart_collection=db.CartCollection



# Enums for Categories and Status
class MainCategory(str, Enum):
    
    MEN = "men"
    WOMEN = "women"
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    COSMETICS = "cosmetics"



class BrandEnum(str, Enum):
    nike = "Nike"
    adidas = "Adidas"
    puma = "Puma"
    reebok = "Reebok"
    denim = "Denim"


# Define response model for better documentation
class SubcategoryResponse(BaseModel):
    main_category: str
    subcategories: List[str]
    total_count: int
    
    
    
    
class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"

class ClothingSize(str, Enum):
    XS = "XS"
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"
    XXL = "XXL"

class ShoeSize(str, Enum):
    UK_6 = "UK6"
    UK_7 = "UK7"
    UK_8 = "UK8"
    UK_9 = "UK9"
    UK_10 = "UK10"
    UK_11 = "UK11"

# Subcategories mapping
SUBCATEGORIES = {
    "men": ["shirts", "pants", "suits", "accessories", "shoes", "sportswear"],
    "women": ["dresses", "tops", "pants", "accessories", "shoes", "ethnic_wear","Saree"],
    "electronics": ["smartphones", "laptops", "accessories", "audio", "gaming"],
    "clothing": ["casual", "formal", "ethnic", "sports", "winter_wear"],
    "cosmetics": ["skincare", "makeup", "haircare", "fragrance", "beauty_tools"]
}

# Base Models
class Address(BaseModel):
    street: str
    city: str
    state: str
    country: str
    postal_code: str
    is_primary: bool = True
    address_type: str = "home"

class ProductReview(BaseModel):
    rating: float = Field(ge=1, le=5)
    comment: Optional[str]
    user_id: str
    created_at: datetime
    helpful_votes: int = 0
    verified_purchase: bool = False
    images: List[str] = []

class ProductSpecification(BaseModel):   
    key: str
    value: str
    unit: Optional[str]
    filterable: bool = False

class ProductVariant(BaseModel):
    variant_id: Optional[str] = None
    color: Optional[str]
    size: Optional[str]
    weight: Optional[float] = Field(ge=0)
    price_adjustment: float = Field(ge=0)
    stock: int = Field(ge=0)
    images: List[str] = []
   

class OrderItem(BaseModel):
    product_id: str
    product_name: str
    category: MainCategory
    sub_category: str
    variant_id: str
    price: float = Field(ge=0)
    quantity: int = Field(ge=1)
    discount: float = Field(ge=0)
    tax: float = Field(ge=0)
    status: OrderStatus = OrderStatus.PENDING

class Payment(BaseModel):
    payment_id: Optional[str]
    payment_intent_id: Optional[str]
    method: str
    amount: float = Field(ge=0)
    status: PaymentStatus
    transaction_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    gateway: str = "stripe"
    currency: str = "usd"
    error_message: Optional[str]

class Order(BaseModel):
    order_id: str
    customer_id: str
    order_date: datetime
    items: List[OrderItem]
    total_amount: float = Field(ge=0)
    shipping_address: Address
    billing_address: Optional[Address]
    payment: Payment
    status: OrderStatus
    tracking_number: Optional[str]
    notes: Optional[str]
    estimated_delivery: Optional[datetime]
    shipping_method: str
    shipping_carrier: Optional[str]

class Product(BaseModel):
    product_id: Optional[str] = None
    name: str
    description: str
    category: MainCategory
    sub_category: str
    base_price: float = Field(ge=0)
    current_price: float = Field(ge=0)
    brand: str
    specifications: List[ProductSpecification]
    variants: List[ProductVariant]
    reviews: List[ProductReview]
    avg_rating: float = 0
    total_reviews: int = 0
    stock: int = Field(ge=0)
    created_at: Optional[datetime]
    updated_at: datetime
    tags: List[str] = []
    is_active: bool = True
    
    search_keywords: List[str] = []

class Customer(BaseModel):
    customer_id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    addresses: List[Address]
    created_at: datetime
    last_login: Optional[datetime]
    total_orders: int = 0
    total_spent: float = 0
    preferences: Dict[str, List[str]] = {}
    marketing_consent: bool = False
    wishlist: List[str] = []
    recently_viewed: List[str] = []
    account_status: str = "active"
    notifications_enabled: bool = True
    
    
class CartItem(BaseModel):
    product_id: str
    name: str
    description: str
    category: MainCategory
    sub_category: str
    base_price: float
    current_price: float
    brand: str
    variant_id: str = "default_variant"  # Set default value
    quantity: int = Field(ge=1)
    added_at: Optional[datetime]
    specifications: List[ProductSpecification] = []
    variants: List[ProductVariant] = []
    stock: int = Field(ge=0)
    is_active: bool = True


class Cart(BaseModel):
    
    items: List[CartItem]
    last_updated: Optional[datetime]
    
    
    
# Add to Cart Request Model
class AddToCartRequest(BaseModel):
    
    product_id: str
 
# Helper function to convert MongoDB results and datetime to JSON serializable format
def serialize_mongo_doc(doc):
    if isinstance(doc, dict):
        return {k: serialize_mongo_doc(v) for k, v in doc.items()}
    elif isinstance(doc, list):
        return [serialize_mongo_doc(item) for item in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    elif isinstance(doc, datetime):
        return doc.isoformat()
    else:
        return doc

# Database Index Creation
def create_indexes():
    try:
        collection_products.create_index([("category", 1)])
        collection_products.create_index([("sub_category", 1)])
        collection_products.create_index([("name", "text"), ("description", "text"), ("search_keywords", "text")])
        collection_products.create_index([("current_price", 1)])
        collection_products.create_index([("brand", 1)])
        collection_orders.create_index([("customer_id", 1)])
        collection_orders.create_index([("order_date", -1)])
        collection_customers.create_index([("email", 1)], unique=True)
    except Exception as e:
        print(f"Error creating indexes: {e}")

# Create indexes on startup
create_indexes()

# API Endpoints
@router.post("/products/", response_model=Product)
async def create_product(product: Product):
    try:
        sequence = collection_product_counter.find_one_and_update(
            {"_id": "product_counter"},
            {"$inc": {"counter": 1}},
            upsert=True,
            return_document=True
        )
        
        product.product_id = f"PROD{str(sequence['counter']).zfill(3)}"
        product.created_at = datetime.utcnow()
        product.updated_at = datetime.utcnow()
        
        collection_products.insert_one(product.dict())
        return product
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/customers/", response_model=Customer)
async def create_customer(customer: Customer):
    try:
        sequence = collection_customers_counter.find_one_and_update(
            {"_id": "customers_counter"},
            {"$inc": {"counter": 1}},
            upsert=True,
            return_document=True
        )
        
        customer.customer_id = f"CUST{str(sequence['counter']).zfill(3)}"
        customer.created_at = datetime.utcnow()
        
        collection_customers.insert_one(customer.dict())
        return customer
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 


@router.get("/categories/main")
async def get_main_categories():
    
    return {"categories": [category.value for category in MainCategory]}
    

# Modified filter_products endpoint
@router.get("/products/filter")
async def filter_products(
    main_category: MainCategory,
    subcategory_search: Optional[str] = None,
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = None,
    sort_by: Optional[str] = Query("name", enum=["name", "price", "rating"]),
    sort_order: Optional[str] = Query("asc", enum=["asc", "desc"]),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    try:
        if min_price is not None and max_price is not None and min_price > max_price:
            raise HTTPException(
                status_code=400,
                detail="min_price cannot be greater than max_price"
            )

        pipeline = []
        pipeline.append({"$match": {"category": main_category}})
        
        if subcategory_search:
            pipeline.append({
                "$match": {
                    "sub_category": {
                        "$regex": re.escape(subcategory_search),
                        "$options": "i"
                    }
                }
            })
        
        if min_price is not None or max_price is not None:
            price_match = {}
            if min_price is not None:
                price_match["$gte"] = min_price
            if max_price is not None:
                price_match["$lte"] = max_price
            if price_match:
                pipeline.append({"$match": {"current_price": price_match}})
        
        count_pipeline = pipeline.copy()
        count_pipeline.append({"$count": "total"})
        
        total_count = list(collection_products.aggregate(count_pipeline))
        total_products = total_count[0]["total"] if total_count else 0
        
        pipeline.append({
            "$sort": {sort_by: 1 if sort_order == "asc" else -1}
        })
        
        pipeline.extend([
            {"$skip": (page - 1) * page_size},
            {"$limit": page_size}
        ])
        
        products = list(collection_products.aggregate(pipeline))
        
        # Serialize MongoDB documents including datetime
        serialized_products = serialize_mongo_doc(products)
        
        response_data = {
            "products": serialized_products,
            "pagination": {
                "current_page": page,
                "total_pages": (total_products + page_size - 1) // page_size,
                "total_products": total_products,
                "page_size": page_size
            },
            "filters": {
                "main_category": main_category,
                "subcategory_search": subcategory_search,
                "price_range": {
                    "min": min_price,
                    "max": max_price
                }
            },
            "sorting": {
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        }
        
        return JSONResponse(content=response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Apply the same serialization to other endpoints that return MongoDB documents
@router.get("/products/search")
async def search_products(
    query: str = Query(..., min_length=1),
    
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    try:
        pipeline = [
            {
                "$match": {
                    "$or": [
                        {"name": {"$regex": re.escape(query), "$options": "i"}},
                        {"description": {"$regex": re.escape(query), "$options": "i"}},
                        {"search_keywords": {"$regex": re.escape(query), "$options": "i"}},
                        {"brand": {"$regex": re.escape(query), "$options": "i"}}
                    ]
                }
            }
        ]

         

        count_pipeline = pipeline.copy()
        count_pipeline.append({"$count": "total"})
        
        total_count = list(collection_products.aggregate(count_pipeline))
        total_products = total_count[0]["total"] if total_count else 0

        pipeline.extend([
            {"$skip": (page - 1) * page_size},
            {"$limit": page_size}
        ])

        products = list(collection_products.aggregate(pipeline))
        serialized_products = serialize_mongo_doc(products)

        response_data = {
            "products": serialized_products,
            "total": total_products,
            "page": page,
            "pages": (total_products + page_size - 1) // page_size
        }

        return JSONResponse(content=response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories/all")
async def get_all_categories():
    try:
        return {
            "categories": [
                {
                    "main_category": category,
                    "subcategories": SUBCATEGORIES[category],
                    "total_subcategories": len(SUBCATEGORIES[category])
                }
                for category in MainCategory
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving categories: {str(e)}"
        )
   
#get products

@router.get("/products/all")
async def get_all_products():
    try:
        # Simply get all products from collection
        products = list(collection_products.find())
        
        # Serialize the products to handle ObjectId and datetime
        serialized_products = serialize_mongo_doc(products)
        
        return JSONResponse(content={
            "status": "success",
            "products": serialized_products,
            "total_products": len(serialized_products)
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving products: {str(e)}"
        )
# Optional: Add an endpoint to get a single product by ID
@router.get("/products/{product_id}")
async def get_product_by_id(product_id: str):
    try:
        # Find the product by ID
        product = collection_products.find_one({"product_id": product_id})
        
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product with ID {product_id} not found"
            )

        # Serialize the product
        serialized_product = serialize_mongo_doc(product)

        return JSONResponse(content={
            "status": "success",
            "data": serialized_product
        })

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving product: {str(e)}"
        )
    
    


@router.get("/products/filter")
async def filter_products(
    main_category: MainCategory,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    try:
        pipeline = []
        pipeline.append({"$match": {"category": main_category}})

        count_pipeline = pipeline.copy()
        count_pipeline.append({"$count": "total"})

        total_count = list(collection_products.aggregate(count_pipeline))
        total_products = total_count[0]["total"] if total_count else 0

        pipeline.extend([
            {"$skip": (page - 1) * page_size},
            {"$limit": page_size}
        ])

        products = list(collection_products.aggregate(pipeline))

        # Serialize MongoDB documents including datetime
        serialized_products = serialize_mongo_doc(products)

        response_data = {
            "products": serialized_products,
            "pagination": {
                "current_page": page,
                "total_pages": (total_products + page_size - 1) // page_size,
                "total_products": total_products,
                "page_size": page_size
            },
            "filters": {
                "main_category": main_category
            }
        }

        return JSONResponse(content=response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/cart/add", response_model=Cart)
async def add_to_cart(request: AddToCartRequest):
    try:
        # Verify product exists
        product = collection_products.find_one({"product_id": request.product_id})
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product with ID {request.product_id} not found"
            )
        
        current_time = datetime.utcnow()
        
        # Prepare the cart item with required fields
        cart_item = {
            "product_id": product["product_id"],
            "name": product["name"],
            "description": product["description"],
            "category": product["category"],
            "sub_category": product["sub_category"],
            "base_price": product["base_price"],
            "current_price": product["current_price"],
            "brand": product["brand"],
            "variant_id": "default_variant",  # Set default variant
            "specifications": product.get("specifications", []),
            "variants": product.get("variants", []),
            "stock": product.get("stock", 0),
            "is_active": product.get("is_active", True),
            "quantity": 1,
            "added_at": current_time
        }
        
        # Try to find the existing cart, if none found, create a new one
        updated_cart = cart_collection.find_one_and_update(
            {},  # No filter, update the first cart or create a new one
            {
                "$push": {"items": cart_item},
                "$set": {"last_updated": current_time}
            },
            upsert=True,  # Create a new cart if it doesn't exist
            return_document=ReturnDocument.AFTER  # Return the updated cart
        )

        if not updated_cart:
            raise HTTPException(status_code=404, detail="Cart not found after update")
        
        # Serialize the cart before returning
        serialized_cart = serialize_mongo_doc(updated_cart)
        
        # Create and validate Cart model instance before returning
        return Cart(**serialized_cart)
        
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        print("Error occurred:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
    
    
@router.get("/cart")
async def get_cart():
    try:
        # Fetch all carts (without filtering by customer_id)
        carts = cart_collection.find()
        
        # Enrich cart items with product details for each cart
        enriched_carts = []
        for cart in carts:
            enriched_items = []
            for item in cart["items"]:
                product = collection_products.find_one({"product_id": item["product_id"]})
                if product:
                    enriched_item = {
                        **item,
                        "product_name": product["name"],
                        "price": product["current_price"],
                        "brand": product["brand"]
                    }
                    if item.get("variant_id"):
                        for variant in product.get("variants", []):
                            if variant["variant_id"] == item["variant_id"]:
                                enriched_item["variant_details"] = variant
                                break
                    enriched_items.append(enriched_item)
            
            cart["items"] = enriched_items
            enriched_carts.append(serialize_mongo_doc(cart))
        
        return enriched_carts
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#order items
@router.delete("/cart/{item_id}")
async def delete_from_cart(item_id: str):
    try:
        current_time = datetime.utcnow()
        
        # Try to find and update the cart by removing the specified item
        updated_cart = cart_collection.find_one_and_update(
            {},  # No filter, update the first cart found
            {
                "$pull": {"items": {"product_id": item_id}},
                "$set": {"last_updated": current_time}
            },
            return_document=ReturnDocument.AFTER
        )
        
        if not updated_cart:
            raise HTTPException(
                status_code=404,
                detail=f"Cart not found or item with ID {item_id} not in cart"
            )
        
        # If the cart is now empty, you might want to delete it entirely
        if len(updated_cart.get("items", [])) == 0:
            cart_collection.delete_one({})
            return {"message": "Cart deleted successfully"}
            
        # Serialize the cart before returning
        serialized_cart = serialize_mongo_doc(updated_cart)
        
        # Create and validate Cart model instance before returning
        return Cart(**serialized_cart)
        
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        print("Error occurred:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint to delete entire cart
@router.delete("/cart")
async def delete_entire_cart():
    try:
        # Delete the cart
        result = cart_collection.delete_one({})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail="No cart found to delete"
            )
            
        return {"message": "Cart deleted successfully"}
        
    except Exception as e:
        print("Error occurred:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.post("/orders/", response_model=Order)
async def create_order(order: Order):
    try:
        # Start a session for atomic operations
        with client.start_session() as session:
            with session.start_transaction():
                # Check stock availability for all items
                for item in order.items:
                    product = collection_products.find_one(
                        {"product_id": item.product_id},
                        session=session
                    )
                    
                    if not product:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Product {item.product_id} not found"
                        )
                        
                    if product["stock"] < item.quantity:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Insufficient stock for product {item.product_id}"
                        )
                
                # Generate order ID
                sequence = collection_orders.find_one_and_update(
                    {"_id": "order_counter"},
                    {"$inc": {"counter": 1}},
                    upsert=True,
                    return_document=True,
                    session=session
                )
                
                order.order_id = f"ORD{str(sequence['counter']).zfill(5)}"
                order.order_date = datetime.utcnow()
                order.status = OrderStatus.PENDING

                # Calculate total amount
                total_amount = sum(
                    (item.price - item.discount + item.tax) * item.quantity
                    for item in order.items
                )
                order.total_amount = total_amount

                # Update stock levels
                for item in order.items:
                    collection_products.update_one(
                        {"product_id": item.product_id},
                        {"$inc": {"stock": -item.quantity}},
                        session=session
                    )

                # Create order
                collection_orders.insert_one(
                    order.dict(by_alias=True),
                    session=session
                )

                # Update customer statistics
                collection_customers.update_one(
                    {"customer_id": order.customer_id},
                    {
                        "$inc": {
                            "total_orders": 1,
                            "total_spent": total_amount
                        },
                        "$set": {"last_login": datetime.utcnow()}
                    },
                    session=session
                )

                # Clear customer's cart
                cart_collection.delete_one(
                    {"customer_id": order.customer_id},
                    session=session
                )

        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
    
    
    

@router.get("/products/")
async def search_brandWise(brand: Optional[BrandEnum] = None):
    query = {}
    if brand:
        query["brand"] = brand.value

    products = list(collection_products.find(query, {"_id": 0}))
    return {"products": products}




@router.get("/brands-by-category/")
async def get_brands_by_category():
    """
    Fetch brand names grouped by their respective main categories.
    """
    # Aggregate MongoDB pipeline to group brands by main categories
    pipeline = [
        {
            "$group": {
                "_id": "$category",  # Group by category
                "brands": {"$addToSet": "$brand"}  # Collect unique brands for each category
            }
        },
        {
            "$project": {
                "_id": 0,  # Exclude the MongoDB _id field
                "category": "$_id",
                "brands": 1
            }
        }
    ]

    # Execute the aggregation pipeline
    result = list(collection_products.aggregate(pipeline))

    # Convert result to dictionary
    response = {item["category"]: item["brands"] for item in result}
    return response



@router.get("/api/products/filter")
async def filter_products(
    main_category: Optional[str] = Query(None),
    brands: Optional[List[str]] = Query(None),
    subcategories: Optional[List[str]] = Query(None),
    colors: Optional[List[str]] = Query(None),  # Add colors parameter
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    sort_by: Optional[str] = Query("current_price"),
    sort_order: Optional[str] = Query("asc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    try:
        query = {}
        
        if main_category:
            query["category"] = main_category
            
        if brands:
            query["brand"] = {"$in": brands}
            
        if subcategories:
            query["sub_category"] = {"$in": subcategories}
            
        # Add color filter
        if colors:
            query["variants.color"] = {"$in": colors}
            
        if min_price is not None or max_price is not None:
            price_query = {}
            if min_price is not None:
                price_query["$gte"] = min_price
            if max_price is not None:
                price_query["$lte"] = max_price
            if price_query:
                query["current_price"] = price_query
        
        query["is_active"] = True
        
        # Get available colors for the current category
        available_colors = list(collection_products.distinct(
            "variants.color",
            {"category": main_category} if main_category else {}
        ))
        
        # Remove None or empty values from colors
        available_colors = [color for color in available_colors if color]
        
        sort_direction = 1 if sort_order.lower() == "asc" else -1
        total_count = collection_products.count_documents(query)
        
        products = list(collection_products.find(
            query,
            skip=skip,
            limit=limit
        ).sort(sort_by, sort_direction))
        
        serialized_products = [serialize_mongo_doc(product) for product in products]
        
        response = {
            "products": serialized_products,
            "metadata": {
                "total_count": total_count,
                "page": skip // limit + 1,
                "limit": limit,
                "total_pages": (total_count + limit - 1) // limit,
                "filters_applied": {
                    "main_category": main_category,
                    "brands": brands,
                    "subcategories": subcategories,
                    "colors": colors,
                    "price_range": {
                        "min": min_price,
                        "max": max_price
                    } if min_price is not None or max_price is not None else None
                },
                "available_colors": available_colors,  # Add available colors to metadata
                "sorting": {
                    "field": sort_by,
                    "order": sort_order
                }
            }
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error filtering products: {str(e)}")
@router.get("/api/products/filter-options")
async def get_filter_options(main_category: Optional[MainCategory] = None):
    try:
        # Build the base query
        query = {"is_active": True}
        if main_category:
            query["category"] = main_category
        
        # Get unique brands
        brands = list(collection_products.distinct("brand", query))
        
        # Get unique subcategories
        subcategories = list(collection_products.distinct("sub_category", query))
        
        # Get price range
        price_info = list(collection_products.aggregate([
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "min_price": {"$min": "$current_price"},
                    "max_price": {"$max": "$current_price"}
                }
            }
        ]))
        
        price_range = {
            "min_price": price_info[0]["min_price"] if price_info else 0,
            "max_price": price_info[0]["max_price"] if price_info else 0
        }
        
        return {
            "brands": brands,
            "subcategories": subcategories,
            "price_range": price_range
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting filter options: {str(e)}")
    
    
    
@router.get("/api/categories", response_model=Dict[str, List[str]])
async def get_category_subcategories():
    """
    Get all subcategories mapped to their main categories
    """
    try:
        return JSONResponse(content=SUBCATEGORIES)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting subcategories: {str(e)}"
        )
        
        


@router.get("/api/colors")
async def get_unique_colors(main_category: Optional[MainCategory] = None):
    try:
        # Build the base query to filter active products
        query = {"is_active": True}
        
        # Add category filter if provided
        if main_category:
            query["category"] = main_category
            
        # Aggregate pipeline to get unique colors from product variants
        pipeline = [
            {"$match": query},
            {"$unwind": "$variants"},  # Deconstruct variants array
            {"$match": {"variants.color": {"$exists": True, "$ne": None, "$ne": ""}}},  # Filter out null/empty colors
            {"$group": {"_id": "$variants.color"}},  # Group by unique colors
            {"$sort": {"_id": 1}},  # Sort alphabetically
            {"$project": {"color": "$_id", "_id": 0}}  # Reshape output
        ]
        
        # Execute aggregation
        colors = list(collection_products.aggregate(pipeline))
        
        # Extract colors from result
        color_list = [doc["color"] for doc in colors]
        
        return JSONResponse(content={
            "status": "success",
            "colors": color_list,
            "total_colors": len(color_list),
            "category": main_category.value if main_category else "all"
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving unique colors: {str(e)}"
        )
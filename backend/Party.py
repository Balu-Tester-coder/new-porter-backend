from typing import Optional, Dict, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path, status, WebSocket, WebSocketDisconnect
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
db = client["Party"]
collection = db["seats"]

router = APIRouter(tags=["Party"], prefix="/party")



active_connections: List[WebSocket] = []


class Party(BaseModel):
    party_name: str
    part_seats_won: str

class PartyResponse(BaseModel):
    id: str
    party_name: str
    part_seats_won: str

    class Config:
        orm_mode = True

# Helper function to transform MongoDB documents to match Pydantic model
def transform_party_doc(party_doc):
    # Convert MongoDB _id to id for Pydantic model
    return {
        "id": str(party_doc["_id"]),
        "party_name": party_doc["party_name"],
        "part_seats_won": party_doc["part_seats_won"]
    }
    
    
    
    
    
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print("Received message from client:", data)
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print("Client disconnected")

async def broadcast_update():
    """Send updated data to all connected WebSocket clients."""
    parties = list(collection.find())
    updated_data = [transform_party_doc(party) for party in parties]
    
    for connection in active_connections:
        try:
            await connection.send_json(updated_data)
        except:
            active_connections.remove(connection)

@router.get("/all", response_model=List[PartyResponse])
async def get_all_parties():
    """Fetch all parties."""
    try:
        parties = list(collection.find())
        await broadcast_update()
        # Transform MongoDB documents to match the Pydantic model
        transformed_parties = [transform_party_doc(party) for party in parties]
        return transformed_parties
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/party/{party_name}", response_model=List[PartyResponse])
async def get_party_by_name(party_name: str):
    """Fetch parties by name."""
    try:
        parties = list(collection.find({"party_name": party_name}))
        # Transform MongoDB documents to match the Pydantic model
        transformed_parties = [transform_party_doc(party) for party in parties]
        return transformed_parties
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/party/seats/{seats_won}", response_model=List[PartyResponse])
async def get_party_by_seats(seats_won: int):
    """Fetch parties by seats won."""
    try:
        parties = list(collection.find({"part_seats_won": seats_won}))
        # Transform MongoDB documents to match the Pydantic model
        transformed_parties = [transform_party_doc(party) for party in parties]
        return transformed_parties
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=PartyResponse, status_code=status.HTTP_201_CREATED)
async def create_party(party: Party):
    try:
        party_dict = party.dict()
        result = collection.insert_one(party_dict)
        created_party = collection.find_one({"_id": result.inserted_id})

        # Broadcast the update to WebSocket clients
        await broadcast_update()

        return transform_party_doc(created_party)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{party_id}", response_model=PartyResponse)
async def update_party(party_id: str, party_update: Party):
    try:
        object_id = ObjectId(party_id)
        existing_party = collection.find_one({"_id": object_id})
        if not existing_party:
            raise HTTPException(status_code=404, detail="Party not found")

        update_data = party_update.dict()
        collection.update_one({"_id": object_id}, {"$set": update_data})

        # Broadcast the update to WebSocket clients
        await broadcast_update()

        updated_party = collection.find_one({"_id": object_id})
        return transform_party_doc(updated_party)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{party_id}", response_model=Dict[str, str])
async def delete_party(party_id: str):
    """Delete a party by ID."""
    try:
        # Convert string ID to ObjectId
        try:
            object_id = ObjectId(party_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid ID format")

        # Check if the party exists
        existing_party = collection.find_one({"_id": object_id})
        if not existing_party:
            raise HTTPException(status_code=404, detail="Party not found")

        # Delete the party
        result = collection.delete_one({"_id": object_id})
        await broadcast_update()

        if result.deleted_count == 1:
            return {"message": "Party deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete party")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

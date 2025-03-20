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

router = APIRouter(tags=["Permissions"], prefix="/permissions")

client = MongoClient(DATABASE_URL)

db = client.employee_payments
employee_collection=db.payments





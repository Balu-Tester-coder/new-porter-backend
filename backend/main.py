from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.Daily import router as daily_router
from backend.Dashboard import router as dashboard_router
from backend.Cources import router as cources_router
from backend.Images import router as images_router
from backend.Roombooking import router as roombooking_router
from backend.Employee import router as employee_router
from backend.Orders import router as orders_router
from backend.Dailyorders import router as dailyorders_router
from backend.Quiz import router as quiz_router
from backend.Party import router as party_router
from backend.Login import router as login_router
from backend.HomeWork import router as homework_router
from backend.EmployeeAttendence import router as attendence_router
from backend.Tasks import router as task_router
from backend.calender import router as calender_router
from backend.Worker import router as worker_router

app = FastAPI(title="Employee Payment Management System")  

# Include both routers
app.include_router(daily_router)
app.include_router(dashboard_router)
app.include_router(cources_router) 
app.include_router(images_router)
app.include_router(roombooking_router)
app.include_router(employee_router)
app.include_router(orders_router)
app.include_router(dailyorders_router)
app.include_router(quiz_router)
app.include_router(party_router)
app.include_router(login_router)

app.include_router(attendence_router)
app.include_router(task_router)
app.include_router(calender_router)
app.include_router(homework_router)
app.include_router(worker_router)
    

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
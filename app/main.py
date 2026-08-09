# app/main.py
from fastapi import FastAPI
from app.api import auth, users, admin_users

app = FastAPI()

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin_users.router)

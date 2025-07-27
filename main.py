# main.py
from fastapi import FastAPI
from app.routes import summary  # import your modular route

app = FastAPI()

# Include routers
app.include_router(summary.router)

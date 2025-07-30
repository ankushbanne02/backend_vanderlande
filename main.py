from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import summary  # Import your router module

app = FastAPI(
    title="Parcel KPI API",
    description="API to get parcel processing KPIs from MongoDB collections",
    version="1.0.0"
)

# CORS for frontend (e.g., React, Streamlit)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Root route to check if server is running
@app.get("/")
def root():
    print("🌐 Root URL '/' accessed")
    return {"message": "🚀 FastAPI backend is running and ready!"}

# Register KPI summary route
app.include_router(summary.router)

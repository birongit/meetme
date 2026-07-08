import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app = FastAPI(title="Booking Backend")

@app.on_event("shutdown")
def flush_langfuse():
    """Flush buffered traces before the process exits (Heroku restarts dynos daily)."""
    if os.environ.get("LANGFUSE_PUBLIC_KEY"):
        try:
            from langfuse import get_client
            get_client().shutdown()
        except Exception:
            pass

allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

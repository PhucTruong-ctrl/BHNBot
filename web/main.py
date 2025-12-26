"""
BHNBot Admin Panel - FastAPI Main Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

from .config import HOST, PORT, DEBUG, CORS_ORIGINS
from .routers import stats, users, roles, config as config_router, export
import logging
import traceback
from fastapi.responses import JSONResponse
from fastapi import Request

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AdminPanel")

# Create FastAPI app
app = FastAPI(
    title="BHNBot Admin Panel",
    description="Web dashboard for managing BHN Discord Bot",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = f"Global Error: {str(exc)}\n{traceback.format_exc()}"
    logging.error(error_msg)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc), "trace": traceback.format_exc()},
    )

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stats.router, prefix="/api/stats", tags=["Statistics"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(roles.router, prefix="/api/roles", tags=["Roles"])
app.include_router(config_router.router, prefix="/api/config", tags=["Configuration"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])

# Mount static files (for legacy role_manager UI if needed)
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "BHNBot Admin Panel",
        "version": "1.0.0"
    }


@app.get("/api/health")
async def health():
    """Detailed health check."""
    from .database import fetchone
    try:
        result = await fetchone("SELECT COUNT(*) as count FROM users")
        return {
            "status": "healthy",
            "database": "connected",
            "users_count": result["count"] if result else 0
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Admin Panel at http://{HOST}:{PORT}")
    uvicorn.run("web.main:app", host=HOST, port=PORT, reload=DEBUG)

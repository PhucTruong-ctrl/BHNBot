from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response
import os

from core.logging import get_logger
from .config import HOST, PORT, DEBUG, CORS_ORIGINS
from .routers import stats, users, roles, config as config_router, export, system, modules, audit, auth, cog_config, websocket, bot_logs
import traceback
from fastapi.responses import JSONResponse
from fastapi import Request

# Setup structured logging
logger = get_logger("AdminPanel")

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
    error_msg = f"Global Error: {str(exc)}\\n{traceback.format_exc()}"
    logger.error("global_exception", error=str(exc), trace=traceback.format_exc())
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
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(modules.router, prefix="/api/modules", tags=["Modules"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(cog_config.router, prefix="/api/cogs", tags=["Cog Config"])
app.include_router(websocket.router, prefix="/api", tags=["WebSocket"])
app.include_router(bot_logs.router, prefix="/api", tags=["Bot Logs"])

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root(request: Request):
    """Serve dashboard UI."""
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    templates = Jinja2Templates(directory=templates_dir)
    
    # Check authentication
    token = request.cookies.get("auth_token")
    if not token:
        if os.path.exists(os.path.join(templates_dir, "login.html")):
            return templates.TemplateResponse("login.html", {"request": request})
    
    if os.path.exists(os.path.join(templates_dir, "index.html")):
        return templates.TemplateResponse("index.html", {"request": request})
    return {
        "status": "ok",
        "service": "BHNBot Admin Panel",
        "version": "1.0.0"
    }


@app.get("/login")
async def login_page(request: Request):
    """Login page."""
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    templates = Jinja2Templates(directory=templates_dir)
    return templates.TemplateResponse("login.html", {"request": request})


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


@app.get("/favicon.ico")
async def favicon():
    """Return empty favicon to prevent 404 errors."""
    # Simple 1x1 transparent ICO
    ico_data = bytes([
        0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x01,
        0x00, 0x00, 0x01, 0x00, 0x18, 0x00, 0x30, 0x00,
        0x00, 0x00, 0x16, 0x00, 0x00, 0x00, 0x28, 0x00,
        0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x02, 0x00,
        0x00, 0x00, 0x01, 0x00, 0x18, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00
    ])
    return Response(content=ico_data, media_type="image/x-icon")


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Admin Panel at http://{HOST}:{PORT}")
    uvicorn.run("web.main:app", host=HOST, port=PORT, reload=DEBUG)

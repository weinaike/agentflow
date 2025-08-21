# api/serve.py - Simplified API service
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from ..version import VERSION
from .config import settings
from .deps import cleanup_managers, init_auth_manager, init_managers, register_auth_dependencies
from .initialization import AppInitializer
from .routes import ws

# Initialize application
app_file_path = os.path.dirname(os.path.abspath(__file__))
initializer = AppInitializer(settings, app_file_path)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifecycle manager for the simplified API service.
    Handles initialization and cleanup of application resources.
    """
    try:
        # Initialize essential managers (DB, Connection, Auth)
        await init_managers(initializer.database_uri, initializer.config_dir, initializer.app_root)
        
        # Initialize authentication manager
        auth_manager = init_auth_manager(initializer.config_dir)
        await register_auth_dependencies(app, auth_manager)
        
        logger.info(
            f"Simplified API service startup complete. Navigate to http://{os.environ.get('AUTOGENSTUDIO_HOST', '127.0.0.1')}:{os.environ.get('AUTOGENSTUDIO_PORT', '8084')}"
        )
    except Exception as e:
        logger.error(f"Failed to initialize simplified API service: {str(e)}")
        raise

    yield  # Application runs here

    # Shutdown
    try:
        logger.info("Cleaning up simplified API service resources...")
        await cleanup_managers()
        logger.info("Simplified API service shutdown complete")
    except Exception as e:
        logger.error(f"Error during simplified API service shutdown: {str(e)}")


# Create FastAPI application
app = FastAPI(
    lifespan=lifespan,
    title="AgentFlow Server Simplified API",
    version=VERSION,
    description="Simplified AgentFlow Server API service with WebSocket support only.",
    docs_url="/docs" if settings.API_DOCS else None,
    redoc_url="/redoc" if settings.API_DOCS else None,
    debug=True
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000", 
        "http://localhost:8001",
        "http://localhost:8081",
        "http://localhost:8084",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include only WebSocket router
app.include_router(
    ws.router,
    prefix="/ws",
    tags=["websocket"],
    responses={404: {"description": "Not found"}},
)

# Mount static files for the test page
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Version endpoint
@app.get("/version")
async def get_version():
    """Get API version"""
    return {
        "status": True,
        "message": "Version retrieved successfully",
        "data": {"version": VERSION},
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """API health check endpoint"""
    return {
        "status": True,
        "message": "Simplified API service is healthy",
        "service": "agentflow server simplified",
    }

# WebSocket Protocol Documentation
@app.get("/ws-docs")
async def get_websocket_docs():
    """Get WebSocket protocol documentation"""
    import json
    
    try:
        # Load documentation from static file
        docs_path = os.path.join(static_dir, "ws-protocol.json")
        with open(docs_path, 'r', encoding='utf-8') as f:
            protocol_data = json.load(f)
        
        return {
            "status": True,
            "message": "WebSocket protocol documentation",
            "data": protocol_data
        }
    except FileNotFoundError:
        logger.error(f"WebSocket protocol documentation file not found at {docs_path}")
        return {
            "status": False,
            "message": "Protocol documentation file not found"
        }
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in protocol documentation: {str(e)}")
        return {
            "status": False,
            "message": "Invalid protocol documentation format"
        }
    except Exception as e:
        logger.error(f"Error loading protocol documentation: {str(e)}")
        return {
            "status": False,
            "message": "Error loading protocol documentation"
        }

# WebSocket Protocol Documentation (HTML)
@app.get("/ws-docs-html")
async def get_websocket_docs_html():
    """Redirect to the HTML WebSocket protocol documentation"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/ws-docs.html")

# WebSocket Test Page
@app.get("/ws-test")
async def get_websocket_test_page():
    """Redirect to the WebSocket test page"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/ws-test.html")

# Debug endpoint to create a test run
@app.post("/debug/create-test-run")
async def create_test_run(request_body: dict):
    """Create a test run for WebSocket testing"""
    try:
        from .deps import get_db
        from ..datamodel import Run, RunStatus, Session
        
        # Get run_id from request body, default to 1
        run_id = request_body.get("run_id", 1)
        session_id = run_id  # Use same ID for session for simplicity
        
        db = await get_db()
        
        # First, create a test session if it doesn't exist
        existing_session = db.get(Session, filters={"id": session_id}, return_json=False)
        if not existing_session.status or not existing_session.data:
            test_session = Session(
                id=session_id,
                name=f"Test Session {session_id}",
                user_id="test_user",
                team_id=None
            )
            session_result = db.upsert(test_session)
            if not session_result.status:
                return {
                    "status": False,
                    "message": f"Failed to create test session: {session_result.message}"
                }
        
        # Create a test run
        test_run = Run(
            id=run_id,
            session_id=session_id,
            user_id="test_user",
            status=RunStatus.CREATED,
            task={"content": f"Test task {run_id}", "source": "user"},
            team_result=None,
            error_message=None
        )
        
        # Check if run already exists
        existing_run = db.get(Run, filters={"id": run_id}, return_json=False)
        if not existing_run.status or not existing_run.data:
            result = db.upsert(test_run)
            if result.status:
                return {
                    "status": True,
                    "message": "Test run created successfully",
                    "data": {
                        "run_id": run_id,
                        "session_id": session_id,
                        "user_id": "test_user"
                    }
                }
            else:
                return {
                    "status": False,
                    "message": f"Failed to create test run: {result.message}"
                }
        else:
            return {
                "status": True,
                "message": "Test run already exists",
                "data": {
                    "run_id": run_id,
                    "session_id": session_id,
                    "user_id": "test_user"
                }
            }
            
    except Exception as e:
        logger.error(f"Error creating test run: {str(e)}")
        return {
            "status": False,
            "message": f"Error creating test run: {str(e)}"
        }

# Debug endpoint to check run status
@app.get("/debug/run/{run_id}")
async def get_run_info(run_id: int):
    """Get run information for debugging"""
    try:
        from .deps import get_db
        from ..datamodel import Run
        
        db = await get_db()
        result = db.get(Run, filters={"id": run_id}, return_json=False)
        
        if result.status and result.data:
            run = result.data[0]
            return {
                "status": True,
                "message": "Run found",
                "data": {
                    "id": run.id,
                    "session_id": run.session_id,
                    "user_id": run.user_id,
                    "status": run.status,
                    "task": run.task,
                    "created_at": run.created_at
                }
            }
        else:
            return {
                "status": False,
                "message": f"Run {run_id} not found"
            }
            
    except Exception as e:
        return {
            "status": False,
            "message": f"Error retrieving run: {str(e)}"
        }

# Debug endpoint to check database status
@app.get("/debug/db-status")
async def get_database_status():
    """Get database status for debugging"""
    try:
        from .deps import get_db
        from ..datamodel import Run, Session
        
        db = await get_db()
        
        # Check sessions
        sessions_result = db.get(Session, return_json=False)
        sessions_count = len(sessions_result.data) if sessions_result.status and sessions_result.data else 0
        
        # Check runs
        runs_result = db.get(Run, return_json=False)
        runs_count = len(runs_result.data) if runs_result.status and runs_result.data else 0
        
        return {
            "status": True,
            "message": "Database status retrieved",
            "data": {
                "sessions_count": sessions_count,
                "runs_count": runs_count,
                "database_uri": db.engine.url.render_as_string(hide_password=False) if hasattr(db, 'engine') else "Unknown"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting database status: {str(e)}")
        return {
            "status": False,
            "message": f"Error getting database status: {str(e)}"
        }

# Debug endpoint to clean test data
@app.delete("/debug/clean-test-data")
async def clean_test_data():
    """Clean test data from database"""
    try:
        from .deps import get_db
        from ..datamodel import Run, Session
        
        db = await get_db()
        
        # Delete test run
        run_result = db.delete(Run, filters={"id": 1})
        
        # Delete test session
        session_result = db.delete(Session, filters={"id": 1})
        
        return {
            "status": True,
            "message": "Test data cleaned successfully",
            "data": {
                "run_deleted": run_result.status if run_result else False,
                "session_deleted": session_result.status if session_result else False
            }
        }
        
    except Exception as e:
        logger.error(f"Error cleaning test data: {str(e)}")
        return {
            "status": False,
            "message": f"Error cleaning test data: {str(e)}"
        }

# Error handlers
@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal error in simplified API service: {str(exc)}")
    return {
        "status": False,
        "message": "Internal server error",
        "detail": str(exc) if settings.API_DOCS else "Internal server error",
    }


def create_app() -> FastAPI:
    """
    Factory function to create and configure the simplified FastAPI application.
    Useful for testing and different deployment scenarios.
    """
    return app

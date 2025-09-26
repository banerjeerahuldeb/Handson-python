import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from agent import WorkflowAgent, ChatMessage, ChatResponse
from health_check import health_router, HealthChecker
from approval_workflow import approval_router
from config.settings import DatabaseConfig
from models.data_models import WorkflowRequest, WorkflowResponse
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan event handler (replaces @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    logger.info("Starting MCP Workflow System...")
    logger.info("Health check endpoints available at /api/health")
    logger.info("Main workflow endpoint available at /api/workflow/maintenance")
    
    # Initialize the agent
    global agent
    agent = WorkflowAgent(openai_api_key=DatabaseConfig.OPENAI_API_KEY)
    
    yield  # App runs here
    
    # Shutdown code (optional)
    logger.info("Shutting down MCP Workflow System...")

app = FastAPI(
    title="MCP Workflow System",
    description="Integrated maintenance workflow system with SQL Server, Oracle, .NET API, and HR data",
    version="1.0.0",
    lifespan=lifespan  # Add lifespan handler
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api")
app.include_router(approval_router, prefix="/api")

# Global agent instance (initialized in lifespan)
agent = None

@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "message": "MCP Workflow System is running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health",
            "workflow": "/api/workflow/maintenance",
            "chat": "/api/chat",
            "approvals": "/api/approvals/pending"
        }
    }

@app.get("/api/status")
async def system_status():
    """Get comprehensive system status"""
    health_checker = HealthChecker()
    health_status = await health_checker.check_all_systems()
    overall_status = health_checker.get_overall_status(health_status)
    
    return {
        "overall_status": overall_status.value,
        "systems": {name: status.dict() for name, status in health_status.items()},
        "timestamp": asyncio.get_event_loop().time()
    }

@app.post("/api/workflow/maintenance", response_model=WorkflowResponse)
async def process_maintenance(request: WorkflowRequest):
    """Process a maintenance workflow request"""
    try:
        logger.info(f"Processing maintenance request for {request.equipment_id}")
        response = await agent.execute_maintenance_workflow(
            request.equipment_id,
            request.issue_description,
            request.priority
        )
        return response
    except Exception as e:
        logger.error(f"Error processing maintenance request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage):
    """Chat interface for natural language maintenance requests"""
    try:
        logger.info(f"Processing chat message from {message.user_id}")
        response = await agent.process_chat_message(message.message)
        return response
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/systems")
async def list_systems():
    """List all integrated systems"""
    return {
        "systems": [
            {
                "name": "inventory",
                "type": "SQL Server",
                "description": "Inventory management database",
                "endpoint": "/mcp/inventory"
            },
            {
                "name": "workorders", 
                "type": "Oracle Database",
                "description": "Work orders management system",
                "endpoint": "/mcp/workorders"
            },
            {
                "name": "permits",
                "type": ".NET Core API", 
                "description": "Permit management system",
                "endpoint": "/api/permits"
            },
            {
                "name": "hr",
                "type": "Excel Data",
                "description": "HR and employee management",
                "endpoint": "/mcp/hr"
            }
        ]
    }

if __name__ == "__main__":
    # Run the application - use import string for reload
    uvicorn.run(
        "main:app",  # Use import string instead of app object
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True  # This will work now with import string
    )

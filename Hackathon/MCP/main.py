import asyncio
import uvicorn
from fastapi import FastAPI
from agent import WorkflowAgent
from servers.inventory_server import InventoryMCPServer
from servers.workorders_server import WorkOrdersMCPServer
from servers.permits_server import PermitsMCPServer
from servers.hr_server import HRMCPServer
from models.data_models import WorkflowRequest, WorkflowResponse
import os

app = FastAPI(title="MCP Workflow System")

# Initialize MCP servers
inventory_server = InventoryMCPServer()
workorders_server = WorkOrdersMCPServer()
permits_server = PermitsMCPServer()
hr_server = HRMCPServer()

mcp_servers = {
    'inventory': inventory_server,
    'workorders': workorders_server, 
    'permits': permits_server,
    'hr': hr_server
}

# Initialize agent
agent = WorkflowAgent(
    openai_api_key=os.getenv('OPENAI_API_KEY', 'your-openai-api-key'),
    mcp_servers=mcp_servers
)

@app.post("/api/workflow/maintenance", response_model=WorkflowResponse)
async def process_maintenance(request: WorkflowRequest):
    """API endpoint to process maintenance requests"""
    return await agent.process_maintenance_request(request)

@app.post("/api/chat")
async def chat_endpoint(message: str):
    """Chat interface for maintenance requests"""
    response = await agent.chat_interface(message)
    return {"response": response}

@app.get("/")
async def root():
    return {"message": "MCP Workflow System is running"}

async def run_mcp_servers():
    """Run all MCP servers in background"""
    # In a real implementation, these would run as separate processes
    print("MCP servers initialized and ready")

if __name__ == "__main__":
    # Start MCP servers
    asyncio.run(run_mcp_servers())
    
    # Start FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=8000)

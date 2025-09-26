import asyncio
import aiohttp
import json
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from models.data_models import WorkflowRequest, WorkflowResponse, SystemHealthStatus
from health_check import HealthChecker, health_router
from approval_workflow import approval_router
from config.settings import DatabaseConfig
import re
import logging
import os
import uuid

app = FastAPI(title="MCP Workflow Agent")
app.include_router(health_router, prefix="/api")
app.include_router(approval_router, prefix="/api")

class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = "user"
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    requires_approval: bool = False
    approval_code: Optional[str] = None
    actions: List[str] = []
    details: Dict[str, Any] = {}

class WorkflowAgent:
    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key="sk-proj-nEoPoNyY90k5vK8leVNFoIku8dbiF5s4DTKpBVYs56QdVJnJfeaxlnAPivk1-jRKZEoJlXwXrVT3BlbkFJT1kFVKSl6tcVzjoUv75J-xcc0E04lBw4CBNYcyrDjSFt3YfEFig3Q2Zl6hb653LxwhTVlzR1g")
        self.health_checker = HealthChecker()
        self.mcp_servers = {
            "inventory": "http://localhost:8002",
            "workorders": "http://localhost:8003",
            "permits": "http://localhost:8001",
            "hr": "http://localhost:8004"
        }
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        self.setup_system_prompt()
    
    def setup_system_prompt(self):
        self.system_prompt = """
        You are an intelligent maintenance workflow agent for an industrial facility.
        Your capabilities include:
        
        1. Health Monitoring: Check status of inventory, workorders, permits, and HR systems
        2. Workflow Management: Process maintenance requests from start to finish
        3. Approval Handling: Manage workflow approvals when required
        4. Natural Language Processing: Understand maintenance requests in plain English
        
        Workflow Steps:
        - Receive maintenance request (e.g., "pump-002 is not working")
        - Check for existing work orders
        - Analyze required parts using AI
        - Check inventory availability
        - Identify required permits
        - Find available qualified personnel
        - Create work order with all details
        - Request approval if needed
        - Execute the workflow
        
        Always provide clear, structured responses and indicate when approval is required.
        """
    
    async def call_mcp_server(self, server: str, endpoint: str, method: str = "POST", params: Dict = None):
        """Make calls to MCP servers"""
        url = f"{self.mcp_servers[server]}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == "POST":
                    async with session.post(url, json=params) as response:
                        return await response.json()
                else:
                    async with session.get(url) as response:
                        return await response.json()
        except Exception as e:
            self.logger.error(f"Error calling {server} server: {str(e)}")
            return {"error": str(e)}
    
    async def check_inventory(self, item_codes: List[str]) -> Dict[str, Any]:
        """Check inventory for specific items"""
        try:
            result = await self.call_mcp_server("inventory", "/mcp/inventory/check", "POST", {
                "method": "check",
                "params": {
                    "item_codes": item_codes,
                    "quantities": {code: 1 for code in item_codes}
                }
            })
            return result
        except Exception as e:
            self.logger.error(f"Error checking inventory: {str(e)}")
            return {"error": str(e)}

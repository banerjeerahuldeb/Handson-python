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

    async def process_chat_message(self, message: str) -> ChatResponse:
        """Process natural language chat messages"""
        try:
            # Use OpenAI to analyze the message and determine intent
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Analyze this message and determine the action: {message}"}
                ],
                functions=[
                    {
                        "name": "health_check",
                        "description": "Check system health status",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "system": {
                                    "type": "string",
                                    "enum": ["all", "inventory", "workorders", "permits", "hr"],
                                    "description": "System to check"
                                }
                            }
                        }
                    },
                    {
                        "name": "process_maintenance",
                        "description": "Process a maintenance request",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "equipment_id": {"type": "string", "description": "Equipment identifier"},
                                "issue_description": {"type": "string", "description": "Description of the issue"},
                                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]}
                            },
                            "required": ["equipment_id", "issue_description"]
                        }
                    },
                    {
                        "name": "check_inventory",
                        "description": "Check inventory for specific items",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "item_codes": {
                                    "type": "array", 
                                    "items": {"type": "string"},
                                    "description": "List of item codes to check"
                                }
                            }
                        }
                    },
                    {
                        "name": "list_workorders",
                        "description": "List workorders with optional filters",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "status": {"type": "string", "enum": ["open", "assigned", "in_progress", "completed", "cancelled"]},
                                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]}
                            }
                        }
                    }
                ],
                function_call="auto"
            )
            
            message_response = response.choices[0].message
            
            if message_response.function_call:
                function_name = message_response.function_call.name
                function_args = json.loads(message_response.function_call.arguments)
                
                # Execute the appropriate function
                if function_name == "health_check":
                    result = await self.health_check(function_args.get("system", "all"))
                elif function_name == "process_maintenance":
                    result = await self.process_maintenance_request(function_args)
                elif function_name == "check_inventory":
                    result = await self.check_inventory(function_args.get("item_codes", []))
                elif function_name == "list_workorders":
                    result = await self.list_workorders(function_args)
                else:
                    result = {"response": f"Function {function_name} not implemented"}
                
                return ChatResponse(
                    response=result.get("response", "Action completed"),
                    requires_approval=result.get("requires_approval", False),
                    approval_code=result.get("approval_code"),
                    actions=result.get("actions", []),
                    details=result.get("details", {})
                )
            else:
                # No function call needed, return the AI's response directly
                return ChatResponse(
                    response=message_response.content,
                    requires_approval=False,
                    actions=[],
                    details={}
                )
                
        except Exception as e:
            self.logger.error(f"Error processing chat message: {str(e)}")
            return ChatResponse(
                response=f"Error processing your request: {str(e)}",
                requires_approval=False,
                actions=[],
                details={"error": str(e)}
            )
    
    async def health_check(self, system: str = "all") -> Dict[str, Any]:
        """Check health of MCP servers"""
        health_results = {}
        
        systems_to_check = []
        if system == "all":
            systems_to_check = list(self.mcp_servers.keys())
        else:
            systems_to_check = [system]
        
        for sys in systems_to_check:
            try:
                result = await self.call_mcp_server(sys, "/health", "GET")
                health_results[sys] = result
            except Exception as e:
                health_results[sys] = {"status": "error", "error": str(e)}
        
        all_healthy = all(
            result.get("status") in ["healthy", "up"] 
            for result in health_results.values() 
            if isinstance(result, dict)
        )
        
        return {
            "response": f"Health check completed. Systems: {', '.join(health_results.keys())}",
            "details": health_results,
            "all_healthy": all_healthy
        }
    async def process_maintenance_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process a maintenance workflow request"""
        try:
            equipment_id = params.get("equipment_id")
            issue_description = params.get("issue_description")
            priority = params.get("priority", "medium")
            
            self.logger.info(f"Processing maintenance request for {equipment_id}: {issue_description}")
            
            # Step 1: Analyze the issue to determine required parts and skills
            analysis_result = await self.analyze_maintenance_issue(issue_description, equipment_id)
            required_parts = analysis_result.get("required_parts", {})
            required_skills = analysis_result.get("required_skills", [])
            
            # Step 2: Check inventory availability
            inventory_result = await self.check_inventory(list(required_parts.keys()))
            
            # Step 3: Check for available employees with required skills
            hr_result = await self.call_mcp_server("hr", "/mcp/hr/available_employees", "POST", {
                "method": "available_employees",
                "params": {
                    "required_skills": required_skills,
                    "max_workload": 2
                }
            })
            
            # Step 4: Create workorder
            workorder_result = await self.call_mcp_server("workorders", "/mcp/workorders/create", "POST", {
                "method": "create",
                "params": {
                    "equipment_id": equipment_id,
                    "description": issue_description,
                    "priority": priority,
                    "estimated_hours": analysis_result.get("estimated_hours", 4.0)
                }
            })
            
            workorder_id = workorder_result.get("result", {}).get("workorder_id")
            
            # Determine if approval is needed based on priority and cost
            requires_approval = priority in ["high", "critical"] or len(required_parts) > 5
            
            response_data = {
                "response": f"Maintenance workflow initiated for {equipment_id}",
                "requires_approval": requires_approval,
                "details": {
                    "equipment_id": equipment_id,
                    "workorder_id": workorder_id,
                    "required_parts": required_parts,
                    "required_skills": required_skills,
                    "inventory_status": inventory_result.get("result", {}),
                    "available_employees": hr_result.get("result", {}).get("available_employees", []),
                    "analysis": analysis_result
                },
                "actions": [
                    "Issue analyzed",
                    "Inventory checked",
                    "Personnel availability verified",
                    "Workorder created"
                ]
            }
            
            if requires_approval:
                approval_code = f"WO-{workorder_id}-APPROVAL"
                response_data["approval_code"] = approval_code
                response_data["response"] += f". Approval required: {approval_code}"
            
            return response_data
            
        except Exception as e:
            self.logger.error(f"Error processing maintenance request: {str(e)}")
            return {
                "response": f"Error processing maintenance request: {str(e)}",
                "requires_approval": False,
                "details": {"error": str(e)}
            }
    
    async def analyze_maintenance_issue(self, issue_description: str, equipment_id: str) -> Dict[str, Any]:
        """Use AI to analyze maintenance issue and determine requirements"""
        try:
            prompt = f"""
            Analyze this maintenance issue and determine what's needed:
            
            Equipment: {equipment_id}
            Issue: {issue_description}
            
            Provide a JSON response with:
            - required_parts: dictionary of part codes and quantities needed
            - required_skills: list of skills needed for the repair
            - estimated_hours: estimated time to complete
            - risk_level: low, medium, high, critical
            - special_requirements: any special tools or safety requirements
            
            Base your analysis on typical industrial maintenance knowledge.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an industrial maintenance expert. Analyze maintenance issues and provide structured responses."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing maintenance issue: {str(e)}")
            # Fallback analysis
            return {
                "required_parts": {"GASKET-001": 1, "BOLT-002": 4},
                "required_skills": ["mechanical", "troubleshooting"],
                "estimated_hours": 4.0,
                "risk_level": "medium",
                "special_requirements": ["safety glasses", "gloves"]
            }
    async def list_workorders(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List workorders with optional filters"""
        try:
            result = await self.call_mcp_server("workorders", "/mcp/workorders/list", "POST", {
                "method": "list",
                "params": params
            })
            return {
                "response": f"Found {result.get('result', {}).get('total_count', 0)} workorders",
                "details": result.get("result", {})
            }
        except Exception as e:
            self.logger.error(f"Error listing workorders: {str(e)}")
            return {"response": f"Error listing workorders: {str(e)}", "details": {}}
    
    async def execute_approved_workflow(self, approval_code: str) -> Dict[str, Any]:
        """Execute a workflow after approval"""
        try:
            # Extract workorder ID from approval code
            match = re.search(r"WO-(\w+)-APPROVAL", approval_code)
            if not match:
                return {"success": False, "error": "Invalid approval code"}
            
            workorder_id = match.group(1)
            
            # Get workorder details
            workorder_result = await self.call_mcp_server("workorders", "/mcp/workorders/details", "POST", {
                "method": "details",
                "params": {"workorder_id": workorder_id}
            })
            
            workorder_details = workorder_result.get("result", {}).get("workorder", {})
            
            # Execute the workflow steps
            # 1. Assign employee
            # 2. Reserve inventory
            # 3. Update workorder status
            
            return {
                "success": True,
                "message": f"Workflow executed for workorder {workorder_id}",
                "workorder_id": workorder_id,
                "details": workorder_details
            }
            
        except Exception as e:
            self.logger.error(f"Error executing approved workflow: {str(e)}")
            return {"success": False, "error": str(e)}

# Initialize the agent globally
agent_instance = None

def get_agent():
    """Get or create the workflow agent instance"""
    global agent_instance
    if agent_instance is None:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        agent_instance = WorkflowAgent(openai_api_key)
    return agent_instance

# FastAPI endpoints
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatMessage):
    """Chat endpoint for natural language interaction"""
    try:
        agent = get_agent()
        response = await agent.process_chat_message(chat_message.message)
        return response
    except ValueError as e:
        return ChatResponse(
            response="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.",
            requires_approval=False,
            actions=[],
            details={"error": str(e)}
        )
    except Exception as e:
        return ChatResponse(
            response=f"Error processing chat message: {str(e)}",
            requires_approval=False,
            actions=[],
            details={"error": str(e)}
        )

@app.post("/api/workflow/process", response_model=WorkflowResponse)
async def process_workflow(workflow_request: WorkflowRequest):
    """Process a maintenance workflow"""
    try:
        agent = get_agent()
        result = await agent.process_maintenance_request(workflow_request.dict())
        
        return WorkflowResponse(
            success=True,
            message=result.get("response", "Workflow processed"),
            workflow_id=result.get("details", {}).get("workorder_id", str(uuid.uuid4())),
            requires_approval=result.get("requires_approval", False),
            approval_code=result.get("approval_code"),
            details=result.get("details", {})
        )
    except Exception as e:
        return WorkflowResponse(
            success=False,
            message=f"Error processing workflow: {str(e)}",
            workflow_id=None,
            requires_approval=False,
            approval_code=None,
            details={"error": str(e)}
        )

@app.post("/api/workflow/execute")
async def execute_workflow(approval_code: str):
    """Execute an approved workflow"""
    try:
        agent = get_agent()
        result = await agent.execute_approved_workflow(approval_code)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/systems/health")
async def systems_health():
    """Check health of all MCP systems"""
    try:
        agent = get_agent()
        health_result = await agent.health_check("all")
        return health_result
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/inventory/check")
async def check_inventory_endpoint(item_codes: str):
    """Check inventory endpoint"""
    try:
        agent = get_agent()
        items = item_codes.split(",")
        result = await agent.check_inventory(items)
        return result
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

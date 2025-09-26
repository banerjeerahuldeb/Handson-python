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
        self.client = OpenAI(api_key=openai_api_key)
        self.health_checker = HealthChecker()
        self.mcp_servers = {
            "inventory": "http://localhost:8002",
            "workorders": "http://localhost:8003",
            "permits": "http://localhost:8001",
            "hr": "http://localhost:8004"
        }
        
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
            return {"error": str(e)}
    
    async def process_chat_message(self, message: str) -> ChatResponse:
        """Process natural language chat messages"""
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
                }
            ],
            function_call="auto"
        )
        
        message_content = response.choices[0].message
        
        if message_content.function_call:
            function_name = message_content.function_call.name
            function_args = json.loads(message_content.function_call.arguments)
            
            if function_name == "health_check":
                return await self.handle_health_check(function_args.get("system", "all"))
            elif function_name == "process_maintenance":
                return await self.handle_maintenance_request(function_args)
        
        # Default response for general chat
        return ChatResponse(
            response="I can help you with maintenance workflows and system health checks. Please provide specific details about the equipment issue or what you'd like to check.",
            actions=["chat_processed"]
        )
    
    async def handle_health_check(self, system: str) -> ChatResponse:
        """Handle health check requests"""
        if system == "all":
            health_status = await self.health_checker.check_all_systems()
            overall_status = self.health_checker.get_overall_status(health_status)
            
            status_text = "\n".join([
                f"{name}: {status.status.value} (Response: {status.response_time:.2f}ms)"
                for name, status in health_status.items()
            ])
            
            return ChatResponse(
                response=f"System Health Status (Overall: {overall_status.value}):\n{status_text}",
                actions=["health_check_all"]
            )
        else:
            health_status = await self.health_checker.check_system_health(
                system, self.health_checker.systems[system]
            )
            
            return ChatResponse(
                response=f"{system.capitalize()} System: {health_status.status.value}\nResponse Time: {health_status.response_time:.2f}ms",
                actions=[f"health_check_{system}"]
            )
    
    async def handle_maintenance_request(self, args: Dict) -> ChatResponse:
        """Handle maintenance workflow requests"""
        equipment_id = args["equipment_id"]
        issue_description = args["issue_description"]
        priority = args.get("priority", "medium")
        
        # Extract equipment ID from natural language if not provided directly
        if not equipment_id or equipment_id == "unknown":
            # Use regex to find equipment patterns like "pump-001", "valve-002", etc.
            equipment_pattern = r'\b(pump|valve|motor|compressor)-(\d{3})\b'
            matches = re.findall(equipment_pattern, issue_description, re.IGNORECASE)
            if matches:
                equipment_id = f"{matches[0][0]}-{matches[0][1]}"
            else:
                return ChatResponse(
                    response="I couldn't identify the equipment ID from your description. Please specify the equipment ID (e.g., pump-002).",
                    actions=["equipment_id_missing"]
                )
        
        # Start the workflow
        workflow_result = await self.execute_maintenance_workflow(
            equipment_id, issue_description, priority
        )
        
        if workflow_result.requires_approval:
            return ChatResponse(
                response=f"Workflow created for {equipment_id}. Approval required. Approval Code: {workflow_result.approval_code}",
                requires_approval=True,
                approval_code=workflow_result.approval_code,
                actions=workflow_result.actions_taken,
                details=workflow_result.details
            )
        else:
            return ChatResponse(
                response=f"Workflow completed successfully for {equipment_id}. Work Order: {workflow_result.workorder_id}",
                actions=workflow_result.actions_taken,
                details=workflow_result.details
            )
    
    async def execute_maintenance_workflow(self, equipment_id: str, issue_description: str, priority: str) -> WorkflowResponse:
        """Execute the complete maintenance workflow"""
        actions_taken = []
        details = {}
        
        try:
            # Step 1: Check existing work orders
            actions_taken.append("Checked existing work orders")
            existing_orders = await self.call_mcp_server(
                "workorders", "/mcp/workorders/check",
                params={"method": "check", "params": {"equipment_id": equipment_id}}
            )
            
            details['existing_workorders'] = existing_orders
            
            if existing_orders.get('active_count', 0) > 0:
                return WorkflowResponse(
                    success=False,
                    message=f"Active work order already exists for {equipment_id}",
                    actions_taken=actions_taken,
                    details=details
                )
            
            # Step 2: Analyze required parts using AI
            actions_taken.append("Analyzed required parts using AI")
            required_parts = await self.analyze_required_parts(equipment_id, issue_description)
            details['required_parts'] = required_parts
            
            # Step 3: Check inventory
            actions_taken.append("Checked inventory availability")
            inventory_status = await self.call_mcp_server(
                "inventory", "/mcp/inventory/check",
                params={"method": "check", "params": {"item_codes": required_parts}}
            )
            details['inventory_status'] = inventory_status
            
            if not inventory_status.get('result', {}).get('all_available', False):
                return WorkflowResponse(
                    success=False,
                    message="Insufficient inventory for required parts",
                    actions_taken=actions_taken,
                    details=details
                )
            
            # Step 4: Check required permits
            actions_taken.append("Checked permit requirements")
            equipment_type = equipment_id.split('-')[0]
            permit_requirements = await self.call_mcp_server(
                "permits", f"/api/permits/required/{equipment_type}",
                method="GET", params={"work_type": "repair"}
            )
            details['permit_requirements'] = permit_requirements
            
            # Step 5: Find available employees
            actions_taken.append("Searched for available employees")
            available_employees = await self.call_mcp_server(
                "hr", "/mcp/hr/find",
                params={"method": "find", "params": {
                    "skills": ["pump repair", "mechanical"],
                    "department": "Maintenance",
                    "max_workload": 3
                }}
            )
            details['available_employees'] = available_employees
            
            if available_employees.get('count', 0) == 0:
                return WorkflowResponse(
                    success=False,
                    message="No available employees with required skills",
                    actions_taken=actions_taken,
                    details=details
                )
            
            # Step 6: Create work order
            actions_taken.append("Created work order")
            assigned_employee = available_employees.get('employees', [{}])[0].get('employee_id', 'EMP001')
            
            workorder = await self.call_mcp_server(
                "workorders", "/mcp/workorders/create",
                params={"method": "create", "params": {
                    "equipment_id": equipment_id,
                    "title": f"Repair - {equipment_id}",
                    "description": issue_description,
                    "priority": priority,
                    "required_parts": required_parts,
                    "assigned_to": assigned_employee
                }}
            )
            details['workorder'] = workorder
            
            workorder_id = workorder.get('workorder_id')
            
            # Determine if approval is required (based on priority and cost)
            requires_approval = priority in ["high", "critical"] or len(required_parts) > 3
            
            if requires_approval:
                actions_taken.append("Requested approval")
                # Request approval
                approval_request = await self.call_mcp_server(
                    "agent", "/api/workflow/request-approval",
                    method="POST", params={
                        "workorder_id": workorder_id,
                        "requested_by": "System",
                        "approval_items": [
                            {"type": "workorder", "id": workorder_id, "description": issue_description},
                            {"type": "inventory", "items": required_parts},
                            {"type": "permits", "required": permit_requirements.get('required_permits', [])}
                        ]
                    }
                )
                details['approval_request'] = approval_request
                
                return WorkflowResponse(
                    success=True,
                    workorder_id=workorder_id,
                    message=f"Workflow created for {equipment_id}. Approval required.",
                    actions_taken=actions_taken,
                    requires_approval=True,
                    approval_code=approval_request.get('approval_code'),
                    details=details
                )
            else:
                # Auto-approve and continue
                actions_taken.append("Auto-approved workflow")
                
                # Reserve inventory
                item_quantities = {part: 1 for part in required_parts}
                inventory_reservation = await self.call_mcp_server(
                    "inventory", "/mcp/inventory/reserve",
                    params={"method": "reserve", "params": {
                        "item_quantities": item_quantities,
                        "workorder_id": workorder_id
                    }}
                )
                details['inventory_reservation'] = inventory_reservation
                
                # Create permits
                if permit_requirements.get('permit_required', False):
                    actions_taken.append("Created permit requests")
                    permits_created = []
                    for permit_type in permit_requirements.get('required_permits', []):
                        permit = await self.call_mcp_server(
                            "permits", "/api/permits",
                            method="POST", params={
                                "workorder_id": workorder_id,
                                "permit_type": permit_type,
                                "description": f"Permit for {equipment_id} repair"
                            }
                        )
                        permits_created.append(permit)
                    details['permits_created'] = permits_created
                
                return WorkflowResponse(
                    success=True,
                    workorder_id=workorder_id,
                    message=f"Workflow completed successfully for {equipment_id}",
                    actions_taken=actions_

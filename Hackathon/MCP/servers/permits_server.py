import requests
from mcp import MCPServer, Tool
from models.data_models import Permit, PermitStatus
from typing import List, Dict, Any

class PermitsMCPServer:
    def __init__(self, api_base_url: str = "http://localhost:8001"):
        self.api_base_url = api_base_url
        self.server = MCPServer("permits-server")
        self._register_tools()

    def _register_tools(self):
        self.server.register_tool(
            Tool(
                name="check_required_permits",
                description="Check what permits are required for equipment maintenance",
                input_schema={
                    "type": "object",
                    "properties": {
                        "equipment_id": {"type": "string"},
                        "work_type": {"type": "string"}
                    },
                    "required": ["equipment_id", "work_type"]
                },
                handler=self.check_required_permits
            )
        )
        
        self.server.register_tool(
            Tool(
                name="create_permit_request",
                description="Create a permit request for work order",
                input_schema={
                    "type": "object",
                    "properties": {
                        "workorder_id": {"type": "string"},
                        "permit_type": {"type": "string"},
                        "description": {"type": "string"}
                    },
                    "required": ["workorder_id", "permit_type"]
                },
                handler=self.create_permit_request
            )
        )

    def check_required_permits(self, equipment_id: str, work_type: str) -> Dict[str, Any]:
        # Simulate API call to .NET Core permit system
        # In real implementation, this would be an actual API call
        
        # Mock response based on equipment and work type
        permit_requirements = {
            "pump": {
                "maintenance": ["work-permit", "safety-permit"],
                "repair": ["hot-work-permit", "safety-permit", "electrical-permit"]
            },
            "valve": {
                "maintenance": ["work-permit"],
                "repair": ["work-permit", "pressure-permit"]
            }
        }
        
        equipment_type = equipment_id.split('-')[0]  # Extract type from ID like "pump-001"
        required_permits = permit_requirements.get(equipment_type, {}).get(work_type, ["work-permit"])
        
        return {
            "equipment_id": equipment_id,
            "work_type": work_type,
            "required_permits": required_permits,
            "permit_required": len(required_permits) > 0
        }

    def create_permit_request(self, workorder_id: str, permit_type: str, description: str = "") -> Dict[str, Any]:
        # Simulate creating permit via .NET Core API
        permit_id = f"PERMIT-{workorder_id}-{permit_type.upper()}"
        
        permit = Permit(
            permit_id=permit_id,
            workorder_id=workorder_id,
            type=permit_type,
            status=PermitStatus.DRAFT,
            required=True
        )
        
        # In real implementation, make API call to .NET Core system
        # response = requests.post(f"{self.api_base_url}/api/permits", json=permit.dict())
        
        return {
            "success": True,
            "permit_id": permit_id,
            "permit": permit.dict(),
            "message": f"Permit request created for {permit_type}"
        }

    async def run_server(self):
        await self.server.run()

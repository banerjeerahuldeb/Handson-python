# models/workorder.py
from typing import List, Dict, Any
from datetime import datetime

class WorkOrder:
    def __init__(self, workorder_id: int, equipment_id: str, description: str, 
                 priority: str, status: str, created_date: str):
        self.workorder_id = workorder_id
        self.equipment_id = equipment_id
        self.description = description
        self.priority = priority
        self.status = status
        self.created_date = created_date
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "workorder_id": self.workorder_id,
            "equipment_id": self.equipment_id,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "created_date": self.created_date
        }

# Sample work orders
SAMPLE_WORKORDERS = [
    WorkOrder(1, "pump-001", "Replace bearing", "high", "open", "2024-03-20"),
    WorkOrder(2, "compressor-002", "Monthly maintenance", "medium", "in progress", "2024-03-18"),
    WorkOrder(3, "generator-003", "Fuel system check", "low", "completed", "2024-03-15")
]

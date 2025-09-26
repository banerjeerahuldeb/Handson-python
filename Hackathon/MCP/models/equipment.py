# models/equipment.py
from typing import List, Dict, Any
from datetime import datetime

class Equipment:
    def __init__(self, equipment_id: str, name: str, category: str, status: str, 
                 location: str, last_maintenance: str = None):
        self.equipment_id = equipment_id
        self.name = name
        self.category = category
        self.status = status
        self.location = location
        self.last_maintenance = last_maintenance
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "equipment_id": self.equipment_id,
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "location": self.location,
            "last_maintenance": self.last_maintenance
        }

# Sample equipment data
SAMPLE_EQUIPMENT = [
    Equipment("pump-001", "Centrifugal Pump", "Pump", "Operational", "Plant A", "2024-01-15"),
    Equipment("compressor-002", "Air Compressor", "Compressor", "Maintenance", "Plant B", "2024-02-20"),
    Equipment("generator-003", "Backup Generator", "Generator", "Operational", "Plant C", "2024-01-10"),
    Equipment("valve-004", "Control Valve", "Valve", "Operational", "Plant A", "2024-03-05"),
    Equipment("motor-005", "Electric Motor", "Motor", "Idle", "Plant B", "2024-02-28")
]

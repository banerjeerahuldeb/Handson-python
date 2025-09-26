from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.data_models import PermitStatus, SystemHealthStatus, SystemHealth
import time

router = APIRouter()

# In-memory storage for permits (in production, use database)
permits_db = {}
permit_rules_db = {
    "pump": {
        "maintenance": ["work-permit"],
        "repair": ["hot-work-permit", "safety-permit"],
        "installation": ["work-permit", "safety-permit", "electrical-permit"]
    },
    "valve": {
        "maintenance": ["work-permit"],
        "repair": ["pressure-permit", "safety-permit"],
        "replacement": ["work-permit", "pressure-permit"]
    },
    "motor": {
        "maintenance": ["work-permit"],
        "repair": ["electrical-permit", "safety-permit"],
        "installation": ["electrical-permit", "work-permit"]
    }
}

class PermitRequest(BaseModel):
    workorder_id: str
    permit_type: str
    description: str
    required_documents: List[str] = []
    urgency: str = "normal"

class PermitResponse(BaseModel):
    permit_id: str
    status: str
    message: str
    submitted_date: Optional[datetime] = None
    estimated_approval_time: Optional[str] = None

@router.get("/health")
async def health_check():
    """Health check endpoint for permit system"""
    start_time = time.time()
    
    # Simulate some checks
    health_status = SystemHealth.HEALTHY
    details = {
        "total_permits": len(permits_db),
        "permit_rules_loaded": len(permit_rules_db),
        "api_version": "1.0.0"
    }
    
    response_time = (time.time() - start_time) * 1000
    
    return SystemHealthStatus(
        system_name="permit-api",
        status=health_status,
        response_time=response_time,
        details=details
    )

@router.get("/permits/required/{equipment_type}")
async def get_required_permits(equipment_type: str, work_type: str):
    """Get required permits for specific equipment and work type"""
    equipment_type = equipment_type.lower()
    work_type = work_type.lower()
    
    if equipment_type not in permit_rules_db:
        raise HTTPException(status_code=404, detail=f"Equipment type '{equipment_type}' not found")
    
    if work_type not in permit_rules_db[equipment_type]:
        # Default to maintenance if work type not found
        work_type = "maintenance"
    
    required_permits = permit_rules_db[equipment_type].get(work_type, ["work-permit"])
    
    return {
        "equipment_type": equipment_type,
        "work_type": work_type,
        "required_permits": required_permits,
        "permit_required": len(required_permits) > 0,
        "notes": f"Permits required for {work_type} on {equipment_type}"
    }

@router.post("/permits", response_model=PermitResponse)
async def create_permit(request: PermitRequest):
    """Create a new permit request"""
    permit_id = f"PERMIT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Determine estimated approval time based on urgency
    approval_times = {
        "emergency": "1 hour",
        "high": "4 hours", 
        "normal": "24 hours",
        "low": "48 hours"
    }
    
    estimated_time = approval_times.get(request.urgency, "24 hours")
    
    permit_data = {
        "permit_id": permit_id,
        "workorder_id": request.workorder_id,
        "permit_type": request.permit_type,
        "description": request.description,
        "status": PermitStatus.DRAFT.value,
        "required_documents": request.required_documents,
        "urgency": request.urgency,
        "created_date": datetime.now(),
        "estimated_approval_time": estimated_time
    }
    
    permits_db[permit_id] = permit_data
    
    return PermitResponse(
        permit_id=permit_id,
        status=PermitStatus.DRAFT.value,
        message=f"Permit {permit_id} created successfully",
        submitted_date=datetime.now(),
        estimated_approval_time=estimated_time
    )

@router.put("/permits/{permit_id}/submit")
async def submit_permit(permit_id: str):
    """Submit a permit for approval"""
    if permit_id not in permits_db:
        raise HTTPException(status_code=404, detail="Permit not found")
    
    permits_db[permit_id]["status"] = PermitStatus.SUBMITTED.value
    permits_db[permit_id]["submitted_date"] = datetime.now()
    
    return {
        "permit_id": permit_id,
        "status": "submitted",
        "message": "Permit submitted for approval",
        "submitted_date": datetime.now().isoformat()
    }

@router.put("/permits/{permit_id}/approve")
async def approve_permit(permit_id: str, approver: str, comments: Optional[str] = None):
    """Approve a permit"""
    if permit_id not in permits_db:
        raise HTTPException(status_code=404, detail="Permit not found")
    
    permits_db[permit_id]["status"] = PermitStatus.APPROVED.value
    permits_db[permit_id]["approved_date"] = datetime.now()
    permits_db[permit_id]["approver"] = approver
    permits_db[permit_id]["approver_comments"] = comments
    
    return {
        "permit_id": permit_id,
        "status": "approved",
        "approver": approver,
        "approval_date": datetime.now().isoformat(),
        "message": "Permit approved successfully"
    }

@router.get("/permits/{permit_id}")
async def get_permit(permit_id: str):
    """Get permit details"""
    if permit_id not in permits_db:
        raise HTTPException(status_code=404, detail="Permit not found")
    
    return permits_db[permit_id]

@router.get("/permits")
async def list_permits(status: Optional[str] = None, workorder_id: Optional[str] = None):
    """List permits with optional filtering"""
    filtered_permits = permits_db.values()
    
    if status:
        filtered_permits = [p for p in filtered_permits if p["status"] == status]
    
    if workorder_id:
        filtered_permits = [p for p in filtered_permits if p["workorder_id"] == workorder_id]
    
    return {
        "permits": list(filtered_permits),
        "count": len(filtered_permits),
        "filters": {
            "status": status,
            "workorder_id": workorder_id
        }
    }

@router.get("/permit-rules")
async def get_permit_rules():
    """Get all permit rules"""
    return {
        "permit_rules": permit_rules_db,
        "last_updated": datetime.now().isoformat()
    }

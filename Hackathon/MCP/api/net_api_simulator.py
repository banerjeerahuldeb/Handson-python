from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uvicorn
from models.data_models import Permit, PermitStatus

app = FastAPI(title="Permit Management API", description="Simulated .NET Core API for Permit Management")

# In-memory storage for permits
permits_db = {}

class PermitRequest(BaseModel):
    workorder_id: str
    permit_type: str
    description: str
    required_documents: List[str] = []

class PermitResponse(BaseModel):
    permit_id: str
    status: str
    message: str
    submitted_date: Optional[datetime] = None

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "permit-management", "timestamp": datetime.now()}

@app.get("/api/permits/required/{equipment_type}")
async def get_required_permits(equipment_type: str, work_type: str):
    """Get required permits for equipment type and work type"""
    permit_rules = {
        "pump": {
            "maintenance": ["work-permit"],
            "repair": ["hot-work-permit", "safety-permit"],
            "installation": ["work-permit", "safety-permit"]
        },
        "valve": {
            "maintenance": ["work-permit"],
            "repair": ["pressure-permit", "safety-permit"]
        },
        "motor": {
            "maintenance": ["work-permit"],
            "repair": ["electrical-permit", "safety-permit"]
        }
    }
    
    required_permits = permit_rules.get(equipment_type, {}).get(work_type, ["work-permit"])
    
    return {
        "equipment_type": equipment_type,
        "work_type": work_type,
        "required_permits": required_permits,
        "permit_required": len(required_permits) > 0
    }

@app.post("/api/permits", response_model=PermitResponse)
async def create_permit(request: PermitRequest):
    """Create a new permit request"""
    permit_id = f"PERMIT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    permit = Permit(
        permit_id=permit_id,
        workorder_id=request.workorder_id,
        permit_type=request.permit_type,
        status=PermitStatus.DRAFT,
        required=True,
        submitted_date=datetime.now()
    )
    
    permits_db[permit_id] = permit.dict()
    
    return PermitResponse(
        permit_id=permit_id,
        status=permit.status.value,
        message=f"Permit {permit_id} created successfully",
        submitted_date=permit.submitted_date
    )

@app.put("/api/permits/{permit_id}/submit")
async def submit_permit(permit_id: str):
    """Submit permit for approval"""
    if permit_id not in permits_db:
        raise HTTPException(status_code=404, detail="Permit not found")
    
    permits_db[permit_id]['status'] = PermitStatus.SUBMITTED.value
    permits_db[permit_id]['submitted_date'] = datetime.now()
    
    return {
        "permit_id": permit_id,
        "status": "submitted",
        "message": "Permit submitted for approval"
    }

@app.put("/api/permits/{permit_id}/approve")
async def approve_permit(permit_id: str, approver: str):
    """Approve a permit"""
    if permit_id not in permits_db:
        raise HTTPException(status_code=404, detail="Permit not found")
    
    permits_db[permit_id]['status'] = PermitStatus.APPROVED.value
    permits_db[permit_id]['approved_date'] = datetime.now()
    permits_db[permit_id]['approver'] = approver
    
    return {
        "permit_id": permit_id,
        "status": "approved",
        "approver": approver,
        "message": "Permit approved successfully"
    }

@app.get("/api/permits/{permit_id}")
async def get_permit(permit_id: str):
    """Get permit details"""
    if permit_id not in permits_db:
        raise HTTPException(status_code=404, detail="Permit not found")
    
    return permits_db[permit_id]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import hashlib
import json
from models.data_models import ApprovalRequest, ApprovalStatus, WorkflowResponse

approval_router = APIRouter()

# In-memory storage for approval requests (in production, use database)
approval_requests: Dict[str, ApprovalRequest] = {}

class ApprovalAction(BaseModel):
    approval_code: str
    action: str  # "approve" or "reject"
    approver: str
    comments: Optional[str] = None

def generate_approval_code(workorder_id: str, timestamp: datetime) -> str:
    """Generate unique approval code"""
    hash_input = f"{workorder_id}-{timestamp.isoformat()}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:8].upper()

@approval_router.post("/workflow/request-approval")
async def request_approval(workorder_id: str, requested_by: str, approval_items: List[Dict[str, Any]]):
    """Request approval for a workflow"""
    approval_code = generate_approval_code(workorder_id, datetime.now())
    
    approval_request = ApprovalRequest(
        approval_code=approval_code,
        workorder_id=workorder_id,
        requested_by=requested_by,
        approval_items=approval_items,
        status=ApprovalStatus.PENDING
    )
    
    approval_requests[approval_code] = approval_request
    
    # In production, send email notification here
    
    return {
        "approval_code": approval_code,
        "workorder_id": workorder_id,
        "message": "Approval requested successfully",
        "approval_url": f"/approve/{approval_code}"  # URL for approvers
    }

@approval_router.get("/approval/{approval_code}")
async def get_approval_request(approval_code: str):
    """Get approval request details"""
    if approval_code not in approval_requests:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    return approval_requests[approval_code]

@approval_router.post("/approval/action")
async def process_approval(action: ApprovalAction):
    """Process approval action (approve/reject)"""
    if action.approval_code not in approval_requests:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    approval_request = approval_requests[action.approval_code]
    
    if action.action.lower() == "approve":
        approval_request.status = ApprovalStatus.APPROVED
        message = "Workflow approved successfully"
    elif action.action.lower() == "reject":
        approval_request.status = ApprovalStatus.REJECTED
        message = "Workflow rejected"
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")
    
    approval_request.comments = action.comments
    
    # Update work order status based on approval
    # This would typically call the workorders MCP server
    
    return {
        "approval_code": action.approval_code,
        "workorder_id": approval_request.workorder_id,
        "status": approval_request.status.value,
        "message": message,
        "approver": action.approver
    }

@approval_router.get("/approvals/pending")
async def get_pending_approvals():
    """Get all pending approval requests"""
    pending = [
        request.dict() for request in approval_requests.values() 
        if request.status == ApprovalStatus.PENDING
    ]
    
    return {
        "pending_approvals": pending,
        "count": len(pending)
    }

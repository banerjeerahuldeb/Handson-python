from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class WorkOrderStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class PermitStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class SystemHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"

class InventoryItem(BaseModel):
    item_id: str = Field(..., description="Unique item identifier")
    name: str = Field(..., description="Item name")
    description: str = Field(..., description="Item description")
    quantity: int = Field(..., ge=0, description="Current stock quantity")
    min_stock: int = Field(..., ge=0, description="Minimum stock level")
    max_stock: int = Field(..., ge=0, description="Maximum stock level")
    location: str = Field(..., description="Storage location")
    last_updated: datetime = Field(default_factory=datetime.now)

class WorkOrder(BaseModel):
    workorder_id: str = Field(..., description="Work order ID")
    equipment_id: str = Field(..., description="Equipment identifier")
    title: str = Field(..., description="Work order title")
    description: str = Field(..., description="Detailed description")
    status: WorkOrderStatus = Field(default=WorkOrderStatus.DRAFT)
    priority: str = Field(default="medium", description="Priority level")
    created_date: datetime = Field(default_factory=datetime.now)
    assigned_to: Optional[str] = Field(None, description="Assigned employee ID")
    required_parts: List[str] = Field(default_factory=list)
    permits_required: List[str] = Field(default_factory=list)
    estimated_hours: Optional[float] = Field(None, ge=0)
    actual_hours: Optional[float] = Field(None, ge=0)

class Permit(BaseModel):
    permit_id: str = Field(..., description="Permit ID")
    workorder_id: str = Field(..., description="Associated work order")
    permit_type: str = Field(..., description="Type of permit")
    status: PermitStatus = Field(default=PermitStatus.DRAFT)
    required: bool = Field(default=True)
    submitted_date: Optional[datetime] = Field(None)
    approved_date: Optional[datetime] = Field(None)
    approver: Optional[str] = Field(None)

class Employee(BaseModel):
    employee_id: str = Field(..., description="Employee ID")
    name: str = Field(..., description="Employee name")
    department: str = Field(..., description="Department")
    position: str = Field(..., description="Job position")
    skills: List[str] = Field(default_factory=list)
    current_workload: int = Field(default=0, ge=0)
    max_workload: int = Field(default=5, ge=1)
    available: bool = Field(default=True)
    email: str = Field(..., description="Contact email")

class WorkflowRequest(BaseModel):
    equipment_id: str = Field(..., description="Equipment ID")
    issue_description: str = Field(..., description="Issue details")
    priority: str = Field(default="medium")
    requested_by: str = Field(..., description="Requester name")
    department: str = Field(..., description="Requesting department")

class WorkflowResponse(BaseModel):
    success: bool = Field(..., description="Workflow success status")
    workorder_id: Optional[str] = Field(None, description="Created work order ID")
    message: str = Field(..., description="Response message")
    actions_taken: List[str] = Field(default_factory=list)
    requires_approval: bool = Field(default=False)
    approval_code: Optional[str] = Field(None, description="Approval tracking code")
    details: Dict[str, Any] = Field(default_factory=dict)

class SystemHealthStatus(BaseModel):
    system_name: str = Field(..., description="System name")
    status: SystemHealth = Field(..., description="Health status")
    response_time: float = Field(..., description="Response time in ms")
    last_checked: datetime = Field(default_factory=datetime.now)
    details: Dict[str, Any] = Field(default_factory=dict)

class ApprovalRequest(BaseModel):
    approval_code: str = Field(..., description="Unique approval code")
    workorder_id: str = Field(..., description="Work order to approve")
    requested_by: str = Field(..., description="Who requested approval")
    requested_date: datetime = Field(default_factory=datetime.now)
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING)
    approval_items: List[Dict[str, Any]] = Field(default_factory=list)
    comments: Optional[str] = Field(None, description="Approval comments")

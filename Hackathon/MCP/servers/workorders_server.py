from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text
from config.settings import ORACLE_CONNECTION_STRING
from models.data_models import WorkOrder, WorkOrderStatus, SystemHealthStatus, SystemHealth
from datetime import datetime
import time
import json

app = FastAPI(title="WorkOrders MCP Server")

class MCPRequest(BaseModel):
    method: str
    params: Dict[str, Any] = {}

engine = create_engine(ORACLE_CONNECTION_STRING)

@app.get("/health")
async def health_check():
    start_time = time.time()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM DUAL"))
        response_time = (time.time() - start_time) * 1000
        
        return SystemHealthStatus(
            system_name="workorders-mcp-server",
            status=SystemHealth.HEALTHY,
            response_time=response_time,
            details={"database": "connected", "tables": ["workorders"]}
        )
    except Exception as e:
        return SystemHealthStatus(
            system_name="workorders-mcp-server",
            status=SystemHealth.DOWN,
            response_time=0,
            details={"error": str(e)}
        )

@app.post("/mcp/workorders/check")
async def check_workorders(request: MCPRequest):
    """Check existing work orders for equipment"""
    try:
        equipment_id = request.params.get("equipment_id")
        status_filter = request.params.get("status_filter", [])
        
        if not equipment_id:
            raise HTTPException(status_code=400, detail="Equipment ID required")
        
        with engine.connect() as conn:
            query = text("""
                SELECT workorder_id, equipment_id, title, description, status, priority,
                       created_date, assigned_to, required_parts, permits_required,
                       estimated_hours, actual_hours
                FROM workorders 
                WHERE equipment_id = :equipment_id
            """)
            
            if status_filter:
                placeholders = ",".join([f"'{status}'" for status in status_filter])
                query = text(f"""
                    SELECT workorder_id, equipment_id, title, description, status, priority,
                           created_date, assigned_to, required_parts, permits_required,
                           estimated_hours, actual_hours
                    FROM workorders 
                    WHERE equipment_id = :equipment_id AND status IN ({placeholders})
                """)
            
            result = conn.execute(query, {"equipment_id": equipment_id})
            workorders = result.fetchall()
        
        workorder_list = []
        for wo in workorders:
            workorder_list.append({
                "workorder_id": wo[0],
                "equipment_id": wo[1],
                "title": wo[2],
                "description": wo[3],
                "status": wo[4],
                "priority": wo[5],
                "created_date": wo[6].isoformat() if wo[6] else None,
                "assigned_to": wo[7],
                "required_parts": json.loads(wo[8]) if wo[8] else [],
                "permits_required": json.loads(wo[9]) if wo[9] else [],
                "estimated_hours": float(wo[10]) if wo[10] else None,
                "actual_hours": float(wo[11]) if wo[11] else None
            })
        
        return {
            "equipment_id": equipment_id,
            "existing_workorders": workorder_list,
            "count": len(workorders),
            "active_count": len([wo for wo in workorder_list if wo["status"] in ["draft", "pending_approval", "approved", "in_progress"]])
        }
        
    except Exception as e:
        return {"error": str(e)}

@app.post("/mcp/workorders/create")
async def create_workorder(request: MCPRequest):
    """Create a new work order"""
    try:
        equipment_id = request.params.get("equipment_id")
        title = request.params.get("title", "Maintenance Work Order")
        description = request.params.get("description", "")
        priority = request.params.get("priority", "medium")
        required_parts = request.params.get("required_parts", [])
        assigned_to = request.params.get("assigned_to")
        
        if not equipment_id:
            raise HTTPException(status_code=400, detail="Equipment ID required")
        
        # Generate work order ID
        workorder_id = f"WO-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() % 10000):04d}"
        
        with engine.connect() as conn:
            # Get next sequence value for Oracle
            result = conn.execute(text("SELECT workorder_seq.NEXTVAL FROM DUAL"))
            seq_id = result.scalar()
            
            workorder_id = f"WO-{datetime.now().strftime('%Y%m%d')}-{seq_id:04d}"
            
            conn.execute(text("""
                INSERT INTO workorders (
                    workorder_id, equipment_id, title, description, status, priority,
                    assigned_to, required_parts, permits_required, created_date
                ) VALUES (
                    :workorder_id, :equipment_id, :title, :description, :status, :priority,
                    :assigned_to, :required_parts, :permits_required, :created_date
                )
            """), {
                "workorder_id": workorder_id,
                "equipment_id": equipment_id,
                "title": title,
                "description": description,
                "status": "draft",
                "priority": priority,
                "assigned_to": assigned_to,
                "required_parts": json.dumps(required_parts),
                "permits_required": json.dumps([]),
                "created_date": datetime.now()
            })
            
            conn.commit()
        
        return {
            "success": True,
            "workorder_id": workorder_id,
            "message": "Work order created successfully",
            "details": {
                "equipment_id": equipment_id,
                "title": title,
                "status": "draft",
                "created_date": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

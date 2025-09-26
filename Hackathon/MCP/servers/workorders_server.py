from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import psycopg2
from config.settings import DatabaseConfig
import time
import logging

app = FastAPI(title="WorkOrders MCP Server")

class MCPRequest(BaseModel):
    method: str
    params: Dict[str, Any] = {}

class MCPResponse(BaseModel):
    result: Dict[str, Any]
    error: Optional[str] = None

# Setup logging
logger = logging.getLogger(__name__)

def get_postgres_connection():
    """Get a connection to PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host=DatabaseConfig.POSTGRES_HOST,
            port=DatabaseConfig.POSTGRES_PORT,
            database=DatabaseConfig.POSTGRES_DB,
            user=DatabaseConfig.POSTGRES_USER,
            password=DatabaseConfig.POSTGRES_PASSWORD
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
        raise

@app.get("/health")
async def health_check():
    start_time = time.time()
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        
        response_time = (time.time() - start_time) * 1000
        
        return {
            "system_name": "workorders-mcp-server",
            "status": "healthy",
            "response_time": response_time,
            "details": {"database": "connected", "tables": ["workorders", "workorder_tasks"]}
        }
    except Exception as e:
        return {
            "system_name": "workorders-mcp-server",
            "status": "down",
            "response_time": 0,
            "details": {"error": str(e)}
        }

@app.post("/mcp/workorders/list")
async def list_workorders(request: MCPRequest):
    """Get workorders from PostgreSQL database, optionally filtered by status"""
    try:
        status_filter = request.params.get("status", None)
        
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        if status_filter:
            cursor.execute("""
                SELECT workorder_id, equipment_id, description, priority, status, 
                       assigned_to, created_date, completed_date, estimated_hours, actual_hours
                FROM workorders 
                WHERE status = %s
                ORDER BY created_date DESC
            """, (status_filter,))
        else:
            cursor.execute("""
                SELECT workorder_id, equipment_id, description, priority, status, 
                       assigned_to, created_date, completed_date, estimated_hours, actual_hours
                FROM workorders 
                ORDER BY created_date DESC
            """)
        
        workorders = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        workorder_list = []
        for row in workorders:
            workorder_dict = dict(zip(columns, row))
            # Convert dates to ISO format
            for date_field in ['created_date', 'completed_date']:
                if workorder_dict.get(date_field):
                    workorder_dict[date_field] = workorder_dict[date_field].isoformat()
            workorder_list.append(workorder_dict)
        
        cursor.close()
        conn.close()
        
        return MCPResponse(result={
            "workorders": workorder_list,
            "total_count": len(workorder_list),
            "status_filter": status_filter if status_filter else "all"
        })
        
    except Exception as e:
        logger.error(f"Error fetching workorders: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/workorders/create")
async def create_workorder(request: MCPRequest):
    """Create a new workorder in PostgreSQL database"""
    try:
        equipment_id = request.params.get("equipment_id")
        description = request.params.get("description")
        priority = request.params.get("priority", "medium")
        assigned_to = request.params.get("assigned_to")
        estimated_hours = request.params.get("estimated_hours")
        
        if not equipment_id or not description:
            raise HTTPException(status_code=400, detail="Equipment ID and description are required")
        
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO workorders (equipment_id, description, priority, status, assigned_to, estimated_hours)
            VALUES (%s, %s, %s, 'open', %s, %s)
            RETURNING workorder_id, created_date
        """, (equipment_id, description, priority, assigned_to, estimated_hours))
        
        result = cursor.fetchone()
        workorder_id = result[0]
        created_date = result[1]
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return MCPResponse(result={
            "success": True,
            "workorder_id": workorder_id,
            "message": "Workorder created successfully",
            "created_date": created_date.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error creating workorder: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/workorders/update")
async def update_workorder(request: MCPRequest):
    """Update workorder status and optionally actual hours in PostgreSQL database"""
    try:
        workorder_id = request.params.get("workorder_id")
        status = request.params.get("status")
        actual_hours = request.params.get("actual_hours")
        
        if not workorder_id or not status:
            raise HTTPException(status_code=400, detail="Workorder ID and status are required")
        
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        if actual_hours is not None:
            cursor.execute("""
                UPDATE workorders 
                SET status = %s, actual_hours = %s, 
                    completed_date = CASE WHEN %s = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_date END
                WHERE workorder_id = %s
                RETURNING workorder_id
            """, (status, actual_hours, status, workorder_id))
        else:
            cursor.execute("""
                UPDATE workorders 
                SET status = %s, 
                    completed_date = CASE WHEN %s = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_date END
                WHERE workorder_id = %s
                RETURNING workorder_id
            """, (status, status, workorder_id))
        
        result = cursor.fetchone()
        conn.commit()
        affected_rows = cursor.rowcount
        
        cursor.close()
        conn.close()
        
        if affected_rows == 0:
            return MCPResponse(result={
                "success": False,
                "message": f"Workorder with ID {workorder_id} not found"
            })
        else:
            return MCPResponse(result={
                "success": True,
                "message": "Workorder updated successfully",
                "workorder_id": workorder_id,
                "new_status": status
            })
            
    except Exception as e:
        logger.error(f"Error updating workorder: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/workorders/tasks")
async def get_workorder_tasks(request: MCPRequest):
    """Get tasks for a specific workorder from PostgreSQL database"""
    try:
        workorder_id = request.params.get("workorder_id")
        
        if not workorder_id:
            raise HTTPException(status_code=400, detail="Workorder ID is required")
        
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT task_id, task_description, status, sequence, estimated_hours, actual_hours
            FROM workorder_tasks
            WHERE workorder_id = %s
            ORDER BY sequence
        """, (workorder_id,))
        
        tasks = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        task_list = []
        for task in tasks:
            task_dict = dict(zip(columns, task))
            task_list.append(task_dict)
        
        cursor.close()
        conn.close()
        
        return MCPResponse(result={
            "workorder_id": workorder_id,
            "tasks": task_list,
            "total_tasks": len(task_list)
        })
        
    except Exception as e:
        logger.error(f"Error fetching workorder tasks: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/workorders/details")
async def get_workorder_details(request: MCPRequest):
    """Get detailed information for a specific workorder"""
    try:
        workorder_id = request.params.get("workorder_id")
        
        if not workorder_id:
            raise HTTPException(status_code=400, detail="Workorder ID is required")
        
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT workorder_id, equipment_id, description, priority, status, 
                   assigned_to, created_date, completed_date, estimated_hours, actual_hours,
                   notes, location, department
            FROM workorders 
            WHERE workorder_id = %s
        """, (workorder_id,))
        
        workorder = cursor.fetchone()
        
        if not workorder:
            cursor.close()
            conn.close()
            return MCPResponse(result={
                "error": f"Workorder with ID {workorder_id} not found"
            })
        
        columns = [desc[0] for desc in cursor.description]
        workorder_dict = dict(zip(columns, workorder))
        
        # Convert dates to ISO format
        for date_field in ['created_date', 'completed_date']:
            if workorder_dict.get(date_field):
                workorder_dict[date_field] = workorder_dict[date_field].isoformat()
        
        cursor.close()
        conn.close()
        
        return MCPResponse(result={
            "workorder": workorder_dict
        })
        
    except Exception as e:
        logger.error(f"Error fetching workorder details: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/workorders/assign")
async def assign_workorder(request: MCPRequest):
    """Assign a workorder to a specific technician"""
    try:
        workorder_id = request.params.get("workorder_id")
        assigned_to = request.params.get("assigned_to")
        
        if not workorder_id or not assigned_to:
            raise HTTPException(status_code=400, detail="Workorder ID and assigned_to are required")
        
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE workorders 
            SET assigned_to = %s, status = 'assigned'
            WHERE workorder_id = %s
            RETURNING workorder_id
        """, (assigned_to, workorder_id))
        
        result = cursor.fetchone()
        conn.commit()
        affected_rows = cursor.rowcount
        
        cursor.close()
        conn.close()
        
        if affected_rows == 0:
            return MCPResponse(result={
                "success": False,
                "message": f"Workorder with ID {workorder_id} not found"
            })
        else:
            return MCPResponse(result={
                "success": True,
                "message": "Workorder assigned successfully",
                "workorder_id": workorder_id,
                "assigned_to": assigned_to
            })
            
    except Exception as e:
        logger.error(f"Error assigning workorder: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/workorders/statistics")
async def get_workorder_statistics(request: MCPRequest):
    """Get workorder statistics by status and priority"""
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        # Get counts by status
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM workorders 
            GROUP BY status
        """)
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Get counts by priority
        cursor.execute("""
            SELECT priority, COUNT(*) as count 
            FROM workorders 
            GROUP BY priority
        """)
        priority_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Get average completion time
        cursor.execute("""
            SELECT AVG(EXTRACT(EPOCH FROM (completed_date - created_date))/3600) as avg_hours
            FROM workorders 
            WHERE status = 'completed' AND completed_date IS NOT NULL
        """)
        avg_completion_hours = cursor.fetchone()[0] or 0
        
        cursor.close()
        conn.close()
        
        return MCPResponse(result={
            "statistics": {
                "by_status": status_counts,
                "by_priority": priority_counts,
                "average_completion_hours": round(float(avg_completion_hours), 2),
                "total_workorders": sum(status_counts.values())
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching workorder statistics: {str(e)}")
        return MCPResponse(result={}, error=str(e))

if __name__ == "__main__":
    import uvicorn
    print("Starting WorkOrders MCP Server on http://localhost:8003")
    uvicorn.run(app, host="0.0.0.0", port=8003)

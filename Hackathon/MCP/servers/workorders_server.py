import os
import sys
import logging
from typing import List, Dict, Any
import psycopg2
from mcp.server.fastmcp import FastMCP

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DatabaseConfig

# Initialize FastMCP server
mcp = FastMCP("WorkOrders")

logger = logging.getLogger(__name__)

def get_postgres_connection():
    """Get a connection to PostgreSQL database"""
    return psycopg2.connect(
        host=DatabaseConfig.POSTGRES_HOST,
        port=DatabaseConfig.POSTGRES_PORT,
        database=DatabaseConfig.POSTGRES_DB,
        user=DatabaseConfig.POSTGRES_USER,
        password=DatabaseConfig.POSTGRES_PASSWORD
    )

@mcp.tool()
def get_workorders(status: str = None) -> List[Dict[str, Any]]:
    """Get workorders from PostgreSQL database, optionally filtered by status"""
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT workorder_id, equipment_id, description, priority, status, 
                       assigned_to, created_date, completed_date, estimated_hours, actual_hours
                FROM workorders 
                WHERE status = %s
                ORDER BY created_date DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT workorder_id, equipment_id, description, priority, status, 
                       assigned_to, created_date, completed_date, estimated_hours, actual_hours
                FROM workorders 
                ORDER BY created_date DESC
            """)
        
        columns = [desc[0] for desc in cursor.description]
        workorders = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return workorders
    except Exception as e:
        logger.error(f"Error fetching workorders: {str(e)}")
        return []

@mcp.tool()
def create_workorder(equipment_id: str, description: str, priority: str = 'medium', 
                    assigned_to: str = None, estimated_hours: float = None) -> Dict[str, Any]:
    """Create a new workorder in PostgreSQL database"""
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO workorders (equipment_id, description, priority, status, assigned_to, estimated_hours)
            VALUES (%s, %s, %s, 'open', %s, %s)
            RETURNING workorder_id
        """, (equipment_id, description, priority, assigned_to, estimated_hours))
        
        workorder_id = cursor.fetchone()[0]
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return {"success": True, "workorder_id": workorder_id, "message": "Workorder created successfully"}
    except Exception as e:
        logger.error(f"Error creating workorder: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def update_workorder_status(workorder_id: int, status: str, actual_hours: float = None) -> Dict[str, Any]:
    """Update workorder status and optionally actual hours in PostgreSQL database"""
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        if actual_hours is not None:
            cursor.execute("""
                UPDATE workorders 
                SET status = %s, actual_hours = %s, completed_date = CASE WHEN %s = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_date END
                WHERE workorder_id = %s
            """, (status, actual_hours, status, workorder_id))
        else:
            cursor.execute("""
                UPDATE workorders 
                SET status = %s, completed_date = CASE WHEN %s = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_date END
                WHERE workorder_id = %s
            """, (status, status, workorder_id))
        
        conn.commit()
        affected_rows = cursor.rowcount
        
        cursor.close()
        conn.close()
        
        if affected_rows == 0:
            return {"success": False, "message": f"Workorder with ID {workorder_id} not found"}
        else:
            return {"success": True, "message": "Workorder updated successfully"}
    except Exception as e:
        logger.error(f"Error updating workorder: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def get_workorder_tasks(workorder_id: int) -> List[Dict[str, Any]]:
    """Get tasks for a specific workorder from PostgreSQL database"""
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT task_id, task_description, status, sequence
            FROM workorder_tasks
            WHERE workorder_id = %s
            ORDER BY sequence
        """, (workorder_id,))
        
        columns = [desc[0] for desc in cursor.description]
        tasks = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return tasks
    except Exception as e:
        logger.error(f"Error fetching workorder tasks: {str(e)}")
        return []

if __name__ == "__main__":
    # Start the server
    mcp.run(transport='stdio')

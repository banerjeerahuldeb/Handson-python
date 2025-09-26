import os
import sys
import logging
from typing import List, Dict, Any, Optional
import pyodbc
from mcp.server.fastmcp import FastMCP

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DatabaseConfig, SQL_SERVER_CONNECTION_STRING

# Initialize FastMCP server
mcp = FastMCP("Inventory")

logger = logging.getLogger(__name__)

def get_sql_server_connection():
    """Get a connection to SQL Server database using Windows Authentication"""
    try:
        conn = pyodbc.connect(SQL_SERVER_CONNECTION_STRING)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to SQL Server: {str(e)}")
        raise

@mcp.tool()
def get_equipment_list(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get equipment list from SQL Server database, optionally filtered by status"""
    try:
        conn = get_sql_server_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT EquipmentID, EquipmentName, Category, Status, Location, LastMaintenanceDate
                FROM Equipment 
                WHERE Status = ?
                ORDER BY EquipmentName
            """, (status,))
        else:
            cursor.execute("""
                SELECT EquipmentID, EquipmentName, Category, Status, Location, LastMaintenanceDate
                FROM Equipment 
                ORDER BY EquipmentName
            """)
        
        columns = [desc[0] for desc in cursor.description]
        equipment_list = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return equipment_list
    except Exception as e:
        logger.error(f"Error fetching equipment list: {str(e)}")
        return []

@mcp.tool()
def get_equipment_details(equipment_id: str) -> Dict[str, Any]:
    """Get detailed information for a specific equipment item"""
    try:
        conn = get_sql_server_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT EquipmentID, EquipmentName, Category, Status, Location, 
                   LastMaintenanceDate, InstallationDate, Manufacturer, Model, SerialNumber
            FROM Equipment 
            WHERE EquipmentID = ?
        """, (equipment_id,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        else:
            return {"error": f"Equipment with ID {equipment_id} not found"}
    except Exception as e:
        logger.error(f"Error fetching equipment details: {str(e)}")
        return {"error": str(e)}

@mcp.tool()
def get_equipment_by_category(category: str) -> List[Dict[str, Any]]:
    """Get equipment filtered by category"""
    try:
        conn = get_sql_server_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT EquipmentID, EquipmentName, Category, Status, Location, LastMaintenanceDate
            FROM Equipment 
            WHERE Category = ?
            ORDER BY EquipmentName
        """, (category,))
        
        columns = [desc[0] for desc in cursor.description]
        equipment_list = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return equipment_list
    except Exception as e:
        logger.error(f"Error fetching equipment by category: {str(e)}")
        return []

@mcp.tool()
def update_equipment_status(equipment_id: str, status: str) -> Dict[str, Any]:
    """Update equipment status in the database"""
    try:
        conn = get_sql_server_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE Equipment 
            SET Status = ? 
            WHERE EquipmentID = ?
        """, (status, equipment_id))
        
        conn.commit()
        affected_rows = cursor.rowcount
        
        cursor.close()
        conn.close()
        
        if affected_rows == 0:
            return {"success": False, "message": f"Equipment with ID {equipment_id} not found"}
        else:
            return {"success": True, "message": "Equipment status updated successfully"}
    except Exception as e:
        logger.error(f"Error updating equipment status: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def get_maintenance_schedule() -> List[Dict[str, Any]]:
    """Get equipment due for maintenance"""
    try:
        conn = get_sql_server_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT EquipmentID, EquipmentName, Category, Status, Location, 
                   LastMaintenanceDate, 
                   DATEADD(month, 3, LastMaintenanceDate) as NextMaintenanceDate
            FROM Equipment 
            WHERE Status = 'Operational'
            ORDER BY NextMaintenanceDate
        """)
        
        columns = [desc[0] for desc in cursor.description]
        schedule = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return schedule
    except Exception as e:
        logger.error(f"Error fetching maintenance schedule: {str(e)}")
        return []

@mcp.tool()
def search_equipment(search_term: str) -> List[Dict[str, Any]]:
    """Search equipment by name or ID"""
    try:
        conn = get_sql_server_connection()
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        cursor.execute("""
            SELECT EquipmentID, EquipmentName, Category, Status, Location, LastMaintenanceDate
            FROM Equipment 
            WHERE EquipmentID LIKE ? OR EquipmentName LIKE ?
            ORDER BY EquipmentName
        """, (search_pattern, search_pattern))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return results
    except Exception as e:
        logger.error(f"Error searching equipment: {str(e)}")
        return []

def test_connection():
    """Test the SQL Server connection"""
    try:
        conn = get_sql_server_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT @@version as version")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        logger.info(f"Connected to SQL Server: {DatabaseConfig.SQL_SERVER_HOST}")
        return True, f"SQL Server version: {version}"
    except Exception as e:
        logger.error(f"SQL Server connection failed: {str(e)}")
        return False, str(e)

if __name__ == "__main__":
    # Test connection on startup
    success, message = test_connection()
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")
    
    # Start the server
    print("Starting Inventory MCP Server...")
    mcp.run(transport='stdio')

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pyodbc
from config.settings import DatabaseConfig
from models.data_models import InventoryItem, SystemHealthStatus, SystemHealth
import time
import logging

app = FastAPI(title="Inventory MCP Server")

class MCPRequest(BaseModel):
    method: str
    params: Dict[str, Any] = {}

class MCPResponse(BaseModel):
    result: Dict[str, Any]
    error: Optional[str] = None

# Setup logging
logger = logging.getLogger(__name__)

def get_sql_server_connection():
    """Get a connection to SQL Server database using Windows Authentication"""
    try:
        # Use pyodbc directly for Windows Authentication
        conn_str = f"""
            DRIVER={{ODBC Driver 17 for SQL Server}};
            SERVER={DatabaseConfig.SQL_SERVER_HOST};
            DATABASE={DatabaseConfig.SQL_SERVER_DB};
            Trusted_Connection=yes;
        """
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to SQL Server: {str(e)}")
        raise

@app.get("/health")
async def health_check():
    start_time = time.time()
    try:
        conn = get_sql_server_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        
        response_time = (time.time() - start_time) * 1000
        
        return SystemHealthStatus(
            system_name="inventory-mcp-server",
            status=SystemHealth.HEALTHY,
            response_time=response_time,
            details={"database": "connected", "tables": ["inventory"]}
        )
    except Exception as e:
        return SystemHealthStatus(
            system_name="inventory-mcp-server",
            status=SystemHealth.DOWN,
            response_time=0,
            details={"error": str(e)}
        )

@app.post("/mcp/inventory/check")
async def check_inventory(request: MCPRequest):
    """Check inventory for specific items"""
    try:
        item_codes = request.params.get("item_codes", [])
        quantities = request.params.get("quantities", {})
        
        if not item_codes:
            raise HTTPException(status_code=400, detail="No item codes provided")
        
        conn = get_sql_server_connection()
        cursor = conn.cursor()
        
        # Create parameter placeholders for the IN clause
        placeholders = ",".join(["?"] * len(item_codes))
        query = f"SELECT * FROM inventory WHERE item_id IN ({placeholders})"
        
        cursor.execute(query, item_codes)
        items = cursor.fetchall()
        
        # Get column names
        columns = [column[0] for column in cursor.description]
        
        inventory_status = {}
        for item in items:
            item_dict = dict(zip(columns, item))
            item_id = item_dict['item_id']
            qty = item_dict['quantity']
            required_qty = quantities.get(item_id, 1)
            
            inventory_status[item_id] = {
                "name": item_dict.get('name', ''),
                "description": item_dict.get('description', ''),
                "available_quantity": qty,
                "required_quantity": required_qty,
                "sufficient": qty >= required_qty,
                "location": item_dict.get('location', ''),
                "last_updated": item_dict.get('last_updated', '').isoformat() if item_dict.get('last_updated') else None
            }
        
        cursor.close()
        conn.close()
        
        all_available = all(status["sufficient"] for status in inventory_status.values())
        
        return MCPResponse(result={
            "available_items": inventory_status,
            "all_available": all_available,
            "checked_items": len(item_codes),
            "found_items": len(items)
        })
        
    except Exception as e:
        logger.error(f"Error checking inventory: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/inventory/reserve")
async def reserve_items(request: MCPRequest):
    """Reserve items from inventory"""
    try:
        item_quantities = request.params.get("item_quantities", {})
        workorder_id = request.params.get("workorder_id", "")
        
        if not item_quantities:
            raise HTTPException(status_code=400, detail="No items to reserve")
        
        conn = get_sql_server_connection()
        cursor = conn.cursor()
        
        reserved_items = {}
        for item_id, quantity in item_quantities.items():
            # Check current stock
            cursor.execute("SELECT quantity FROM inventory WHERE item_id = ?", (item_id,))
            result = cursor.fetchone()
            
            if result is None:
                reserved_items[item_id] = {
                    "reserved": 0,
                    "success": False,
                    "message": "Item not found"
                }
            else:
                current_stock = result[0]
                if current_stock >= quantity:
                    # Reserve the items
                    cursor.execute(
                        "UPDATE inventory SET quantity = quantity - ? WHERE item_id = ?",
                        (quantity, item_id)
                    )
                    reserved_items[item_id] = {
                        "reserved": quantity,
                        "success": True,
                        "message": "Items reserved successfully"
                    }
                else:
                    reserved_items[item_id] = {
                        "reserved": 0,
                        "success": False,
                        "message": f"Insufficient stock. Available: {current_stock}, Required: {quantity}"
                    }
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return MCPResponse(result={
            "reserved_items": reserved_items,
            "workorder_id": workorder_id,
            "total_items_reserved": sum(item["reserved"] for item in reserved_items.values())
        })
        
    except Exception as e:
        logger.error(f"Error reserving items: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/inventory/restore")
async def restore_items(request: MCPRequest):
    """Restore previously reserved items to inventory"""
    try:
        item_quantities = request.params.get("item_quantities", {})
        workorder_id = request.params.get("workorder_id", "")
        
        if not item_quantities:
            raise HTTPException(status_code=400, detail="No items to restore")
        
        conn = get_sql_server_connection()
        cursor = conn.cursor()
        
        restored_items = {}
        for item_id, quantity in item_quantities.items():
            # Restore items to inventory
            cursor.execute(
                "UPDATE inventory SET quantity = quantity + ? WHERE item_id = ?",
                (quantity, item_id)
            )
            affected_rows = cursor.rowcount
            
            if affected_rows > 0:
                restored_items[item_id] = {
                    "restored": quantity,
                    "success": True,
                    "message": "Items restored successfully"
                }
            else:
                restored_items[item_id] = {
                    "restored": 0,
                    "success": False,
                    "message": "Item not found in inventory"
                }
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return MCPResponse(result={
            "restored_items": restored_items,
            "workorder_id": workorder_id,
            "total_items_restored": sum(item["restored"] for item in restored_items.values())
        })
        
    except Exception as e:
        logger.error(f"Error restoring items: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/inventory/list")
async def list_inventory(request: MCPRequest):
    """List all inventory items with optional filtering"""
    try:
        category_filter = request.params.get("category", "")
        min_quantity = request.params.get("min_quantity", 0)
        
        conn = get_sql_server_connection()
        cursor = conn.cursor()
        
        if category_filter:
            cursor.execute(
                "SELECT * FROM inventory WHERE category = ? AND quantity >= ? ORDER BY item_id",
                (category_filter, min_quantity)
            )
        else:
            cursor.execute(
                "SELECT * FROM inventory WHERE quantity >= ? ORDER BY item_id",
                (min_quantity,)
            )
        
        items = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        
        inventory_list = []
        for item in items:
            item_dict = dict(zip(columns, item))
            # Convert dates to ISO format
            for date_field in ['last_updated', 'created_date']:
                if date_field in item_dict and item_dict[date_field]:
                    item_dict[date_field] = item_dict[date_field].isoformat()
            inventory_list.append(item_dict)
        
        cursor.close()
        conn.close()
        
        return MCPResponse(result={
            "inventory_items": inventory_list,
            "total_items": len(inventory_list),
            "filters_applied": {
                "category": category_filter if category_filter else "all",
                "min_quantity": min_quantity
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing inventory: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/inventory/search")
async def search_inventory(request: MCPRequest):
    """Search inventory items by name or description"""
    try:
        search_term = request.params.get("search_term", "")
        if not search_term:
            raise HTTPException(status_code=400, detail="No search term provided")
        
        conn = get_sql_server_connection()
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        cursor.execute(
            "SELECT * FROM inventory WHERE item_id LIKE ? OR name LIKE ? OR description LIKE ? ORDER BY item_id",
            (search_pattern, search_pattern, search_pattern)
        )
        
        items = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        
        search_results = []
        for item in items:
            item_dict = dict(zip(columns, item))
            # Convert dates to ISO format
            for date_field in ['last_updated', 'created_date']:
                if date_field in item_dict and item_dict[date_field]:
                    item_dict[date_field] = item_dict[date_field].isoformat()
            search_results.append(item_dict)
        
        cursor.close()
        conn.close()
        
        return MCPResponse(result={
            "search_results": search_results,
            "search_term": search_term,
            "total_found": len(search_results)
        })
        
    except Exception as e:
        logger.error(f"Error searching inventory: {str(e)}")
        return MCPResponse(result={}, error=str(e))

if __name__ == "__main__":
    import uvicorn
    print("Starting Inventory MCP Server on http://localhost:8002")
    uvicorn.run(app, host="0.0.0.0", port=8002)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from config.settings import SQL_SERVER_CONNECTION_STRING
from models.data_models import InventoryItem, SystemHealthStatus, SystemHealth
import time

app = FastAPI(title="Inventory MCP Server")

class MCPRequest(BaseModel):
    method: str
    params: Dict[str, Any] = {}

class MCPResponse(BaseModel):
    result: Dict[str, Any]
    error: Optional[str] = None

# Database connection
engine = create_engine(SQL_SERVER_CONNECTION_STRING)

@app.get("/health")
async def health_check():
    start_time = time.time()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
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
        
        with engine.connect() as conn:
            placeholders = ",".join([f"'{code}'" for code in item_codes])
            query = text(f"SELECT * FROM inventory WHERE item_id IN ({placeholders})")
            result = conn.execute(query)
            items = result.fetchall()
        
        inventory_status = {}
        for item in items:
            item_id, name, desc, qty, min_stock, max_stock, location, updated = item
            required_qty = quantities.get(item_id, 1)
            
            inventory_status[item_id] = {
                "name": name,
                "description": desc,
                "available_quantity": qty,
                "required_quantity": required_qty,
                "sufficient": qty >= required_qty,
                "location": location,
                "last_updated": updated.isoformat() if updated else None
            }
        
        all_available = all(status["sufficient"] for status in inventory_status.values())
        
        return MCPResponse(result={
            "available_items": inventory_status,
            "all_available": all_available,
            "checked_items": len(item_codes),
            "found_items": len(items)
        })
        
    except Exception as e:
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/inventory/reserve")
async def reserve_items(request: MCPRequest):
    """Reserve items from inventory"""
    try:
        item_quantities = request.params.get("item_quantities", {})
        workorder_id = request.params.get("workorder_id", "")
        
        if not item_quantities:
            raise HTTPException(status_code=400, detail="No items to reserve")
        
        reserved_items = {}
        with engine.connect() as conn:
            for item_id, quantity in item_quantities.items():
                # Check current stock
                result = conn.execute(
                    text("SELECT quantity FROM inventory WHERE item_id = :item_id"),
                    {"item_id": item_id}
                )
                current_stock = result.scalar()
                
                if current_stock is None:
                    reserved_items[item_id] = {
                        "reserved": 0,
                        "success": False,
                        "message": "Item not found"
                    }
                elif current_stock >= quantity:
                    # Reserve the items
                    conn.execute(
                        text("UPDATE inventory SET quantity = quantity - :qty WHERE item_id = :item_id"),
                        {"qty": quantity, "item_id": item_id}
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
        
        all_reserved = all(item["success"] for item in reserved_items.values())
        
        return MCPResponse(result={
            "workorder_id": workorder_id,
            "reserved_items": reserved_items,
            "all_reserved": all_reserved,
            "total_items": len(item_quantities)
        })
        
    except Exception as e:
        return MCPResponse(result={}, error=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

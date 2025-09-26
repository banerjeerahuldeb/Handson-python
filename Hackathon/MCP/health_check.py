import asyncio
import aiohttp
import time
from typing import List, Dict, Any
from models.data_models import SystemHealthStatus, SystemHealth
from config.settings import DatabaseConfig

class HealthChecker:
    def __init__(self):
        self.systems = {
            "inventory": "http://localhost:8002/health",
            "workorders": "http://localhost:8003/health", 
            "permits": "http://localhost:8001/api/health",
            "hr": "http://localhost:8004/health"
        }
    
    async def check_system_health(self, system_name: str, endpoint: str) -> SystemHealthStatus:
        """Check health of a single system"""
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, timeout=10) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        return SystemHealthStatus(
                            system_name=system_name,
                            status=SystemHealth.HEALTHY,
                            response_time=response_time,
                            details=data
                        )
                    else:
                        return SystemHealthStatus(
                            system_name=system_name,
                            status=SystemHealth.DEGRADED,
                            response_time=response_time,
                            details={"http_status": response.status, "error": "Non-200 response"}
                        )
                        
        except asyncio.TimeoutError:
            return SystemHealthStatus(
                system_name=system_name,
                status=SystemHealth.DOWN,
                response_time=0,
                details={"error": "Request timeout"}
            )
        except Exception as e:
            return SystemHealthStatus(
                system_name=system_name,
                status=SystemHealth.DOWN,
                response_time=0,
                details={"error": str(e)}
            )
    
    async def check_all_systems(self) -> Dict[str, SystemHealthStatus]:
        """Check health of all systems concurrently"""
        tasks = []
        for system_name, endpoint in self.systems.items():
            task = self.check_system_health(system_name, endpoint)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        health_status = {}
        for result in results:
            health_status[result.system_name] = result
        
        return health_status
    
    def get_overall_status(self, health_status: Dict[str, SystemHealthStatus]) -> SystemHealth:
        """Get overall system status"""
        statuses = [status.status for status in health_status.values()]
        
        if SystemHealth.DOWN in statuses:
            return SystemHealth.DOWN
        elif SystemHealth.DEGRADED in statuses:
            return SystemHealth.DEGRADED
        else:
            return SystemHealth.HEALTHY

# FastAPI endpoint for health checks
from fastapi import APIRouter

health_router = APIRouter()
checker = HealthChecker()

@health_router.get("/health")
async def health_overview():
    """Get health status of all systems"""
    health_status = await checker.check_all_systems()
    overall_status = checker.get_overall_status(health_status)
    
    return {
        "overall_status": overall_status.value,
        "systems": {name: status.dict() for name, status in health_status.items()},
        "timestamp": time.time()
    }

@health_router.get("/health/{system_name}")
async def health_system(system_name: str):
    """Get health status of a specific system"""
    if system_name not in checker.systems:
        return {"error": f"System {system_name} not found"}
    
    health_status = await checker.check_system_health(system_name, checker.systems[system_name])
    return health_status.dict()

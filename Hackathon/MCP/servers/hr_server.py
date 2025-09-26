from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd
import time
import logging

app = FastAPI(title="HR MCP Server")

class MCPRequest(BaseModel):
    method: str
    params: Dict[str, Any] = {}

class MCPResponse(BaseModel):
    result: Dict[str, Any]
    error: Optional[str] = None

class Employee(BaseModel):
    employee_id: str
    name: str
    department: str
    skills: List[str]
    current_workload: int
    available: bool

# Setup logging
logger = logging.getLogger(__name__)

class HRService:
    def __init__(self, excel_file_path: str = "hr_data.xlsx"):
        self.excel_file_path = excel_file_path
        self._load_hr_data()

    def _load_hr_data(self):
        """Load HR data from Excel file"""
        try:
            self.hr_df = pd.read_excel(self.excel_file_path)
            logger.info(f"Loaded HR data from {self.excel_file_path}")
        except FileNotFoundError:
            # Create sample data if file doesn't exist
            logger.info("HR data file not found, creating sample data")
            sample_data = {
                'employee_id': ['EMP001', 'EMP002', 'EMP003', 'EMP004', 'EMP005'],
                'name': ['John Smith', 'Maria Garcia', 'David Lee', 'Sarah Chen', 'Mike Johnson'],
                'department': ['Maintenance', 'Maintenance', 'Electrical', 'Mechanical', 'Plumbing'],
                'skills': [
                    'pump repair,mechanical,welding',
                    'electrical,welding,plumbing', 
                    'electrical,control systems,instrumentation',
                    'mechanical,hydraulics,pneumatics',
                    'plumbing,pipe fitting,welding'
                ],
                'current_workload': [2, 1, 0, 3, 1],
                'available': [True, True, True, False, True]
            }
            self.hr_df = pd.DataFrame(sample_data)
            # Save sample data
            self.hr_df.to_excel(self.excel_file_path, index=False)
            logger.info("Sample HR data created and saved")

    def get_available_employees(self, required_skills: List[str] = None, 
                               department: str = None, max_workload: int = 3) -> Dict[str, Any]:
        """Find available employees matching criteria"""
        try:
            filtered_df = self.hr_df[
                (self.hr_df['available'] == True) & 
                (self.hr_df['current_workload'] <= max_workload)
            ]
            
            if department:
                filtered_df = filtered_df[filtered_df['department'] == department]
            
            if required_skills:
                def has_skills(skills_str, req_skills):
                    skills = [s.strip().lower() for s in skills_str.split(',')]
                    return all(skill.lower() in skills for skill in req_skills)
                
                filtered_df = filtered_df[
                    filtered_df['skills'].apply(lambda x: has_skills(x, required_skills))
                ]
            
            employees = []
            for _, row in filtered_df.iterrows():
                employee = Employee(
                    employee_id=row['employee_id'],
                    name=row['name'],
                    department=row['department'],
                    skills=[s.strip() for s in row['skills'].split(',')],
                    current_workload=row['current_workload'],
                    available=row['available']
                )
                employees.append(employee.dict())
            
            return {
                "available_employees": employees,
                "count": len(employees),
                "criteria": {
                    "required_skills": required_skills,
                    "department": department,
                    "max_workload": max_workload
                }
            }
        except Exception as e:
            logger.error(f"Error getting available employees: {str(e)}")
            raise

    def assign_employee(self, employee_id: str, workorder_id: str) -> Dict[str, Any]:
        """Assign employee to work order"""
        try:
            if employee_id in self.hr_df['employee_id'].values:
                # Update workload in DataFrame
                idx = self.hr_df[self.hr_df['employee_id'] == employee_id].index[0]
                self.hr_df.at[idx, 'current_workload'] += 1
                
                # Save updated data
                self.hr_df.to_excel(self.excel_file_path, index=False)
                
                return {
                    "success": True,
                    "employee_id": employee_id,
                    "workorder_id": workorder_id,
                    "message": f"Employee {employee_id} assigned to work order {workorder_id}",
                    "new_workload": int(self.hr_df.at[idx, 'current_workload'])
                }
            else:
                return {
                    "success": False,
                    "message": f"Employee with ID {employee_id} not found"
                }
        except Exception as e:
            logger.error(f"Error assigning employee: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }

    def release_employee(self, employee_id: str, workorder_id: str) -> Dict[str, Any]:
        """Release employee from work order (reduce workload)"""
        try:
            if employee_id in self.hr_df['employee_id'].values:
                idx = self.hr_df[self.hr_df['employee_id'] == employee_id].index[0]
                current_workload = self.hr_df.at[idx, 'current_workload']
                
                if current_workload > 0:
                    self.hr_df.at[idx, 'current_workload'] -= 1
                
                # Save updated data
                self.hr_df.to_excel(self.excel_file_path, index=False)
                
                return {
                    "success": True,
                    "employee_id": employee_id,
                    "workorder_id": workorder_id,
                    "message": f"Employee {employee_id} released from work order {workorder_id}",
                    "new_workload": int(self.hr_df.at[idx, 'current_workload'])
                }
            else:
                return {
                    "success": False,
                    "message": f"Employee with ID {employee_id} not found"
                }
        except Exception as e:
            logger.error(f"Error releasing employee: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }

    def get_employee_details(self, employee_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific employee"""
        try:
            if employee_id in self.hr_df['employee_id'].values:
                row = self.hr_df[self.hr_df['employee_id'] == employee_id].iloc[0]
                
                employee = Employee(
                    employee_id=row['employee_id'],
                    name=row['name'],
                    department=row['department'],
                    skills=[s.strip() for s in row['skills'].split(',')],
                    current_workload=row['current_workload'],
                    available=row['available']
                )
                
                return {
                    "employee": employee.dict(),
                    "success": True
                }
            else:
                return {
                    "success": False,
                    "message": f"Employee with ID {employee_id} not found"
                }
        except Exception as e:
            logger.error(f"Error getting employee details: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }

    def get_all_employees(self) -> Dict[str, Any]:
        """Get all employees"""
        try:
            employees = []
            for _, row in self.hr_df.iterrows():
                employee = Employee(
                    employee_id=row['employee_id'],
                    name=row['name'],
                    department=row['department'],
                    skills=[s.strip() for s in row['skills'].split(',')],
                    current_workload=row['current_workload'],
                    available=row['available']
                )
                employees.append(employee.dict())
            
            return {
                "employees": employees,
                "total_count": len(employees),
                "available_count": len([e for e in employees if e['available']]),
                "departments": list(self.hr_df['department'].unique())
            }
        except Exception as e:
            logger.error(f"Error getting all employees: {str(e)}")
            raise

# Initialize HR service
hr_service = HRService()

@app.get("/health")
async def health_check():
    start_time = time.time()
    try:
        # Test by loading data
        hr_service._load_hr_data()
        response_time = (time.time() - start_time) * 1000
        
        return {
            "system_name": "hr-mcp-server",
            "status": "healthy",
            "response_time": response_time,
            "details": {
                "total_employees": len(hr_service.hr_df),
                "available_employees": len(hr_service.hr_df[hr_service.hr_df['available'] == True]),
                "data_file": hr_service.excel_file_path
            }
        }
    except Exception as e:
        return {
            "system_name": "hr-mcp-server",
            "status": "down",
            "response_time": 0,
            "details": {"error": str(e)}
        }

@app.post("/mcp/hr/available_employees")
async def get_available_employees(request: MCPRequest):
    """Get available employees with specific skills"""
    try:
        required_skills = request.params.get("required_skills", [])
        department = request.params.get("department")
        max_workload = request.params.get("max_workload", 3)
        
        result = hr_service.get_available_employees(required_skills, department, max_workload)
        return MCPResponse(result=result)
        
    except Exception as e:
        logger.error(f"Error in get_available_employees: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/hr/assign_employee")
async def assign_employee(request: MCPRequest):
    """Assign employee to work order"""
    try:
        employee_id = request.params.get("employee_id")
        workorder_id = request.params.get("workorder_id")
        
        if not employee_id or not workorder_id:
            raise HTTPException(status_code=400, detail="Employee ID and Workorder ID are required")
        
        result = hr_service.assign_employee(employee_id, workorder_id)
        return MCPResponse(result=result)
        
    except Exception as e:
        logger.error(f"Error in assign_employee: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/hr/release_employee")
async def release_employee(request: MCPRequest):
    """Release employee from work order"""
    try:
        employee_id = request.params.get("employee_id")
        workorder_id = request.params.get("workorder_id")
        
        if not employee_id or not workorder_id:
            raise HTTPException(status_code=400, detail="Employee ID and Workorder ID are required")
        
        result = hr_service.release_employee(employee_id, workorder_id)
        return MCPResponse(result=result)
        
    except Exception as e:
        logger.error(f"Error in release_employee: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/hr/employee_details")
async def get_employee_details(request: MCPRequest):
    """Get detailed information for a specific employee"""
    try:
        employee_id = request.params.get("employee_id")
        
        if not employee_id:
            raise HTTPException(status_code=400, detail="Employee ID is required")
        
        result = hr_service.get_employee_details(employee_id)
        return MCPResponse(result=result)
        
    except Exception as e:
        logger.error(f"Error in get_employee_details: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/hr/all_employees")
async def get_all_employees(request: MCPRequest):
    """Get all employees"""
    try:
        result = hr_service.get_all_employees()
        return MCPResponse(result=result)
        
    except Exception as e:
        logger.error(f"Error in get_all_employees: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/hr/departments")
async def get_departments(request: MCPRequest):
    """Get list of all departments"""
    try:
        departments = list(hr_service.hr_df['department'].unique())
        return MCPResponse(result={
            "departments": departments,
            "count": len(departments)
        })
        
    except Exception as e:
        logger.error(f"Error in get_departments: {str(e)}")
        return MCPResponse(result={}, error=str(e))

@app.post("/mcp/hr/skills")
async def get_skills(request: MCPRequest):
    """Get list of all unique skills across employees"""
    try:
        all_skills = []
        for skills_str in hr_service.hr_df['skills']:
            all_skills.extend([s.strip() for s in skills_str.split(',')])
        
        unique_skills = list(set(all_skills))
        return MCPResponse(result={
            "skills": sorted(unique_skills),
            "count": len(unique_skills)
        })
        
    except Exception as e:
        logger.error(f"Error in get_skills: {str(e)}")
        return MCPResponse(result={}, error=str(e))

if __name__ == "__main__":
    import uvicorn
    print("Starting HR MCP Server on http://localhost:8004")
    uvicorn.run(app, host="0.0.0.0", port=8004)

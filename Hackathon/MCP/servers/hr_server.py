import pandas as pd
from mcp import MCPServer, Tool
from models.data_models import Employee
from typing import List, Dict, Any

class HRMCPServer:
    def __init__(self, excel_file_path: str = "hr_data.xlsx"):
        self.excel_file_path = excel_file_path
        self._load_hr_data()
        self.server = MCPServer("hr-server")
        self._register_tools()

    def _load_hr_data(self):
        """Load HR data from Excel file"""
        try:
            self.hr_df = pd.read_excel(self.excel_file_path)
        except FileNotFoundError:
            # Create sample data if file doesn't exist
            sample_data = {
                'employee_id': ['EMP001', 'EMP002', 'EMP003', 'EMP004'],
                'name': ['John Smith', 'Maria Garcia', 'David Lee', 'Sarah Chen'],
                'department': ['Maintenance', 'Maintenance', 'Electrical', 'Mechanical'],
                'skills': [
                    'pump repair,mechanical',
                    'electrical,welding', 
                    'electrical,control systems',
                    'mechanical,hydraulics'
                ],
                'current_workload': [2, 1, 0, 3],
                'available': [True, True, True, False]
            }
            self.hr_df = pd.DataFrame(sample_data)

    def _register_tools(self):
        self.server.register_tool(
            Tool(
                name="get_available_employees",
                description="Get available employees with specific skills",
                input_schema={
                    "type": "object",
                    "properties": {
                        "required_skills": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of required skills"
                        },
                        "department": {"type": "string"},
                        "max_workload": {"type": "integer", "default": 3}
                    }
                },
                handler=self.get_available_employees
            )
        )
        
        self.server.register_tool(
            Tool(
                name="assign_employee",
                description="Assign employee to work order",
                input_schema={
                    "type": "object",
                    "properties": {
                        "employee_id": {"type": "string"},
                        "workorder_id": {"type": "string"}
                    },
                    "required": ["employee_id", "workorder_id"]
                },
                handler=self.assign_employee
            )
        )

    def get_available_employees(self, required_skills: List[str] = None, 
                               department: str = None, max_workload: int = 3) -> Dict[str, Any]:
        """Find available employees matching criteria"""
        filtered_df = self.hr_df[
            (self.hr_df['available'] == True) & 
            (self.hr_df['current_workload'] <= max_workload)
        ]
        
        if department:
            filtered_df = filtered_df[filtered_df['department'] == department]
        
        if required_skills:
            def has_skills(skills_str, req_skills):
                skills = [s.strip() for s in skills_str.split(',')]
                return all(skill in skills for skill in req_skills)
            
            filtered_df = filtered_df[
                filtered_df['skills'].apply(lambda x: has_skills(x, required_skills))
            ]
        
        employees = []
        for _, row in filtered_df.iterrows():
            employee = Employee(
                employee_id=row['employee_id'],
                name=row['name'],
                department=row['department'],
                skills=row['skills'].split(','),
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

    def assign_employee(self, employee_id: str, workorder_id: str) -> Dict[str, Any]:
        """Assign employee to work order"""
        if employee_id in self.hr_df['employee_id'].values:
            # Update workload in DataFrame
            idx = self.hr_df[self.hr_df['employee_id'] == employee_id].index[0]
            self.hr_df.at[idx, 'current_workload'] += 1
            
            return {
                "success": True,
                "employee_id": employee_id,
                "workorder_id": workorder_id,
                "message": f"Employee {employee_id} assigned to work order {workorder_id}"
            }
        else:
            return {
                "success": False,
                "message": f"Employee {employee_id} not found"
            }

    async def run_server(self):
        await self.server.run()

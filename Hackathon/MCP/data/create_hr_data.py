import pandas as pd
import os
from datetime import datetime

def create_hr_excel_file():
    """Create HR data Excel file with sample data"""
    
    hr_data = {
        'employee_id': ['EMP001', 'EMP002', 'EMP003', 'EMP004', 'EMP005', 'EMP006', 'EMP007'],
        'name': ['John Smith', 'Maria Garcia', 'David Lee', 'Sarah Chen', 'Robert Brown', 'Lisa Wilson', 'Michael Johnson'],
        'department': ['Maintenance', 'Maintenance', 'Electrical', 'Mechanical', 'Maintenance', 'Electrical', 'Safety'],
        'position': ['Technician', 'Senior Technician', 'Electrician', 'Mechanic', 'Supervisor', 'Senior Electrician', 'Safety Officer'],
        'skills': [
            'pump repair,mechanical,hydraulics',
            'electrical,welding,control systems', 
            'electrical,control systems,instrumentation',
            'mechanical,hydraulics,pneumatics',
            'supervision,planning,safety',
            'electrical,high voltage,transformers',
            'safety,compliance,training'
        ],
        'certifications': [
            'Mechanical Technician, Safety Level 1',
            'Electrical License, Welding Certified',
            'Electrical Engineer, Instrumentation',
            'Mechanical Engineer, Hydraulics',
            'Supervisor Certified, Safety Level 3',
            'High Voltage Certified, Electrical Master',
            'Safety Officer, First Aid, CPR'
        ],
        'current_workload': [2, 1, 0, 3, 1, 2, 0],
        'max_workload': [5, 5, 5, 5, 5, 5, 5],
        'available': [True, True, True, False, True, True, True],
        'email': [
            'john.smith@company.com',
            'maria.garcia@company.com', 
            'david.lee@company.com',
            'sarah.chen@company.com',
            'robert.brown@company.com',
            'lisa.wilson@company.com',
            'michael.johnson@company.com'
        ],
        'phone': ['555-0101', '555-0102', '555-0103', '555-0104', '555-0105', '555-0106', '555-0107'],
        'hire_date': [
            '2020-03-15', '2019-07-22', '2021-01-10', '2018-11-05', '2017-05-30', '2019-09-12', '2022-02-28'
        ],
        'shift': ['Day', 'Night', 'Day', 'Day', 'Day', 'Night', 'Day']
    }
    
    df = pd.DataFrame(hr_data)
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Save to Excel
    file_path = 'data/hr_data.xlsx'
    df.to_excel(file_path, index=False, sheet_name='Employees')
    
    print(f"HR data Excel file created successfully at: {file_path}")
    print(f"Total employees: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    return file_path

def create_skills_matrix():
    """Create a skills matrix sheet in the HR Excel file"""
    
    skills_matrix = {
        'skill_category': ['Mechanical', 'Electrical', 'Safety', 'Hydraulics', 'Pneumatics', 'Welding', 'Control Systems'],
        'required_certification': ['Mechanical Technician', 'Electrical License', 'Safety Level 2', 'Hydraulics Certified', 'Pneumatics Certified', 'Welding Certified', 'Control Systems'],
        'emp001': [True, False, True, True, False, False, False],
        'emp002': [False, True, True, False, False, True, True],
        'emp003': [False, True, True, False, False, False, True],
        'emp004': [True, False, True, True, True, False, False],
        'emp005': [True, True, True, True, True, True, True],
        'emp006': [False, True, True, False, False, False, True],
        'emp007': [False, False, True, False, False, False, False]
    }
    
    df_skills = pd.DataFrame(skills_matrix)
    
    # Append to existing Excel file
    with pd.ExcelWriter('data/hr_data.xlsx', mode='a', engine='openpyxl') as writer:
        df_skills.to_excel(writer, index=False, sheet_name='Skills_Matrix')
    
    print("Skills matrix added to HR Excel file")

if __name__ == "__main__":
    create_hr_excel_file()
    create_skills_matrix()

import pandas as pd
from database.sql_server_setup import SQLServerSetup
from database.oracle_setup import OracleSetup
import os
import logging

logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def __init__(self):
        self.sql_setup = SQLServerSetup()
        self.oracle_setup = OracleSetup()
    
    def init_sql_server(self):
        """Initialize SQL Server database"""
        logger.info("Initializing SQL Server database...")
        success, message = self.sql_setup.test_connection()
        
        if success:
            schema_created = self.sql_setup.create_inventory_schema()
            if schema_created:
                logger.info("SQL Server initialization completed successfully")
            else:
                logger.error("SQL Server schema creation failed")
        else:
            logger.error(f"SQL Server connection failed: {message}")
        
        return success
    
    def init_oracle(self):
        """Initialize Oracle database"""
        logger.info("Initializing Oracle database...")
        success, message = self.oracle_setup.test_connection()
        
        if success:
            schema_created = self.oracle_setup.create_workorders_schema()
            if schema_created:
                logger.info("Oracle initialization completed successfully")
            else:
                logger.error("Oracle schema creation failed")
        else:
            logger.error(f"Oracle connection failed: {message}")
        
        return success
    
    def create_hr_excel(self):
        """Create HR data Excel file"""
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
        os.makedirs('data', exist_ok=True)
        df.to_excel('data/hr_data.xlsx', index=False)
        logger.info("HR Excel file created successfully")
        return True

def initialize_all_databases():
    """Initialize all databases and data files"""
    logger.info("Starting database initialization...")
    
    initializer = DatabaseInitializer()
    
    # Initialize SQL Server
    sql_success = initializer.init_sql_server()
    
    # Initialize Oracle
    oracle_success = initializer.init_oracle()
    
    # Create HR Excel file
    hr_success = initializer.create_hr_excel()
    
    # Summary
    logger.info("Database initialization summary:")
    logger.info(f"SQL Server: {'SUCCESS' if sql_success else 'FAILED'}")
    logger.info(f"Oracle: {'SUCCESS' if oracle_success else 'FAILED'}")
    logger.info(f"HR Data: {'SUCCESS' if hr_success else 'FAILED'}")
    
    overall_success = sql_success and oracle_success and hr_success
    logger.info(f"Overall: {'SUCCESS' if overall_success else 'FAILED'}")
    
    return overall_success

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    success = initialize_all_databases()
    sys.exit(0 if success else 1)

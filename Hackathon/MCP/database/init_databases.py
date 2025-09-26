import pyodbc
import oracledb
import pandas as pd
from sqlalchemy import create_engine, text
from config.settings import SQL_SERVER_CONNECTION_STRING, ORACLE_CONNECTION_STRING
import os

class DatabaseInitializer:
    def __init__(self):
        self.sql_engine = create_engine(SQL_SERVER_CONNECTION_STRING)
        self.oracle_engine = create_engine(ORACLE_CONNECTION_STRING)
    
    def init_sql_server(self):
        """Initialize SQL Server database with tables and dummy data"""
        try:
            # Create Inventory table
            with self.sql_engine.connect() as conn:
                conn.execute(text("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='inventory' AND xtype='U')
                    CREATE TABLE inventory (
                        item_id NVARCHAR(50) PRIMARY KEY,
                        name NVARCHAR(100) NOT NULL,
                        description NVARCHAR(500),
                        quantity INT NOT NULL,
                        min_stock INT NOT NULL,
                        max_stock INT NOT NULL,
                        location NVARCHAR(100),
                        last_updated DATETIME DEFAULT GETDATE()
                    )
                """))
                
                # Insert dummy data
                dummy_data = [
                    ('pump-seal-001', 'Pump Seal Kit', 'Seal kit for centrifugal pumps', 15, 5, 50, 'Warehouse A'),
                    ('bearing-002', 'Ball Bearing', 'High precision ball bearing', 30, 10, 100, 'Warehouse B'),
                    ('gasket-003', 'Mechanical Gasket', 'High temperature gasket', 25, 8, 80, 'Warehouse A'),
                    ('valve-004', 'Control Valve', 'Pressure control valve', 8, 3, 30, 'Warehouse C'),
                    ('motor-005', 'Electric Motor', '1HP industrial motor', 5, 2, 20, 'Warehouse B'),
                    ('coupling-006', 'Shaft Coupling', 'Flexible shaft coupling', 12, 4, 40, 'Warehouse A')
                ]
                
                for item in dummy_data:
                    conn.execute(text("""
                        MERGE inventory AS target
                        USING (VALUES (:item_id, :name, :description, :quantity, :min_stock, :max_stock, :location)) 
                        AS source (item_id, name, description, quantity, min_stock, max_stock, location)
                        ON target.item_id = source.item_id
                        WHEN MATCHED THEN
                            UPDATE SET name = source.name, description = source.description, 
                                      quantity = source.quantity, min_stock = source.min_stock,
                                      max_stock = source.max_stock, location = source.location,
                                      last_updated = GETDATE()
                        WHEN NOT MATCHED THEN
                            INSERT (item_id, name, description, quantity, min_stock, max_stock, location)
                            VALUES (source.item_id, source.name, source.description, source.quantity, 
                                   source.min_stock, source.max_stock, source.location);
                    """), {
                        'item_id': item[0], 'name': item[1], 'description': item[2],
                        'quantity': item[3], 'min_stock': item[4], 'max_stock': item[5],
                        'location': item[6]
                    })
                
                conn.commit()
            print("SQL Server database initialized successfully")
            
        except Exception as e:
            print(f"Error initializing SQL Server: {e}")
    
    def init_oracle(self):
        """Initialize Oracle database with tables and dummy data"""
        try:
            with self.oracle_engine.connect() as conn:
                # Create WorkOrders table
                conn.execute(text("""
                    BEGIN
                        EXECUTE IMMEDIATE '
                            CREATE TABLE workorders (
                                workorder_id VARCHAR2(50) PRIMARY KEY,
                                equipment_id VARCHAR2(50) NOT NULL,
                                title VARCHAR2(200) NOT NULL,
                                description VARCHAR2(1000),
                                status VARCHAR2(20) DEFAULT ''draft'',
                                priority VARCHAR2(10) DEFAULT ''medium'',
                                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                assigned_to VARCHAR2(50),
                                required_parts CLOB,
                                permits_required CLOB,
                                estimated_hours NUMBER,
                                actual_hours NUMBER
                            )
                        ';
                    EXCEPTION
                        WHEN OTHERS THEN
                            IF SQLCODE != -955 THEN
                                RAISE;
                            END IF;
                    END;
                """))
                
                # Create sequence for workorder IDs
                conn.execute(text("""
                    BEGIN
                        EXECUTE IMMEDIATE 'CREATE SEQUENCE workorder_seq START WITH 1 INCREMENT BY 1';
                    EXCEPTION
                        WHEN OTHERS THEN
                            IF SQLCODE != -955 THEN
                                RAISE;
                            END IF;
                    END;
                """))
                
                # Insert dummy work orders
                dummy_workorders = [
                    ('WO-2024-001', 'pump-001', 'Pump Maintenance', 'Routine maintenance for pump-001', 
                     'completed', 'low', 'EMP001', '["pump-seal-001"]', '[]', 4.0, 3.5),
                    ('WO-2024-002', 'pump-002', 'Seal Replacement', 'Replace worn seals on pump-002', 
                     'in_progress', 'high', 'EMP002', '["pump-seal-001", "gasket-003"]', '["work-permit"]', 8.0, 2.0)
                ]
                
                for wo in dummy_workorders:
                    conn.execute(text("""
                        MERGE INTO workorders target
                        USING (SELECT :1 as workorder_id, :2 as equipment_id, :3 as title, 
                                      :4 as description, :5 as status, :6 as priority,
                                      :7 as assigned_to, :8 as required_parts, 
                                      :9 as permits_required, :10 as estimated_hours,
                                      :11 as actual_hours FROM dual) source
                        ON (target.workorder_id = source.workorder_id)
                        WHEN MATCHED THEN
                            UPDATE SET equipment_id = source.equipment_id, title = source.title,
                                      description = source.description, status = source.status,
                                      priority = source.priority, assigned_to = source.assigned_to,
                                      required_parts = source.required_parts, 
                                      permits_required = source.permits_required,
                                      estimated_hours = source.estimated_hours,
                                      actual_hours = source.actual_hours
                        WHEN NOT MATCHED THEN
                            INSERT (workorder_id, equipment_id, title, description, status, 
                                   priority, assigned_to, required_parts, permits_required,
                                   estimated_hours, actual_hours)
                            VALUES (source.workorder_id, source.equipment_id, source.title,
                                   source.description, source.status, source.priority,
                                   source.assigned_to, source.required_parts, 
                                   source.permits_required, source.estimated_hours,
                                   source.actual_hours)
                    """), wo)
                
                conn.commit()
            print("Oracle database initialized successfully")
            
        except Exception as e:
            print(f"Error initializing Oracle: {e}")
    
    def create_hr_excel(self):
        """Create HR data Excel file"""
        hr_data = {
            'employee_id': ['EMP001', 'EMP002', 'EMP003', 'EMP004', 'EMP005'],
            'name': ['John Smith', 'Maria Garcia', 'David Lee', 'Sarah Chen', 'Robert Brown'],
            'department': ['Maintenance', 'Maintenance', 'Electrical', 'Mechanical', 'Maintenance'],
            'position': ['Technician', 'Senior Technician', 'Electrician', 'Mechanic', 'Supervisor'],
            'skills': [
                'pump repair,mechanical,hydraulics',
                'electrical,welding,control systems', 
                'electrical,control systems,instrumentation',
                'mechanical,hydraulics,pneumatics',
                'supervision,planning,safety'
            ],
            'current_workload': [2, 1, 0, 3, 1],
            'max_workload': [5, 5, 5, 5, 5],
            'available': [True, True, True, False, True],
            'email': [
                'john.smith@company.com',
                'maria.garcia@company.com', 
                'david.lee@company.com',
                'sarah.chen@company.com',
                'robert.brown@company.com'
            ]
        }
        
        df = pd.DataFrame(hr_data)
        os.makedirs('data', exist_ok=True)
        df.to_excel('data/hr_data.xlsx', index=False)
        print("HR Excel file created successfully")

def initialize_all_databases():
    """Initialize all databases and data files"""
    initializer = DatabaseInitializer()
    initializer.init_sql_server()
    initializer.init_oracle()
    initializer.create_hr_excel()

if __name__ == "__main__":
    initialize_all_databases()

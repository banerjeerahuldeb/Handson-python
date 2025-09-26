#import pyodbc
#from config.settings import DatabaseConfig, SQL_SERVER_CONNECTION_STRING
#import logging

#logger = logging.getLogger(__name__)

import sys
import os
# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyodbc
from config.settings import DatabaseConfig, SQL_SERVER_CONNECTION_STRING
import logging

logger = logging.getLogger(__name__)

class SQLServerSetup:
    def __init__(self):
        # Connection string for direct pyodbc connection
        self.connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={DatabaseConfig.SQL_SERVER_HOST};"
            f"DATABASE={DatabaseConfig.SQL_SERVER_DB};"
            f"Trusted_Connection={DatabaseConfig.SQL_SERVER_TRUSTED_CONNECTION};"
        )
    
    def test_connection(self):
        """Test connection to SQL Server using Windows Authentication"""
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()
            conn.close()
            logger.info("SQL Server connection successful")
            return True, f"Connected to SQL Server: {version[0][:100]}..."  # Truncate long version string
        except Exception as e:
            logger.error(f"SQL Server connection failed: {str(e)}")
            return False, str(e)
    
    def create_inventory_schema(self):
        """Create inventory database schema"""
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            
            # Check if database exists, create if not
            cursor.execute(f"""
                IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = '{DatabaseConfig.SQL_SERVER_DB}')
                CREATE DATABASE [{DatabaseConfig.SQL_SERVER_DB}]
            """)
            
            # Use the database
            cursor.execute(f"USE [{DatabaseConfig.SQL_SERVER_DB}]")
            
            # Create inventory table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='inventory' AND xtype='U')
                CREATE TABLE inventory (
                    item_id NVARCHAR(50) PRIMARY KEY,
                    name NVARCHAR(100) NOT NULL,
                    description NVARCHAR(500),
                    quantity INT NOT NULL DEFAULT 0,
                    min_stock INT NOT NULL DEFAULT 0,
                    max_stock INT NOT NULL DEFAULT 100,
                    location NVARCHAR(100),
                    last_updated DATETIME DEFAULT GETDATE()
                )
            """)
            
            # Create inventory transactions table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='inventory_transactions' AND xtype='U')
                CREATE TABLE inventory_transactions (
                    transaction_id INT IDENTITY(1,1) PRIMARY KEY,
                    item_id NVARCHAR(50) NOT NULL,
                    transaction_type NVARCHAR(20) NOT NULL,
                    quantity INT NOT NULL,
                    workorder_id NVARCHAR(50),
                    transaction_date DATETIME DEFAULT GETDATE(),
                    FOREIGN KEY (item_id) REFERENCES inventory(item_id)
                )
            """)
            
            # Insert sample data
            sample_data = [
                ('pump-seal-001', 'Pump Seal Kit', 'Seal kit for centrifugal pumps', 15, 5, 50, 'Warehouse A'),
                ('bearing-002', 'Ball Bearing', 'High precision ball bearing', 30, 10, 100, 'Warehouse B'),
                ('gasket-003', 'Mechanical Gasket', 'High temperature gasket', 25, 8, 80, 'Warehouse A'),
                ('valve-004', 'Control Valve', 'Pressure control valve', 8, 3, 30, 'Warehouse C'),
                ('motor-005', 'Electric Motor', '1HP industrial motor', 5, 2, 20, 'Warehouse B'),
                ('coupling-006', 'Shaft Coupling', 'Flexible shaft coupling', 12, 4, 40, 'Warehouse A'),
                ('sensor-007', 'Pressure Sensor', 'Digital pressure sensor', 20, 5, 60, 'Warehouse C'),
                ('filter-008', 'Oil Filter', 'Industrial oil filter', 18, 6, 70, 'Warehouse B')
            ]
            
            for item in sample_data:
                cursor.execute("""
                    IF NOT EXISTS (SELECT 1 FROM inventory WHERE item_id = ?)
                    INSERT INTO inventory (item_id, name, description, quantity, min_stock, max_stock, location)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, item[0], *item)
            
            conn.commit()
            conn.close()
            logger.info("SQL Server inventory schema created successfully with sample data")
            return True
        except Exception as e:
            logger.error(f"Failed to create SQL Server schema: {str(e)}")
            return False

if __name__ == "__main__":
    setup = SQLServerSetup()
    success, message = setup.test_connection()
    print(f"SQL Server Connection Test: {success} - {message}")
    
    if success:
        schema_created = setup.create_inventory_schema()
        print(f"Schema creation: {'Success' if schema_created else 'Failed'}")

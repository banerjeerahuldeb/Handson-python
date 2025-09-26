import pyodbc
from config.settings import DatabaseConfig
import logging

logger = logging.getLogger(__name__)

class SQLServerSetup:
    def __init__(self):
        self.connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={DatabaseConfig.SQL_SERVER_HOST},{DatabaseConfig.SQL_SERVER_PORT};"
            f"DATABASE={DatabaseConfig.SQL_SERVER_DB};"
            f"UID={DatabaseConfig.SQL_SERVER_USER};"
            f"PWD={DatabaseConfig.SQL_SERVER_PASSWORD}"
        )
    
    def test_connection(self):
        """Test connection to SQL Server"""
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()
            conn.close()
            logger.info("SQL Server connection successful")
            return True, f"Connected to SQL Server: {version[0]}"
        except Exception as e:
            logger.error(f"SQL Server connection failed: {str(e)}")
            return False, str(e)
    
    def create_inventory_schema(self):
        """Create inventory database schema"""
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            
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
            
            conn.commit()
            conn.close()
            logger.info("SQL Server inventory schema created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create SQL Server schema: {str(e)}")
            return False

if __name__ == "__main__":
    setup = SQLServerSetup()
    success, message = setup.test_connection()
    print(f"Connection test: {success} - {message}")
    
    if success:
        setup.create_inventory_schema()

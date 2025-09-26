import sys
import os
import pyodbc
import socket
import logging
from datetime import datetime

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config.settings import DatabaseConfig
except ImportError:
    # Fallback if config module not available
    class DatabaseConfig:
        SQL_SERVER_HOST = "AVD116\\SQLEXPRESS"
        SQL_SERVER_DB = "InventoryDB"
        SQL_SERVER_TRUSTED_CONNECTION = "yes"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SQLServerSetup:
    def __init__(self):
        self.connection_strings = [
            # Try different connection methods
            f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=AVD116\\SQLEXPRESS;DATABASE={DatabaseConfig.SQL_SERVER_DB};Trusted_Connection=yes;TrustServerCertificate=yes;Connection Timeout=30;",
            f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=localhost\\SQLEXPRESS;DATABASE={DatabaseConfig.SQL_SERVER_DB};Trusted_Connection=yes;TrustServerCertificate=yes;Connection Timeout=30;",
            f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=.\\SQLEXPRESS;DATABASE={DatabaseConfig.SQL_SERVER_DB};Trusted_Connection=yes;TrustServerCertificate=yes;Connection Timeout=30;",
            f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=127.0.0.1\\SQLEXPRESS;DATABASE={DatabaseConfig.SQL_SERVER_DB};Trusted_Connection=yes;TrustServerCertificate=yes;Connection Timeout=30;",
            f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=AVD116,1433;DATABASE={DatabaseConfig.SQL_SERVER_DB};Trusted_Connection=yes;TrustServerCertificate=yes;Connection Timeout=30;"
        ]
    
    def test_network_connectivity(self):
        """Test basic network connectivity to SQL Server"""
        print("Testing network connectivity...")
        
        # Test server resolution
        try:
            ip = socket.gethostbyname("AVD116")
            print(f"✅ Server AVD116 resolved to: {ip}")
        except:
            print("❌ Cannot resolve AVD116, trying localhost...")
            try:
                ip = socket.gethostbyname("localhost")
                print(f"✅ localhost resolved to: {ip}")
            except:
                print("❌ Cannot resolve localhost")
                return False
        
        # Test port 1433
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(("localhost", 1433))
            sock.close()
            if result == 0:
                print("✅ Port 1433 is open")
                return True
            else:
                print("❌ Port 1433 is closed")
                return False
        except Exception as e:
            print(f"❌ Port test failed: {e}")
            return False
    
    def test_connection(self):
        """Test connection to SQL Server using multiple methods"""
        print("Testing SQL Server connections...")
        
        if not self.test_network_connectivity():
            print("Network connectivity failed. Check SQL Server service and firewall.")
            return False, "Network connectivity failed"
        
        for i, conn_str in enumerate(self.connection_strings):
            print(f"\nAttempt {i+1}: {conn_str.split(';')[1]}")  # Show SERVER part
            
            try:
                start_time = datetime.now()
                conn = pyodbc.connect(conn_str, timeout=10)
                cursor = conn.cursor()
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()
                conn.close()
                elapsed = (datetime.now() - start_time).total_seconds()
                
                print(f"✅ SUCCESS! Connection time: {elapsed:.2f}s")
                print(f"SQL Server: {version[0][:100]}...")
                
                # Save working connection string
                self.working_connection_string = conn_str
                return True, f"Connected using: {conn_str.split(';')[1]}"
                
            except pyodbc.Error as e:
                print(f"❌ Failed: {e}")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        return False, "All connection attempts failed"
    
    def create_inventory_schema(self):
        """Create inventory database schema using working connection"""
        if not hasattr(self, 'working_connection_string'):
            print("No working connection string available")
            return False
            
        try:
            conn = pyodbc.connect(self.working_connection_string)
            cursor = conn.cursor()
            
            # Your schema creation code here...
            # (Keep the existing schema creation code)
            
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
    print(f"\n{'='*50}")
    print(f"Final Result: {success} - {message}")
    
    if success:
        print("Creating database schema...")
        schema_created = setup.create_inventory_schema()
        print(f"Schema creation: {'Success' if schema_created else 'Failed'}")

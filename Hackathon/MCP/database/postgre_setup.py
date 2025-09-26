import sys
import os
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DatabaseConfig

logger = logging.getLogger(__name__)

class PostgreSQLSetup:
    def __init__(self):
        self.connection_params = {
            "host": DatabaseConfig.POSTGRES_HOST,
            "port": DatabaseConfig.POSTGRES_PORT,
            "user": DatabaseConfig.POSTGRES_USER,
            "password": DatabaseConfig.POSTGRES_PASSWORD,
        }
        self.db_name = DatabaseConfig.POSTGRES_DB
    
    def test_connection(self):
        """Test connection to PostgreSQL server"""
        try:
            print("Testing PostgreSQL connection...")
            conn = psycopg2.connect(**self.connection_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            conn.close()
            logger.info("PostgreSQL connection successful")
            return True, f"Connected to PostgreSQL: {version[0]}"
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {str(e)}")
            return False, str(e)
    
    def create_database(self):
        """Create the workorders database if it doesn't exist"""
        try:
            conn = psycopg2.connect(**self.connection_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (self.db_name,))
            exists = cursor.fetchone()
            
            if not exists:
                cursor.execute(f"CREATE DATABASE {self.db_name};")
                logger.info(f"Database {self.db_name} created successfully")
            else:
                logger.info(f"Database {self.db_name} already exists")
            
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to create database: {str(e)}")
            return False
    
    def create_workorders_schema(self):
        """Create workorders schema in the database"""
        try:
            # Connect to the specific database
            conn_params = self.connection_params.copy()
            conn_params["database"] = self.db_name
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            # Create workorders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workorders (
                    workorder_id SERIAL PRIMARY KEY,
                    equipment_id VARCHAR(50) NOT NULL,
                    description TEXT,
                    priority VARCHAR(20) CHECK (priority IN ('low', 'medium', 'high', 'critical')),
                    status VARCHAR(20) CHECK (status IN ('open', 'in progress', 'completed', 'cancelled')),
                    assigned_to VARCHAR(100),
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_date TIMESTAMP,
                    estimated_hours NUMERIC(5,2),
                    actual_hours NUMERIC(5,2)
                )
            """)
            
            # Create workorder_tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workorder_tasks (
                    task_id SERIAL PRIMARY KEY,
                    workorder_id INTEGER REFERENCES workorders(workorder_id),
                    task_description TEXT NOT NULL,
                    status VARCHAR(20) CHECK (status IN ('pending', 'in progress', 'completed')),
                    sequence INTEGER
                )
            """)
            
            # Insert sample workorders
            sample_workorders = [
                ('pump-001', 'Replace seal on centrifugal pump', 'high', 'open', 'John Smith', 4.0),
                ('compressor-002', 'Monthly maintenance on air compressor', 'medium', 'in progress', 'Mike Johnson', 2.5),
                ('generator-003', 'Annual inspection and testing', 'critical', 'open', 'Sarah Wilson', 8.0),
            ]
            
            for wo in sample_workorders:
                cursor.execute("""
                    INSERT INTO workorders (equipment_id, description, priority, status, assigned_to, estimated_hours)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, wo)
            
            # Insert sample tasks for the first workorder
            sample_tasks = [
                (1, 'Shutdown and isolate pump', 'pending', 1),
                (1, 'Remove old seal', 'pending', 2),
                (1, 'Install new seal', 'pending', 3),
                (1, 'Test run and check for leaks', 'pending', 4),
            ]
            
            for task in sample_tasks:
                cursor.execute("""
                    INSERT INTO workorder_tasks (workorder_id, task_description, status, sequence)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, task)
            
            conn.commit()
            conn.close()
            logger.info("PostgreSQL workorders schema created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create workorders schema: {str(e)}")
            return False

if __name__ == "__main__":
    setup = PostgreSQLSetup()
    success, message = setup.test_connection()
    print(f"PostgreSQL Connection Test: {success} - {message}")
    
    if success:
        db_created = setup.create_database()
        if db_created:
            schema_created = setup.create_workorders_schema()
            print(f"Schema creation: {'Success' if schema_created else 'Failed'}")

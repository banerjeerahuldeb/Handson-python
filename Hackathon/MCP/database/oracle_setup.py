import oracledb
from config.settings import DatabaseConfig
import logging

logger = logging.getLogger(__name__)

class OracleSetup:
    def __init__(self):
        self.connection_string = f"{DatabaseConfig.ORACLE_USER}/{DatabaseConfig.ORACLE_PASSWORD}@{DatabaseConfig.ORACLE_HOST}:{DatabaseConfig.ORACLE_PORT}/{DatabaseConfig.ORACLE_SERVICE}"
    
    def test_connection(self):
        """Test connection to Oracle Database"""
        try:
            connection = oracledb.connect(self.connection_string)
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM v$version")
            version = cursor.fetchone()
            connection.close()
            logger.info("Oracle Database connection successful")
            return True, f"Connected to Oracle: {version[0]}"
        except Exception as e:
            logger.error(f"Oracle Database connection failed: {str(e)}")
            return False, str(e)
    
    def create_workorders_schema(self):
        """Create workorders database schema"""
        try:
            connection = oracledb.connect(self.connection_string)
            cursor = connection.cursor()
            
            # Create workorders table
            cursor.execute("""
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
                            actual_hours NUMBER,
                            completed_date TIMESTAMP
                        )
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE != -955 THEN
                            RAISE;
                        END IF;
                END;
            """)
            
            # Create workorder_audit table
            cursor.execute("""
                BEGIN
                    EXECUTE IMMEDIATE '
                        CREATE TABLE workorder_audit (
                            audit_id NUMBER PRIMARY KEY,
                            workorder_id VARCHAR2(50) NOT NULL,
                            action VARCHAR2(20) NOT NULL,
                            action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            performed_by VARCHAR2(50),
                            details CLOB
                        )
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE != -955 THEN
                            RAISE;
                        END IF;
                END;
            """)
            
            # Create sequence for audit IDs
            cursor.execute("""
                BEGIN
                    EXECUTE IMMEDIATE 'CREATE SEQUENCE workorder_audit_seq START WITH 1 INCREMENT BY 1';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE != -955 THEN
                            RAISE;
                        END IF;
                END;
            """)
            
            # Create sequence for workorder IDs
            cursor.execute("""
                BEGIN
                    EXECUTE IMMEDIATE 'CREATE SEQUENCE workorder_seq START WITH 1 INCREMENT BY 1';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE != -955 THEN
                            RAISE;
                        END IF;
                END;
            """)
            
            connection.commit()
            connection.close()
            logger.info("Oracle workorders schema created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create Oracle schema: {str(e)}")
            return False

if __name__ == "__main__":
    setup = OracleSetup()
    success, message = setup.test_connection()
    print(f"Connection test: {success} - {message}")
    
    if success:
        setup.create_workorders_schema()

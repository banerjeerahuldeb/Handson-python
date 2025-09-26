import oracledb
from config.settings import DatabaseConfig, ORACLE_CONNECTION_STRING_ORACLEDB
import logging
import json

logger = logging.getLogger(__name__)

class OracleSetup:
    def __init__(self):
        self.connection_config = ORACLE_CONNECTION_STRING_ORACLEDB
        
        # Configure oracledb to use thick mode for advanced features
        oracledb.init_oracle_client()
    
    def test_connection(self):
        """Test connection to Oracle Cloud Database"""
        try:
            connection = oracledb.connect(**self.connection_config)
            cursor = connection.cursor()
            cursor.execute("SELECT BANNER FROM v$version WHERE ROWNUM = 1")
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
            connection = oracledb.connect(**self.connection_config)
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
                            completed_date TIMESTAMP,
                            created_by VARCHAR2(50) DEFAULT ''system''
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
                    EXECUTE IMMEDIATE 'CREATE SEQUENCE workorder_audit_seq START WITH 1 INCREMENT BY 1 NOCACHE NOCYCLE';
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
                    EXECUTE IMMEDIATE 'CREATE SEQUENCE workorder_seq START WITH 1000 INCREMENT BY 1 NOCACHE NOCYCLE';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE != -955 THEN
                            RAISE;
                        END IF;
                END;
            """)
            
            # Insert sample work orders
            sample_workorders = [
                ('WO-2024-1001', 'pump-001', 'Routine Pump Maintenance', 
                 'Scheduled maintenance for pump-001 including seal inspection and lubrication',
                 'completed', 'low', 'EMP001', 
                 json.dumps(['pump-seal-001', 'gasket-003']), 
                 json.dumps(['work-permit']), 4.0, 3.5, None),
                
                ('WO-2024-1002', 'pump-002', 'Emergency Seal Replacement', 
                 'Urgent seal replacement due to leakage in pump-002',
                 'in_progress', 'high', 'EMP002', 
                 json.dumps(['pump-seal-001', 'bearing-002']), 
                 json.dumps(['hot-work-permit', 'safety-permit']), 8.0, 2.0, None),
                
                ('WO-2024-1003', 'valve-001', 'Control Valve Calibration',
                 'Quarterly calibration of control valve-001 for pressure regulation',
                 'pending_approval', 'medium', None,
                 json.dumps(['valve-004']),
                 json.dumps(['work-permit']), 2.0, None, None)
            ]
            
            for wo in sample_workorders:
                cursor.execute("""
                    MERGE INTO workorders target
                    USING (SELECT :1 as workorder_id, :2 as equipment_id, :3 as title, 
                                  :4 as description, :5 as status, :6 as priority,
                                  :7 as assigned_to, :8 as required_parts, 
                                  :9 as permits_required, :10 as estimated_hours,
                                  :11 as actual_hours, :12 as completed_date FROM dual) source
                    ON (target.workorder_id = source.workorder_id)
                    WHEN MATCHED THEN
                        UPDATE SET equipment_id = source.equipment_id, title = source.title,
                                  description = source.description, status = source.status,
                                  priority = source.priority, assigned_to = source.assigned_to,
                                  required_parts = source.required_parts, 
                                  permits_required = source.permits_required,
                                  estimated_hours = source.estimated_hours,
                                  actual_hours = source.actual_hours,
                                  completed_date = source.completed_date
                    WHEN NOT MATCHED THEN
                        INSERT (workorder_id, equipment_id, title, description, status, 
                               priority, assigned_to, required_parts, permits_required,
                               estimated_hours, actual_hours, completed_date)
                        VALUES (source.workorder_id, source.equipment_id, source.title,
                               source.description, source.status, source.priority,
                               source.assigned_to, source.required_parts, 
                               source.permits_required, source.estimated_hours,
                               source.actual_hours, source.completed_date)
                """, wo)
            
            connection.commit()
            connection.close()
            logger.info("Oracle workorders schema created successfully with sample data")
            return True
        except Exception as e:
            logger.error(f"Failed to create Oracle schema: {str(e)}")
            return False

if __name__ == "__main__":
    setup = OracleSetup()
    success, message = setup.test_

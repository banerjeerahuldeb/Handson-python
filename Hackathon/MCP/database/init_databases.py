import sys
import os
import logging

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DatabaseConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_databases():
    """Initialize all database systems"""
    results = {}
    
    # 1. Initialize SQL Server (Inventory)
    try:
        from database.sql_server_setup import SQLServerSetup
        sql_setup = SQLServerSetup()
        sql_success, sql_message = sql_setup.test_connection()
        
        if sql_success:
            schema_created = sql_setup.create_inventory_schema()
            results['sql_server'] = {
                'status': 'success' if schema_created else 'schema_failed',
                'message': sql_message
            }
            logger.info("SQL Server initialized successfully")
        else:
            results['sql_server'] = {'status': 'failed', 'message': sql_message}
            logger.error(f"SQL Server initialization failed: {sql_message}")
            
    except Exception as e:
        results['sql_server'] = {'status': 'error', 'message': str(e)}
        logger.error(f"SQL Server error: {e}")
    
    # 2. Initialize PostgreSQL (WorkOrders)
    try:
        from database.postgresql_setup import PostgreSQLSetup
        postgres_setup = PostgreSQLSetup()
        postgres_success, postgres_message = postgres_setup.test_connection()
        
        if postgres_success:
            db_created = postgres_setup.create_database()
            if db_created:
                schema_created = postgres_setup.create_workorders_schema()
                results['postgresql'] = {
                    'status': 'success' if schema_created else 'schema_failed', 
                    'message': postgres_message
                }
                logger.info("PostgreSQL initialized successfully")
            else:
                results['postgresql'] = {'status': 'db_creation_failed', 'message': postgres_message}
                logger.warning(f"PostgreSQL database creation failed: {postgres_message}")
        else:
            results['postgresql'] = {'status': 'failed', 'message': postgres_message}
            logger.warning(f"PostgreSQL initialization failed: {postgres_message}")
            
    except Exception as e:
        results['postgresql'] = {'status': 'error', 'message': str(e)}
        logger.warning(f"PostgreSQL error: {e}")
    
    # 3. Create HR Excel data
    try:
        from data.create_hr_data import create_sample_hr_data
        excel_created = create_sample_hr_data()
        results['hr_excel'] = {
            'status': 'success' if excel_created else 'failed',
            'message': 'HR Excel data created'
        }
        logger.info("HR Excel data created successfully")
    except Exception as e:
        results['hr_excel'] = {'status': 'error', 'message': str(e)}
        logger.error(f"HR Excel creation failed: {e}")
    
    return results

if __name__ == "__main__":
    print("Initializing MCP Workflow System Databases...")
    print("=" * 50)
    
    results = initialize_databases()
    
    print("\nInitialization Results:")
    print("=" * 50)
    for db, result in results.items():
        status_icon = "✅" if result['status'] == 'success' else "⚠️" if result['status'] in ['skipped', 'db_creation_failed', 'schema_failed'] else "❌"
        print(f"{status_icon} {db.upper():<12} {result['status']:<15} {result['message']}")
    
    # Check if system is operational
    sql_ok = results.get('sql_server', {}).get('status') == 'success'
    postgres_ok = results.get('postgresql', {}).get('status') == 'success'
    
    if sql_ok and postgres_ok:
        print("\n🎉 System is ready! You can start the services.")
    else:
        print("\n⚠️  System has some issues but may still be operational.")

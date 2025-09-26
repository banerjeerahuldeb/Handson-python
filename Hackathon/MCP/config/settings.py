import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    # SQL Server Configuration (Windows Authentication)
    SQL_SERVER_HOST: str = os.getenv("SQL_SERVER_HOST", "AVD116\\SQLEXPRESS")
    SQL_SERVER_DB: str = os.getenv("SQL_SERVER_DB", "InventoryDB")
    SQL_SERVER_TRUSTED_CONNECTION: str = os.getenv("SQL_SERVER_TRUSTED_CONNECTION", "yes")
    
    # Oracle Cloud Configuration
    ORACLE_DSN: str = os.getenv("ORACLE_DSN", 
        "(description= (retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1522)(host=adb.ap-mumbai-1.oraclecloud.com))(connect_data=(service_name=g47e7c82019d9f8_kg94u2w2g92iyiti_high.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes))")
    ORACLE_USER: str = os.getenv("ORACLE_USER", "your_oracle_username")
    ORACLE_PASSWORD: str = os.getenv("ORACLE_PASSWORD", "your_oracle_password")
    
    # API Configuration
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8001")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Application Settings
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Connection strings
# SQL Server with Windows Authentication
SQL_SERVER_CONNECTION_STRING = (
    f"mssql+pyodbc://{DatabaseConfig.SQL_SERVER_HOST}/{DatabaseConfig.SQL_SERVER_DB}"
    f"?trusted_connection={DatabaseConfig.SQL_SERVER_TRUSTED_CONNECTION}"
    f"&driver=ODBC+Driver+17+for+SQL+Server"
)

# Oracle with custom DSN
ORACLE_CONNECTION_STRING = f"oracle://{DatabaseConfig.ORACLE_USER}:{DatabaseConfig.ORACLE_PASSWORD}@?dsn={DatabaseConfig.ORACLE_DSN}"

# Alternative Oracle connection string for oracledb driver
ORACLE_CONNECTION_STRING_ORACLEDB = {
    "user": DatabaseConfig.ORACLE_USER,
    "password": DatabaseConfig.ORACLE_PASSWORD,
    "dsn": DatabaseConfig.ORACLE_DSN
}

import os
from dataclasses import dataclass

@dataclass
class DatabaseConfig:
    # SQL Server Configuration
    SQL_SERVER_HOST: str = os.getenv("SQL_SERVER_HOST", "localhost")
    SQL_SERVER_PORT: str = os.getenv("SQL_SERVER_PORT", "1433")
    SQL_SERVER_DB: str = os.getenv("SQL_SERVER_DB", "InventoryDB")
    SQL_SERVER_USER: str = os.getenv("SQL_SERVER_USER", "sa")
    SQL_SERVER_PASSWORD: str = os.getenv("SQL_SERVER_PASSWORD", "Password123!")
    
    # Oracle Configuration
    ORACLE_HOST: str = os.getenv("ORACLE_HOST", "localhost")
    ORACLE_PORT: str = os.getenv("ORACLE_PORT", "1521")
    ORACLE_SERVICE: str = os.getenv("ORACLE_SERVICE", "XE")
    ORACLE_USER: str = os.getenv("ORACLE_USER", "system")
    ORACLE_PASSWORD: str = os.getenv("ORACLE_PASSWORD", "oracle")
    
    # API Configuration
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8001")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# Connection strings
SQL_SERVER_CONNECTION_STRING = f"mssql+pyodbc://{DatabaseConfig.SQL_SERVER_USER}:{DatabaseConfig.SQL_SERVER_PASSWORD}@{DatabaseConfig.SQL_SERVER_HOST}:{DatabaseConfig.SQL_SERVER_PORT}/{DatabaseConfig.SQL_SERVER_DB}?driver=ODBC+Driver+17+for+SQL+Server"
ORACLE_CONNECTION_STRING = f"oracle://{DatabaseConfig.ORACLE_USER}:{DatabaseConfig.ORACLE_PASSWORD}@{DatabaseConfig.ORACLE_HOST}:{DatabaseConfig.ORACLE_PORT}/?service_name={DatabaseConfig.ORACLE_SERVICE}"

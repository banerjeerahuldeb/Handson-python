import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    # SQL Server Configuration (Windows Authentication)
    SQL_SERVER_HOST: str = os.getenv("SQL_SERVER_HOST", "AVDAILAB-16\\SQLEXPRESS")
    SQL_SERVER_DB: str = os.getenv("SQL_SERVER_DB", "InventoryDB")
    SQL_SERVER_TRUSTED_CONNECTION: str = os.getenv("SQL_SERVER_TRUSTED_CONNECTION", "yes")
    
    # PostgreSQL Configuration
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "workorders_db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    
    # API Configuration
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8001")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Application Settings
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Connection strings
SQL_SERVER_CONNECTION_STRING = (
    f"mssql+pyodbc://{DatabaseConfig.SQL_SERVER_HOST}/{DatabaseConfig.SQL_SERVER_DB}"
    f"?trusted_connection={DatabaseConfig.SQL_SERVER_TRUSTED_CONNECTION}"
    f"&TrustServerCertificate=yes"
    f"&driver=ODBC+Driver+17+for+SQL+Server"
)

# PostgreSQL connection string
POSTGRES_CONNECTION_STRING = (
    f"postgresql://{DatabaseConfig.POSTGRES_USER}:{DatabaseConfig.POSTGRES_PASSWORD}"
    f"@{DatabaseConfig.POSTGRES_HOST}:{DatabaseConfig.POSTGRES_PORT}/{DatabaseConfig.POSTGRES_DB}"
)

# For SQLAlchemy (if used)
POSTGRES_SQLALCHEMY_URI = POSTGRES_CONNECTION_STRING

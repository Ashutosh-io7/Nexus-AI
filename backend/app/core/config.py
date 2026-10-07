from pathlib import Path 

from pydantic_settings import BaseSettings, SettingsConfigDict 

# The .env file lives in the project root. 
ROOT_DIR = Path(__file__).resolve().parents[3] 


class Settings(BaseSettings): 
    app_env: str = "development"
    database_url: str 
    cors_origins: str = "http://localhost:5173" 

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        extra="ignore",
    ) 

    @property 
    def cors_origins_list(self) -> list[str]: 
        return [origin.strip() for origin in self.cors_origins.split(",")] 

    @property
    def sqlalchemy_database_url(self) -> str: 
        return self.database_url.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )

settings = Settings() 
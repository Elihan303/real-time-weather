from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime, func

# Actualiza la cadena de conexión con tus credenciales y nombre de base de datos.
DATABASE_URL = "postgresql+asyncpg://username:password@localhost/databasename"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class WeatherReport(Base):
    __tablename__ = "weather_reports"
    id = Column(Integer, primary_key=True, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    condition = Column(String(50), nullable=False)
    description = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

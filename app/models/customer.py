"""Customer ORM Model."""
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    segment = Column(String(50), default="Standard", nullable=False)
    country = Column(String(50), default="United States", nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name='{self.name}', email='{self.email}', segment='{self.segment}')>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "segment": self.segment,
            "country": self.country,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

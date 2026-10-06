"""Order ORM Model."""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import relationship
from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    order_date = Column(DateTime, default=func.now(), nullable=False)
    status = Column(String(50), default="completed", nullable=False, index=True)  # completed, pending, cancelled, refunded
    total_amount = Column(Numeric(10, 2), nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, customer_id={self.customer_id}, status='{self.status}', total={self.total_amount})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "status": self.status,
            "total_amount": float(self.total_amount) if self.total_amount is not None else 0.0,
        }


Index("ix_orders_status_date", Order.status, Order.order_date)

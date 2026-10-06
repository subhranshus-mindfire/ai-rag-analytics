"""
Backward-compatibility alias module for analytics models.
Re-exports decomposed models from customer, product, order, and order_item.
"""
from app.models.customer import Customer
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem

__all__ = ["Customer", "Product", "Order", "OrderItem"]

from sqlalchemy import BigInteger, String, Boolean, Float, Integer, ForeignKey, DateTime, JSON, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from datetime import datetime
import enum

class Base(AsyncAttrs, DeclarativeBase):
    pass

class PaymentProvider(str, enum.Enum):
    STARS = "stars"
    YOOKASSA = "yookassa"
    PLATEGA = "platega"
    TRIBUTE = "tribute"
    MANUAL = "manual"

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram ID
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str] = mapped_column(String(10), default="en")
    
    remnawave_uuid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    is_trial_used: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    orders: Mapped[list["Order"]] = relationship(back_populates="user")

class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="RUB")
    
    duration_days: Mapped[int] = mapped_column(Integer)
    traffic_limit_gb: Mapped[int | None] = mapped_column(Integer, nullable=True) # None = Unlimited
    
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Promocode(Base):
    __tablename__ = "promocodes"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    is_percent: Mapped[bool] = mapped_column(Boolean, default=True) # True = %, False = Fixed amount
    value: Mapped[float] = mapped_column(Float) # 10 means 10% or 10 RUB
    
    max_uses: Mapped[int] = mapped_column(Integer, default=0) # 0 = Unlimited
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    
    active_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id"))
    
    payment_provider: Mapped[PaymentProvider] = mapped_column(SAEnum(PaymentProvider))
    invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), default=OrderStatus.PENDING)
    
    promocode_code: Mapped[str | None] = mapped_column(ForeignKey("promocodes.code"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    user: Mapped["User"] = relationship(back_populates="orders")
    tariff: Mapped["Tariff"] = relationship()

class KeyValue(Base):
    __tablename__ = "key_value"
    
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(String)

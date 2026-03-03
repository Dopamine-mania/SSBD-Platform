from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

Base = declarative_base()

# Enums
class UserRole(enum.Enum):
    ADMIN = "admin"
    FRONT_DESK = "front_desk"
    ENGINEER = "engineer"

class ResourceType(enum.Enum):
    RECORDING_ROOM = "recording_room"
    CONTROL_ROOM = "control_room"
    MICROPHONE = "microphone"
    SOUND_CARD = "sound_card"
    OTHER_EQUIPMENT = "other_equipment"

class ResourceStatus(enum.Enum):
    AVAILABLE_RENTAL = "available_rental"      # 可租
    INTERNAL_ONLY = "internal_only"            # 仅内用
    MAINTENANCE = "maintenance"                # 维修中

class BookingStatus(enum.Enum):
    PENDING = "pending"                        # 待确认
    CONFIRMED = "confirmed"                    # 已确认
    IN_PROGRESS = "in_progress"                # 进行中
    COMPLETED = "completed"                    # 已完成
    CANCELLED = "cancelled"                    # 已取消

class PaymentMethod(enum.Enum):
    CASH = "cash"                              # 现金
    WECHAT = "wechat"                          # 微信
    ALIPAY = "alipay"                          # 支付宝

class OrderStatus(enum.Enum):
    PENDING = "pending"                        # 待支付
    PAID = "paid"                              # 已支付
    REFUNDED = "refunded"                      # 已退款

# Models
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    email = Column(String(100))
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bookings_created = relationship("Booking", back_populates="created_by_user", foreign_keys="Booking.created_by")
    bookings_assigned = relationship("Booking", back_populates="engineer_user", foreign_keys="Booking.engineer_id")
    audit_logs = relationship("AuditLog", back_populates="user")

class Resource(Base):
    __tablename__ = 'resources'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    resource_type = Column(Enum(ResourceType), nullable=False)
    status = Column(Enum(ResourceStatus), default=ResourceStatus.AVAILABLE_RENTAL)
    serial_number = Column(String(100))
    photo_path = Column(String(255))
    hourly_rate = Column(Float, default=0.0)  # 时价
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    booking_resources = relationship("BookingResource", back_populates="resource")

class Customer(Base):
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    email = Column(String(100))
    company = Column(String(100))
    preferences = Column(Text)  # JSON string for preferences
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bookings = relationship("Booking", back_populates="customer")

class Booking(Base):
    __tablename__ = 'bookings'

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    engineer_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING)

    # Time tracking
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)
    pause_duration_minutes = Column(Integer, default=0)  # Total pause time
    is_late = Column(Boolean, default=False)
    late_minutes = Column(Integer, default=0)

    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="bookings")
    created_by_user = relationship("User", back_populates="bookings_created", foreign_keys=[created_by])
    engineer_user = relationship("User", back_populates="bookings_assigned", foreign_keys=[engineer_id])
    booking_resources = relationship("BookingResource", back_populates="booking", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="booking")
    time_logs = relationship("TimeLog", back_populates="booking", cascade="all, delete-orphan")

class BookingResource(Base):
    __tablename__ = 'booking_resources'

    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False)
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False)
    quantity = Column(Integer, default=1)

    # Relationships
    booking = relationship("Booking", back_populates="booking_resources")
    resource = relationship("Resource", back_populates="booking_resources")

class TimeLog(Base):
    __tablename__ = 'time_logs'

    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False)
    action = Column(String(20), nullable=False)  # 'start', 'pause', 'resume', 'end'
    timestamp = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)

    # Relationships
    booking = relationship("Booking", back_populates="time_logs")

class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False)

    # Billing breakdown
    room_charge = Column(Float, default=0.0)
    engineer_charge = Column(Float, default=0.0)
    equipment_charge = Column(Float, default=0.0)
    night_surcharge = Column(Float, default=0.0)  # 22:00-08:00 +20%
    subtotal = Column(Float, nullable=False)
    total = Column(Float, nullable=False)

    # Payment
    payment_method = Column(Enum(PaymentMethod), nullable=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    paid_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    refund_approved_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    invoice_notes = Column(Text)  # 开票信息备注
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    booking = relationship("Booking", back_populates="orders")
    refund_approver = relationship("User", foreign_keys=[refund_approved_by])

class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action = Column(String(100), nullable=False)  # e.g., 'LOGIN', 'CREATE_BOOKING', 'REFUND'
    entity_type = Column(String(50))  # e.g., 'Booking', 'Order'
    entity_id = Column(Integer)
    details = Column(Text)  # JSON string for additional details
    ip_address = Column(String(45))
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

class Notification(Base):
    """通知消息表"""
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # 接收通知的用户
    title = Column(String(200), nullable=False)  # 通知标题
    message = Column(Text, nullable=False)  # 通知内容
    notification_type = Column(String(50), nullable=False)  # 通知类型：LATE_ARRIVAL, BOOKING_REMINDER, SYSTEM
    related_entity_type = Column(String(50))  # 关联实体类型：Booking, Order
    related_entity_id = Column(Integer)  # 关联实体ID
    is_read = Column(Boolean, default=False)  # 是否已读
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)  # 阅读时间

    # Relationships
    user = relationship("User")


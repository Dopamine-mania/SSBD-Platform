"""Initialize database with comprehensive sample data."""
import logging
from datetime import datetime, timedelta
from database.connection import db
from database.models import (
    User, UserRole, Resource, ResourceType, ResourceStatus,
    Customer, Booking, BookingResource, BookingStatus
)
from utils.security import hash_password

logger = logging.getLogger(__name__)

def init_sample_data():
    """Initialize database with sample data for testing."""
    logger.info("Initializing sample data...")

    with db.get_session() as session:
        # Check if data already exists
        existing_resources = session.query(Resource).count()
        if existing_resources > 0:
            logger.info("Sample data already exists, skipping initialization")
            return

        # Create resources
        logger.info("Creating sample resources...")

        # Recording rooms
        room_a = Resource(
            name="录音间A",
            resource_type=ResourceType.RECORDING_ROOM,
            status=ResourceStatus.AVAILABLE_RENTAL,
            hourly_rate=200.0,
            description="专业录音间，配备隔音设施"
        )
        session.add(room_a)

        room_b = Resource(
            name="录音间B",
            resource_type=ResourceType.RECORDING_ROOM,
            status=ResourceStatus.AVAILABLE_RENTAL,
            hourly_rate=180.0,
            description="中型录音间，适合小型乐队"
        )
        session.add(room_b)

        # Control room
        control_room = Resource(
            name="控制室1",
            resource_type=ResourceType.CONTROL_ROOM,
            status=ResourceStatus.AVAILABLE_RENTAL,
            hourly_rate=150.0,
            description="专业控制室，配备混音设备"
        )
        session.add(control_room)

        # Microphones
        mic_u87 = Resource(
            name="话筒 Neumann U87",
            resource_type=ResourceType.MICROPHONE,
            status=ResourceStatus.AVAILABLE_RENTAL,
            serial_number="U87-001",
            hourly_rate=50.0,
            description="经典电容话筒"
        )
        session.add(mic_u87)

        mic_sm58 = Resource(
            name="话筒 Shure SM58",
            resource_type=ResourceType.MICROPHONE,
            status=ResourceStatus.AVAILABLE_RENTAL,
            serial_number="SM58-001",
            hourly_rate=30.0,
            description="动圈话筒，适合人声"
        )
        session.add(mic_sm58)

        # Sound cards
        soundcard = Resource(
            name="声卡 Focusrite Scarlett 2i2",
            resource_type=ResourceType.SOUND_CARD,
            status=ResourceStatus.AVAILABLE_RENTAL,
            serial_number="SC-001",
            hourly_rate=40.0,
            description="专业音频接口"
        )
        session.add(soundcard)

        # Equipment in maintenance
        mic_maintenance = Resource(
            name="话筒 AKG C414 (维修中)",
            resource_type=ResourceType.MICROPHONE,
            status=ResourceStatus.MAINTENANCE,
            serial_number="C414-001",
            hourly_rate=60.0,
            description="维修中，暂不可用"
        )
        session.add(mic_maintenance)

        session.flush()

        # Create customers
        logger.info("Creating sample customers...")

        customers_data = [
            ("张三", "13800138001", "zhangsan@example.com", "独立音乐人"),
            ("李四", "13800138002", "lisi@example.com", "乐队主唱"),
            ("王五", "13800138003", "wangwu@example.com", "音乐制作人"),
            ("赵六", "13800138004", "zhaoliu@example.com", "播客主播"),
            ("钱七", "13800138005", "qianqi@example.com", "配音演员"),
        ]

        customers = []
        for name, phone, email, company in customers_data:
            customer = Customer(
                name=name,
                phone=phone,
                email=email,
                company=company,
                preferences="偏好使用录音间A"
            )
            session.add(customer)
            customers.append(customer)

        session.flush()

        # Get users for bookings
        admin = session.query(User).filter(User.username == "admin").first()
        engineer = session.query(User).filter(User.username == "engineer").first()

        if not admin or not engineer:
            logger.warning("Default users not found, skipping booking creation")
            session.commit()
            return

        # Create sample bookings
        logger.info("Creating sample bookings...")

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Today's bookings
        bookings_data = [
            # Morning booking
            {
                'customer': customers[0],
                'start': today.replace(hour=9, minute=0),
                'end': today.replace(hour=11, minute=0),
                'resources': [room_a, mic_u87],
                'status': BookingStatus.CONFIRMED,
                'notes': "录制新专辑"
            },
            # Afternoon booking
            {
                'customer': customers[1],
                'start': today.replace(hour=14, minute=0),
                'end': today.replace(hour=16, minute=30),
                'resources': [room_b, mic_sm58, soundcard],
                'status': BookingStatus.CONFIRMED,
                'notes': "乐队排练"
            },
            # Evening booking (night surcharge applies)
            {
                'customer': customers[2],
                'start': today.replace(hour=20, minute=0),
                'end': today.replace(hour=23, minute=0),
                'resources': [control_room, mic_u87],
                'status': BookingStatus.PENDING,
                'notes': "混音工作"
            },
            # Tomorrow's booking
            {
                'customer': customers[3],
                'start': (today + timedelta(days=1)).replace(hour=10, minute=0),
                'end': (today + timedelta(days=1)).replace(hour=12, minute=0),
                'resources': [room_a, mic_sm58],
                'status': BookingStatus.CONFIRMED,
                'notes': "播客录制"
            },
            # Yesterday's completed booking
            {
                'customer': customers[4],
                'start': (today - timedelta(days=1)).replace(hour=15, minute=0),
                'end': (today - timedelta(days=1)).replace(hour=17, minute=0),
                'resources': [room_b, mic_u87],
                'status': BookingStatus.COMPLETED,
                'notes': "配音工作"
            },
        ]

        for booking_data in bookings_data:
            booking = Booking(
                customer_id=booking_data['customer'].id,
                created_by=admin.id,
                engineer_id=engineer.id if booking_data['status'] != BookingStatus.PENDING else None,
                start_time=booking_data['start'],
                end_time=booking_data['end'],
                status=booking_data['status'],
                notes=booking_data['notes']
            )
            session.add(booking)
            session.flush()

            # Add resources to booking
            for resource in booking_data['resources']:
                booking_resource = BookingResource(
                    booking_id=booking.id,
                    resource_id=resource.id,
                    quantity=1
                )
                session.add(booking_resource)

        session.commit()
        logger.info("Sample data initialization completed successfully")

        # Print summary
        print("\n" + "="*60)
        print("📊 样本数据初始化完成")
        print("="*60)
        print(f"✅ 资源: 7个 (3个房间, 3个话筒, 1个声卡)")
        print(f"✅ 客户: 5个")
        print(f"✅ 预约: 5个 (今天3个, 明天1个, 昨天1个)")
        print("="*60)
        print("\n💡 提示: 运行 python app.py 启动应用")
        print("   登录账号: admin / admin123\n")

if __name__ == "__main__":
    from config.logging_config import setup_logging

    setup_logging()
    db.initialize()
    init_sample_data()
    db.close()

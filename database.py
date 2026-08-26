import time
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
engine = create_engine("sqlite:///bot_database.db", echo=False)
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, index=True)
    balance = Column(Float, default=0.0)
    referrer_id = Column(Integer, nullable=True)
    reward_given = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(Integer, default=lambda: int(time.time()))

class SponsorChannel(Base):
    __tablename__ = "sponsor_channels"
    id = Column(Integer, primary_key=True)
    channel_id = Column(String)  # @username или -100xxx
    title = Column(String)
    link = Column(String)

class CustomTask(Base):
    __tablename__ = "custom_tasks"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    link = Column(String)
    channel_id = Column(String)
    reward = Column(Float)

class ConfigSetting(Base):
    __tablename__ = "config_settings"
    key = Column(String, primary_key=True)
    value = Column(Text)

class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    amount = Column(Float)
    status = Column(String, default="pending")  # pending, approved, rejected

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    message = Column(Text)
    status = Column(String, default="open")

def init_db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    defaults = {
        "ref_reward": "6.0",
        "daily_bonus": "1.0",
        "withdrawal_channel": "",
        "welcome_photo": "",
        "welcome_text": "🔔 **Привет!**\n\nПодпишись на спонсоров ниже, чтобы войти в бота, приглашать друзей и зарабатывать 👆 прямо к себе в профиль!",
        "main_menu_text": "💬 **Добро пожаловать в бота!**\n\nПриглашай друзей и получай звёзды и подарки к себе в профиль!"
    }
    for k, v in defaults.items():
        if not session.query(ConfigSetting).filter_by(key=k).first():
            session.add(ConfigSetting(key=k, value=v))
    session.commit()
    session.close()
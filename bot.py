import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db, SessionLocal, User, SponsorChannel, ConfigSetting
from handlers import router, is_subscribed
from admin import admin_router

async def check_unsubscribers_loop(bot: Bot):
    while True:
        await asyncio.sleep(600)
        db = SessionLocal()
        users = db.query(User).filter_by(reward_given=True, is_blocked=False).all()
        sponsors = db.query(SponsorChannel).all()
        
        for u in users:
            for sp in sponsors:
                subbed = await is_subscribed(bot, u.telegram_id, sp.channel_id)
                if not subbed:
                    u.is_blocked = True
                    if u.referrer_id:
                        ref_user = db.query(User).filter_by(telegram_id=u.referrer_id).first()
                        if ref_user:
                            reward = float(db.query(ConfigSetting).filter_by(key="ref_reward").first().value)
                            ref_user.balance = max(0.0, ref_user.balance - reward)
                    db.commit()
                    break
        db.close()

async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    dp.include_router(router)
    dp.include_router(admin_router)
    
    asyncio.create_task(check_unsubscribers_loop(bot))
    
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
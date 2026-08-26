from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from config import ADMIN_IDS
from database import SessionLocal, User, SponsorChannel, ConfigSetting, WithdrawalRequest

admin_router = Router()

@admin_router.message(Command("admin"))
async def admin_main(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer(
        "🛠 **Панель Администратора**\n\n"
        "Команды:\n"
        "• `/broadcast Текст` — Массовая рассылка\n"
        "• `/add_channel ID Ссылка` — Добавить спонсора\n"
        "• `/set_reward 6.0` — Награда за реферала\n"
        "• `/set_withdraw_chat -100xxx` — Канал выплат\n"
        "• `/set_photo photo_id` — Прикрепить фото к старту",
        parse_mode="Markdown"
    )

@admin_router.message(Command("broadcast"))
async def broadcast_msg(message: Message, bot: Bot):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text.replace("/broadcast ", "")
    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    
    count = 0
    for u in users:
        try:
            await bot.send_message(u.telegram_id, text)
            count += 1
        except Exception:
            pass
    await message.answer(f"✅ Успешно отправлено {count} пользователям.")

@admin_router.callback_query(F.data.startswith("app_w_"))
async def approve_withdrawal(call: CallbackQuery, bot: Bot):
    if call.from_user.id not in ADMIN_IDS:
        return
    req_id = int(call.data.split("_")[2])
    db = SessionLocal()
    req = db.query(WithdrawalRequest).get(req_id)
    
    if req and req.status == "pending":
        req.status = "approved"
        db.commit()
        await call.message.edit_text(f"✅ Вывод #{req.id} на {req.amount} ⭐ одобрен!")
        
        try:
            await bot.send_message(req.user_id, f"🎉 Ваша заявка на вывод {req.amount} ⭐ одобрена!")
        except Exception:
            pass
            
        channel_id = db.query(ConfigSetting).filter_by(key="withdrawal_channel").first()
        if channel_id and channel_id.value:
            try:
                await bot.send_message(channel_id.value, f"💸 **Успешный вывод!**\nПользователь: `{req.user_id}` вывел **{req.amount} ⭐**", parse_mode="Markdown")
            except Exception:
                pass
    db.close()
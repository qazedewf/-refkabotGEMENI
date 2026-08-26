import random
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import SessionLocal, User, SponsorChannel, ConfigSetting, CustomTask, WithdrawalRequest, SupportTicket

router = Router()

class Form(StatesGroup):
    support_msg = State()
    withdraw_amt = State()

def get_config(key: str) -> str:
    db = SessionLocal()
    val = db.query(ConfigSetting).filter_by(key=key).first()
    db.close()
    return val.value if val else ""

async def is_subscribed(bot: Bot, user_id: int, channel_id: str) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status not in ["left", "kicked"]
    except Exception:
        return False

async def check_all_subscriptions(bot: Bot, user_id: int) -> bool:
    db = SessionLocal()
    channels = db.query(SponsorChannel).all()
    db.close()
    for ch in channels:
        if not await is_subscribed(bot, user_id, ch.channel_id):
            return False
    return True

@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject, bot: Bot):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=message.from_user.id).first()
    
    referrer_id = int(command.args) if command.args and command.args.isdigit() else None

    if not user:
        user = User(telegram_id=message.from_user.id, referrer_id=referrer_id)
        db.add(user)
        db.commit()

    if user.is_blocked:
        await message.answer("❌ Вы заблокированы за отписку от спонсоров!")
        db.close()
        return

    is_subbed = await check_all_subscriptions(bot, message.from_user.id)
    photo_id = get_config("welcome_photo")
    
    if not is_subbed:
        channels = db.query(SponsorChannel).all()
        kb = []
        for i in range(0, len(channels), 2):
            row = [InlineKeyboardButton(text=f"🌀 Спонсор", url=channels[i].link)]
            if i + 1 < len(channels):
                row.append(InlineKeyboardButton(text=f"🌀 Спонсор", url=channels[i+1].link))
            kb.append(row)
            
        kb.append([InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")])
        text = get_config("welcome_text")
        
        if photo_id:
            await message.answer_photo(photo_id, caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")
        else:
            await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")
    else:
        await send_main_menu(message)
    db.close()

@router.callback_query(F.data == "check_sub")
async def check_sub_callback(call: CallbackQuery, bot: Bot):
    if not await check_all_subscriptions(bot, call.from_user.id):
        await call.answer("❌ Вы подписались не на все каналы!", show_alert=True)
        return

    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=call.from_user.id).first()
    
    if user and user.referrer_id and not user.reward_given:
        ref_user = db.query(User).filter_by(telegram_id=user.referrer_id).first()
        if ref_user:
            reward = float(get_config("ref_reward"))
            ref_user.balance += reward
            user.reward_given = True
            db.commit()
            try:
                await bot.send_message(ref_user.telegram_id, f"🎉 Ваш реферал подписался! Начислено +{reward} ⭐")
            except Exception:
                pass

    await call.message.delete()
    await send_main_menu(call.message)
    db.close()

async def send_main_menu(message: Message):
    ref_reward = get_config("ref_reward")
    main_text = get_config("main_menu_text")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👥 Пригласить друга ( +{ref_reward}⭐️ )", callback_data="ref_link")],
        [InlineKeyboardButton(text="👾 Питомцы", callback_data="pets")],
        [InlineKeyboardButton(text="✅ Профиль", callback_data="profile"), InlineKeyboardButton(text="💰 Вывести звёзды", callback_data="withdraw_start")],
        [InlineKeyboardButton(text="🏆 Топ рефоводов", callback_data="top_ref")],
        [InlineKeyboardButton(text="🎯 Задания", callback_data="tasks_menu")],
        [InlineKeyboardButton(text="🎁 Кейсы", callback_data="cases_menu")],
        [InlineKeyboardButton(text="🛟 Поддержка", callback_data="support_start")]
    ])
    await message.answer(main_text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "cases_menu")
async def open_cases_menu(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Обычный кейс (10 ⭐)", callback_data="open_case_10")],
        [InlineKeyboardButton(text="🔥 Премиум кейс (50 ⭐)", callback_data="open_case_50")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="to_main")]
    ])
    await call.message.edit_text("🎲 **Выберите кейс:**\n\nИспытайте удачу!", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("open_case_"))
async def process_case(call: CallbackQuery):
    cost = int(call.data.split("_")[2])
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=call.from_user.id).first()
    
    if user.balance < cost:
        await call.answer("❌ Недостаточно ⭐ на балансе!", show_alert=True)
        db.close()
        return

    win = random.choices([1, 3, 5, 8, 12] if cost == 10 else [5, 15, 25, 40, 60], weights=[40, 30, 15, 10, 5])[0]
    user.balance = user.balance - cost + win
    db.commit()
    db.close()
    
    await call.message.edit_text(f"🎰 Вы открыли кейс за {cost} ⭐ и выиграли **{win} ⭐**!", parse_mode="Markdown")

@router.callback_query(F.data == "withdraw_start")
async def withdraw_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(Form.withdraw_amt)
    await call.message.answer("💸 Введите количество ⭐ для вывода:")

@router.message(Form.withdraw_amt)
async def process_withdraw(message: Message, state: FSMContext, bot: Bot):
    if not message.text.isdigit():
        await message.answer("Введите корректное число!")
        return
    amt = float(message.text)
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=message.from_user.id).first()
    
    if user.balance < amt or amt <= 0:
        await message.answer("❌ Недостаточно средств!")
        db.close()
        return

    user.balance -= amt
    req = WithdrawalRequest(user_id=message.from_user.id, amount=amt)
    db.add(req)
    db.commit()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"app_w_{req.id}"), InlineKeyboardButton(text="❌ Отклонить", callback_data=f"rej_w_{req.id}")]
    ])
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"📥 **Заявка на вывод #{req.id}**\nЮзер: `{message.from_user.id}`\nСумма: {amt} ⭐", reply_markup=kb, parse_mode="Markdown")
        except Exception:
            pass
            
    await message.answer("✅ Заявка на вывод создана и отправлена администраторам!")
    await state.clear()
    db.close()

@router.callback_query(F.data == "support_start")
async def support_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(Form.support_msg)
    await call.message.answer("🛟 Опишите вашу проблему в одном сообщении:")

@router.message(Form.support_msg)
async def process_support(message: Message, state: FSMContext, bot: Bot):
    db = SessionLocal()
    ticket = SupportTicket(user_id=message.from_user.id, message=message.text)
    db.add(ticket)
    db.commit()
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"📩 **Тикет поддержки #{ticket.id}**\nОт: `{message.from_user.id}`\nТекст: {message.text}", parse_mode="Markdown")
        except Exception:
            pass
            
    await message.answer("✅ Ваше обращение отправлено поддержке!")
    await state.clear()
    db.close()
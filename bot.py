import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiocryptopay import AioCryptoPay, Networks

TOKEN = "8578958503:AAFaKoz4cRJ18tzerBEZgM_l-T3OUi-sjFM"
CRYPTO_TOKEN = "631807:AA4a2oJZY5wDjj0SnoVUUJcLgJwJ4p5Q6Q1"

bot = Bot(TOKEN)
dp = Dispatcher()
crypto = AioCryptoPay(token=CRYPTO_TOKEN, network=Networks.MAIN_NET)

# Словарь для сохранения ID счета пользователя: {user_id: invoice_id}
user_invoices = {}


def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🛍 Услуги (Аккаунты)", callback_data="services")
    kb.button(text="⚙️ Настройки", callback_data="settings")
    kb.row(InlineKeyboardButton(text="💬 Поддержка", url="https://t.me/svekla_www"))
    kb.adjust(1, 1, 1)
    return kb.as_markup()


def settings_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🇷🇺 Русский", callback_data="lang_ru")
    kb.button(text="🇬🇧 English", callback_data="lang_en")
    kb.button(text="⬅️ Главное меню", callback_data="home")
    kb.adjust(2, 1)
    return kb.as_markup()


def services_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🇺🇸 Аккаунт США — 100 руб.", callback_data="item_us")
    kb.button(text="🇷🇺 Аккаунт Россия — 200 руб.", callback_data="item_ru")
    kb.button(text="🇺🇦 Аккаунт Украина — 250 руб.", callback_data="item_ua")
    kb.button(text="🇰🇿 Аккаунт Казахстан — 200 руб.", callback_data="item_kz")
    kb.button(text="🇮🇳 Аккаунт Индия — 100 руб.", callback_data="item_in")
    kb.button(text="⬅️ Главное меню", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🟣 <b>Свекла Shop</b>\n\n"
        "Добро пожаловать!\n"
        "Выберите раздел:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


@dp.callback_query()
async def buttons(callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    
    if data == "services":
        await callback.message.edit_text(
            "🛍 <b>Доступные аккаунты</b>\n\n"
            "Выберите интересующий вас вариант:",
            reply_markup=services_menu(),
            parse_mode="HTML"
        )
    elif data == "settings":
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>\n\n"
            "Выберите язык интерфейса:",
            reply_markup=settings_menu(),
            parse_mode="HTML"
        )
    elif data == "home":
        await callback.message.edit_text(
            "🟣 <b>Свекла Shop</b>\n\n"
            "Добро пожаловать!\n"
            "Выберите раздел:",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
    elif data.startswith("item_"):
        items = {
            "item_us": ("Аккаунт США", 100),
            "item_ru": ("Аккаунт Россия", 200),
            "item_ua": ("Аккаунт Украина", 250),
            "item_kz": ("Аккаунт Казахстан", 200),
            "item_in": ("Аккаунт Индия", 100)
        }
        
        item_name, price_rub = items.get(data, ("Товар", 100))
        usdt_amount = round(price_rub / 100.0, 2)
        
        try:
            invoice = await crypto.create_invoice(
                asset='USDT', 
                amount=usdt_amount, 
                description=f"Покупка: {item_name} ({price_rub} руб.)"
            )
            
            # Сохраняем ID инвойса конкретного пользователя
            user_invoices[user_id] = invoice.invoice_id
            
            pay_kb = InlineKeyboardBuilder()
            pay_kb.button(text="💳 Оплатить в CryptoBot", url=invoice.bot_invoice_url)
            pay_kb.button(text="✅ Проверить оплату", callback_data="check_payment")
            pay_kb.button(text="⬅️ Назад к списку", callback_data="services")
            pay_kb.adjust(1)
            
            await callback.message.edit_text(
                f"🧾 <b>Счет на оплату создан!</b>\n\n"
                f"Товар: <b>{item_name}</b>\n"
                f"Цена: <b>{price_rub} руб.</b> (≈ <b>{usdt_amount} USDT</b>)\n\n"
                f"Оплатите счет через CryptoBot, после чего нажмите кнопку проверки.",
                reply_markup=pay_kb.as_markup(),
                parse_mode="HTML"
            )
        except Exception as e:
            await callback.answer("Ошибка создания счета. Проверьте токен CryptoBot.", show_alert=True)

    elif data == "check_payment":
        invoice_id = user_invoices.get(user_id)
        
        if not invoice_id:
            await callback.answer("У вас нет активных счетов для проверки.", show_alert=True)
            return

        try:
            # Делаем реальный запрос в CryptoBot для проверки статуса счета
            invoices = await crypto.get_invoices(invoice_ids=invoice_id)
            invoice = invoices[0] if invoices else None

            if invoice and invoice.status == "paid":
                success_kb = InlineKeyboardBuilder()
                success_kb.button(text="💬 Написать в поддержку", url="https://t.me/svekla_www")
                success_kb.button(text="⬅️ В главное меню", callback_data="home")
                success_kb.adjust(1)
                
                # Удаляем сохраненный инвойс, так как он уже оплачен
                user_invoices.pop(user_id, None)

                await callback.message.edit_text(
                    "✅ <b>Успешно!</b>\n\n"
                    "Оплата получена!\n"
                    "Пожалуйста, отпишите в техподдержку (@svekla_www) для получения номера и кода.",
                    reply_markup=success_kb.as_markup(),
                    parse_mode="HTML"
                )
            else:
                await callback.answer("❌ Оплата не найдена или еще не поступила. Попробуйте еще раз после оплаты.", show_alert=True)
        except Exception as e:
            await callback.answer("Ошибка при проверке платежа. Попробуйте позже.", show_alert=True)

    elif data.startswith("lang_"):
        lang = "Русский 🇷🇺" if data.endswith("ru") else "English 🇬🇧"
        await callback.answer(f"Язык изменен на: {lang}", show_alert=True)

    await callback.answer()


async def main():
    try:
        await dp.start_polling(bot)
    finally:
        await crypto.close()

if name == "main":
    asyncio.run(main())
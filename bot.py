import asyncio
import aiohttp
import os
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiocryptopay import AioCryptoPay, Networks

TOKEN = "8578958503:AAFaKoZ4cRJi8tzerBEZgM_1-T3OUi-sjfM"
CRYPTO_TOKEN = "631807:AAAa2oJZYSw0Dj0SnoVAUjclgJw4pSQGQi"

bot = Bot(TOKEN)
dp = Dispatcher()
crypto = AioCryptoPay(token=CRYPTO_TOKEN, network=Networks.MAIN_NET)

# Словарь для сохранения ID счета пользователя: {user_id: invoice_id}
user_invoices = {}

def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Услуги (Аккаунты)", callback_data="services")
    kb.button(text="⚙️ Настройки", callback_data="settings")
    kb.row(InlineKeyboardButton(text="💬 Поддержка", url="https://t.me/svekla_wow"))
    kb.adjust(2, 1)
    return kb.as_markup()

def settings_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🇷🇺 Русский", callback_data="lang_ru")
    kb.button(text="🇬🇧 English", callback_data="lang_en")
    kb.button(text="🔙 Главное меню", callback_data="home")
    kb.adjust(2, 1)
    return kb.as_markup()

def services_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Аккаунт Россия - 100 руб.", callback_data="item_ru")
    kb.button(text="Аккаунт Казахстан - 200 руб.", callback_data="item_kz")
    kb.button(text="Аккаунт Украина - 250 руб.", callback_data="item_ua")
    kb.button(text="Аккаунт Турция - 150 руб.", callback_data="item_tr")
    kb.button(text="🔙 Главное меню", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()

@dp.message(CommandStart())
async def start(message: Message):
    user_invoices[message.from_user.id] = None
    await message.answer(
        "<b>Добро пожаловать в @svekla_shop_bot!</b>\n\n"
        "Выберите нужный раздел:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@dp.callback_query()
async def callback_handler(call: CallbackQuery):
    data = call.data
    user_id = call.from_user.id

    if data in ["home", "main_menu"]:
        await call.message.edit_text(
            "<b>Добро пожаловать в @svekla_shop_bot!</b>\n\n"
            "Выберите нужный раздел:",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )

    elif data == "services":
        await call.message.edit_text(
            "🛒 <b>Услуги (Аккаунты)</b>\n\n"
            "Выберите интересующий вас вариант:",
            reply_markup=services_menu(),
            parse_mode="HTML"
        )

    elif data == "settings":
        await call.message.edit_text(
            "⚙️ <b>Настройки</b>\n\n"
            "Выберите язык интерфейса:",
            reply_markup=settings_menu(),
            parse_mode="HTML"
        )

    elif data.startswith("item_"):
        items = {
            "item_ru": {"name": "Аккаунт Россия", "price": 100},
            "item_kz": {"name": "Аккаунт Казахстан", "price": 200},
            "item_ua": {"name": "Аккаунт Украина", "price": 250},
            "item_tr": {"name": "Аккаунт Турция", "price": 150}
        }
        item = items.get(data)
        if not item:
            return

        item_name = item["name"]
        price_rub = item["price"]

        try:
            invoice = await crypto.create_invoice(
                asset='USDT',
                fiat='RUB',
                accepted_assets=['USDT', 'TON', 'BTC', 'LTC', 'ETH', 'BNB', 'TRX', 'USDC'],
                amount=price_rub,
                description=f"Покупка: {item_name} ({price_rub} руб.)"
            )

            user_invoices[user_id] = invoice.invoice_id

            pay_kb = InlineKeyboardBuilder()
            pay_kb.button(text="Оплатить", url=invoice.bot_invoice_url)
            pay_kb.button(text="Проверить оплату", callback_data="check_payment")
            pay_kb.button(text="🔙 Назад к списку", callback_data="services")
            pay_kb.adjust(1, 1, 1)

            await call.message.edit_text(
                f"Вы выбрали: <b>{item_name}</b>\n"
                f"Сумма к оплате: <b>{price_rub} руб.</b>\n\n"
                f"Нажмите кнопку ниже для оплаты через CryptoBot, "
                f"после чего нажмите кнопку проверки.",
                reply_markup=pay_kb.as_markup(),
                parse_mode="HTML"
            )
        except Exception as e:
            await call.answer(f"Ошибка при создании счета: {e}", show_alert=True)

    elif data == "check_payment":
        invoice_id = user_invoices.get(user_id)
        
        if not invoice_id:
            await call.answer("У вас нет активных счетов для проверки.", show_alert=True)
            return
            
        try:
            invoices = await crypto.get_invoices(invoice_ids=invoice_id)
            invoice = invoices[0] if invoices else None
            
            if invoice and invoice.status == "paid":
                success_kb = InlineKeyboardBuilder()
                success_kb.button(text="Написать в поддержку", url="https://t.me/svekla_www")
                success_kb.button(text="В главное меню", callback_data="home")
                success_kb.adjust(1, 1)
                
                user_invoices.pop(user_id, None)
                
                await call.message.edit_text(
                    "<b>Успешно!</b>\n\n"
                    "Оплата получена!\n\n"
                    "Пожалуйста, отпишите в техподдержку (@svekla_www) для получения номера и кода.",
                    reply_markup=success_kb.as_markup(),
                    parse_mode="HTML"
                )
            else:
                await call.answer("Оплата не найдена или еще не поступила. Попробуйте позже.", show_alert=True)
        except Exception as e:
            await call.answer("Ошибка при проверке платежа. Попробуйте позже.", show_alert=True)

    elif data.startswith("lang_"):
        lang = "Русский 🇷🇺" if data.endswith("ru") else "English 🇬🇧"
        await call.answer(f"Язык изменен на: {lang}", show_alert=True)

    try:
        await call.answer()
    except:
        pass


# ==========================================
# Код для поддержания работы на Render
# ==========================================
async def handle_request(request):
    return web.Response(text="Bot is running", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_request)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    try:
        await start_web_server()
        await dp.start_polling(bot)
    finally:
        await crypto.close()

if name == "main":
    asyncio.run(main())

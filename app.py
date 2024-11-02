import os
import telebot
import requests
import json
from dotenv import load_dotenv 
from telebot import types  
from config import keys


load_dotenv() 


class APIException(Exception):
    pass


class CurrencyConverter:
    @staticmethod
    def convert(quote: str, base: str, amount: str):
        amount = float(amount)
        if amount <= 0:
            raise APIException('Убедитесь что число переводимой валюты больше 0!')
        if quote == base:
            raise APIException(f'Невозможно сконвертировать одинаковые валюты {base}')
        try:
            quote_ticker = keys[quote]
        except KeyError:
            raise APIException(f'Не удалось обработать валюту {quote}.')
        try:
            base_ticker = keys[base]
        except KeyError:
            raise APIException(f'Не удалось обработать валюту {base}.')
        try:
            r = requests.get(f'https://min-api.cryptocompare.com/data/price?fsym={quote_ticker}&tsyms={base_ticker}')
            total_base = json.loads(r.content)[keys[base]]
        except Exception as e:
            raise APIException(f'Не удалось получить данные для конвертации: {e}')
        
        return total_base * amount


TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)


user_data = {} 


def create_currency_buttons():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for currency in keys.keys():
        markup.add(types.KeyboardButton(currency))
    markup.add(types.KeyboardButton("Отмена"))
    return markup


def create_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("/start"))
    markup.add(types.KeyboardButton("/help"))
    markup.add(types.KeyboardButton("/values"))
    return markup

@bot.message_handler(commands=['start'])
def start(message: telebot.types.Message):
    text = f'{message.chat.username}, добро пожаловать в приложение "Конвертер валют"! \nВыберите валюту для конвертации.'
    bot.send_message(message.chat.id, text, reply_markup=create_currency_buttons())
    user_data[message.chat.id] = {}

@bot.message_handler(commands=['help'])
def help_command(message: telebot.types.Message):
    text = 'Чтобы начать конвертацию, выберите валюту, затем введите сумму для конвертации.'
    bot.reply_to(message, text, reply_markup=create_main_menu())

@bot.message_handler(commands=['values'])
def values(message: telebot.types.Message):
    text = 'Доступные валюты:'
    for key in keys.keys():
        text = '\n'.join((text, key,))
    bot.reply_to(message, text, reply_markup=create_main_menu())

@bot.message_handler(content_types=['text'])
def handle_currency_selection(message: telebot.types.Message):
    chat_id = message.chat.id


    if chat_id not in user_data:
        user_data[chat_id] = {}

    selected_currency = message.text.lower()

    if selected_currency in keys:
        if 'quote' not in user_data[chat_id]:
            user_data[chat_id]['quote'] = selected_currency
            text = f'Вы выбрали {selected_currency}. Выберите валюту, в которую хотите конвертировать.'
            bot.send_message(chat_id, text, reply_markup=create_currency_buttons())
        elif 'base' not in user_data[chat_id]:
            user_data[chat_id]['base'] = selected_currency
            text = 'Введите сумму для конвертации:'
            bot.send_message(chat_id, text) 
            bot.send_message(chat_id, "Для отмены введите /start или /help.") 
        else:
            bot.reply_to(message, 'Пожалуйста, введите сумму для конвертации.')

    elif selected_currency == "отмена":
        bot.send_message(chat_id, "Конвертация отменена. Используйте /start для начала.")
        user_data.pop(chat_id, None)  

    elif 'quote' in user_data[chat_id] and 'base' in user_data[chat_id]:
        try:
            amount = float(selected_currency) 
            total_base = CurrencyConverter.convert(user_data[chat_id]['quote'], user_data[chat_id]['base'], amount)
            text = f'{amount} {user_data[chat_id]["quote"]} = {total_base} {user_data[chat_id]["base"]}'
            bot.send_message(chat_id, text, reply_markup=create_main_menu()) 
            del user_data[chat_id] 
        except ValueError:
            bot.reply_to(message, 'Пожалуйста, введите корректное число.')
        except APIException as e:
            bot.reply_to(message, f'Ошибка: {e}')
        except Exception as e:
            bot.reply_to(message, f'Не удалось обработать команду: {e}')
    else:
        bot.reply_to(message, 'Пожалуйста, выберите валюту из списка.')

bot.polling()

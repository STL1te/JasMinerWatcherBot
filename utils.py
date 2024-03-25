import os.path
import sqlite3
import json
import math

from datetime import datetime
from telebot import types

from config import DB_PATH, MINER_DATA_PATH, DEVICES_PER_PAGE
from jasminer_api import JasMinerApi


def db_connect():
    return sqlite3.connect(DB_PATH)


def create_main_menu():
    markup = types.InlineKeyboardMarkup()

    markup.add(types.InlineKeyboardButton(text='Статистика', callback_data='stats:0'))
    markup.add(types.InlineKeyboardButton(text='Устройства', callback_data='dev_list'))

    return markup


def create_stats_menu(user_id, page):
    markup = types.InlineKeyboardMarkup()

    devices, pages = get_devices_pages_total(user_id)

    if pages > 1:
        page_buttons = []

        if page > 0:
            page_buttons.append(types.InlineKeyboardButton(text='<', callback_data=f'update_stats:{page - 1}'))

        if page < pages - 1:
            page_buttons.append(types.InlineKeyboardButton(text='>', callback_data=f'update_stats:{page + 1}'))

        if len(page_buttons):
            markup.row(*page_buttons)

    markup.add(types.InlineKeyboardButton(text='Обновить', callback_data=f'update_stats:{page}'))
    markup.add(types.InlineKeyboardButton(text='Вернуться в главное меню ↩', callback_data='main_menu'))

    return markup


def create_devices_menu(user_id):
    markup = types.InlineKeyboardMarkup()

    with db_connect() as connect:
        sql = """SELECT id, minerName FROM devices WHERE userId = (?)"""
        select_db = connect.cursor().execute(sql, (user_id,))

        for miner_id, minerName in select_db.fetchall():
            markup.add(types.InlineKeyboardButton(text=minerName, callback_data=f'device_{miner_id}_remove'))

    markup.add(types.InlineKeyboardButton(text='Добавить устройство', callback_data='add_device'))
    markup.add(types.InlineKeyboardButton(text='Вернуться в главное меню ↩', callback_data='main_menu'))

    return markup


def get_devices_pages_total(user_id):
    with db_connect() as connect:
        sql = """SELECT COUNT(*) FROM devices WHERE userId = (?)"""
        select_db = connect.cursor().execute(sql, (user_id,))
        total_devices = select_db.fetchone()[0]

    total_pages = math.ceil(total_devices / DEVICES_PER_PAGE)

    return total_devices, total_pages


def check_device(host, user, password):
    api = JasMinerApi(host, user, password)
    return api.is_connected


def add_device(user_id, name, host, user, password):
    if check_device(host, user, password):
        with db_connect() as connect:
            sql = """INSERT INTO devices(userId,minerName,host,user,password)
                  VALUES(?,?,?,?,?)"""
            connect.cursor().execute(sql, (user_id, name, host, user, password))
            connect.commit()
        return True
    else:
        return False


def remove_device(user_id, dev_id):
    with db_connect() as connect:
        sql = """DELETE FROM devices WHERE userId=(?) AND id=(?)"""
        connect.cursor().execute(sql, (user_id, dev_id))
        connect.commit()


def get_stats_message(user_id, page):
    message = datetime.now().strftime("%d.%m.%y %H:%M:%S\n\n")

    if not os.path.exists(MINER_DATA_PATH):
        message += 'Устройства не добавлены или статистика не готова...'
        return message

    with open(MINER_DATA_PATH, 'r') as f:
        miners_data = json.load(f)

    offset = page * DEVICES_PER_PAGE

    with db_connect() as connect:
        sql = f"""SELECT id, minerName FROM devices WHERE userId = (?) LIMIT {DEVICES_PER_PAGE} OFFSET {offset}"""
        select_db = connect.cursor().execute(sql, (user_id,))

        for miner_id, minerName in select_db.fetchall():
            miner_data = miners_data.get(str(miner_id))

            message += f'<b>{minerName}</b>\n'

            if miner_data is None:
                message += 'Статистика недоступна!'
            else:
                # message += f"<b>Model:</b> {miner_data['minerModel']}\n"
                # message += f"<b>Firmware</b>: {miner_data['firmwareVersion']}\n"
                message += f"<b>Uptime</b>: {miner_data['uptime']}\n"
                message += f"<b>Hashrate (AVG)</b>: {miner_data['hashrate']} ({miner_data['avg_hashrate']})\n"

                fan_messages = []
                for fan in miner_data['fans']:
                    fan_messages.append(f"{fan[0]} ({fan[1]})")
                message += f"<b>Fans</b>: {' | '.join(fan_messages)}\n"

                board_messages = []
                for board in miner_data['boards_stats']:
                    board_temps = '-'.join(str(temp) for temp in board[1])
                    if max(board[1]) > 58:
                        board_temps += ' 🔥'

                    asic_stat_message = ''
                    for asic_stat in board[0]:
                        if asic_stat == 'O':
                            asic_stat_message += '🟢'
                        else:
                            asic_stat_message += '🔴'
                    board_messages.append(f"{asic_stat_message} | {board_temps}")
                board_messages_str = '\n'.join(board_messages)
                message += f"<b>Boards:</b> {board_messages_str}"

            message += '\n------------------------\n'

    return message

import os.path
import sqlite3
import json
from datetime import datetime
from telebot import types

from config import DB_PATH, MINER_DATA_PATH
from jasminer_api import JasMinerApi


class MenuTypes:
    MAIN_MENU = 0
    STATS = 1
    ADD_DEVICE = 2


def db_connect():
    return sqlite3.connect(DB_PATH)


def create_menu_simple(type_menu):
    markup = types.InlineKeyboardMarkup()

    if type_menu == MenuTypes.MAIN_MENU:
        markup.add(types.InlineKeyboardButton(text='Статистика', callback_data='stats'))
        markup.add(types.InlineKeyboardButton(text='Устройства', callback_data='dev_list'))

    if type_menu == MenuTypes.STATS:
        markup.add(types.InlineKeyboardButton(text='Обновить', callback_data='update_stats'))
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


def get_stats_message(user_id):
    message = datetime.now().strftime("%d.%m.%y %H:%M:%S\n\n")

    if not os.path.exists(MINER_DATA_PATH):
        message += 'Устройства не добавлены или статистика не готова...'
        return message

    with open(MINER_DATA_PATH, 'r') as f:
        miners_data = json.load(f)

    with db_connect() as connect:
        sql = """SELECT id, minerName FROM devices WHERE userId = (?)"""
        select_db = connect.cursor().execute(sql, (user_id,))

        for miner_id, minerName in select_db.fetchall():
            miner_data = miners_data.get(str(miner_id))

            message += f'<b>{minerName}</b>\n'

            if miner_data is None:
                message += 'Stats not available!'
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

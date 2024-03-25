import traceback
import telebot
from telebot import custom_filters
from telebot.handler_backends import State, StatesGroup

from config import BOT_TOKEN, BOT_OWNER_ID
from utils import MenuTypes, get_stats_message, create_menu_simple,\
    create_devices_menu, add_device, remove_device, check_device

bot = telebot.TeleBot(BOT_TOKEN)
bot.enable_saving_states()
bot.add_custom_filter(custom_filters.StateFilter(bot))


class AddDeviceStates(StatesGroup):
    name = State()
    host = State()
    user = State()
    password = State()


def check_user_access(message):
    if message.chat.id != BOT_OWNER_ID:
        bot.send_message(message.chat.id, "Доступ закрыт!")
        return False
    return True

@bot.message_handler(commands=["menu"])
def menu(message):
    if not check_user_access(message):
        return
    bot.send_message(message.chat.id, "Главное меню 📄", reply_markup=create_menu_simple(MenuTypes.MAIN_MENU))


@bot.message_handler(state="*", commands=["cancel"])
def any_state(message):
    if not check_user_access(message):
        return
    bot.send_message(message.chat.id, "Действие отменено.")
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        bot.delete_messages(message.chat.id, data['remove_messages'])
    bot.delete_state(message.from_user.id, message.chat.id)


@bot.message_handler(state=AddDeviceStates.name)
def process_add_dev_name(message):
    bot_msg = bot.send_message(message.chat.id, 'Введите адрес хоста (например 192.168.1.25):')
    bot.set_state(message.from_user.id, AddDeviceStates.host, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['name'] = message.text
        data['remove_messages'].append(message.id)
        data['remove_messages'].append(bot_msg.id)


@bot.message_handler(state=AddDeviceStates.host)
def process_add_dev_host(message):
    bot_msg = bot.send_message(message.chat.id, 'Введите логин (стандартный - root):')
    bot.set_state(message.from_user.id, AddDeviceStates.user, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['host'] = message.text
        data['remove_messages'].append(message.id)
        data['remove_messages'].append(bot_msg.id)


@bot.message_handler(state=AddDeviceStates.user)
def process_add_dev_user(message):
    bot_msg = bot.send_message(message.chat.id, 'Введите пароль (стандартный - root):')
    bot.set_state(message.from_user.id, AddDeviceStates.password, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['user'] = message.text
        data['remove_messages'].append(message.id)
        data['remove_messages'].append(bot_msg.id)


@bot.message_handler(state=AddDeviceStates.password)
def process_add_dev_password(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['remove_messages'].append(message.id)
        minerName, host, user, password = data['name'], data['host'], data['user'], message.text

        try:
            if not check_device(host, user, password):
                bot.send_message(message.chat.id, 'Не правильные логин/пароль или устройство не доступно!')
            else:
                add_device(message.from_user.id, minerName, host, user, password)

                bot.send_message(message.chat.id, 'Устройство успешно добавлено!')
                bot.edit_message_text(chat_id=message.chat.id, message_id=data['message_to_edit'], text="Устройства",
                                  reply_markup=create_devices_menu(message.chat.id))
        except Exception as e:
            msg = 'Устройство не добавлено!\n'
            msg += telebot.formatting.hcode(str(e))
            bot.send_message(message.chat.id, msg, parse_mode='html')

        bot.delete_messages(message.chat.id, data['remove_messages'])
    bot.delete_state(message.from_user.id, message.chat.id)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if not check_user_access(call.message):
        return

    if call.data == 'main_menu':
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Главное меню",
                              reply_markup=create_menu_simple(MenuTypes.MAIN_MENU))

    if call.data in ('stats', 'update_stats'):
        stats_message = get_stats_message(call.message.chat.id)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=stats_message,
                              parse_mode='HTML', reply_markup=create_menu_simple(MenuTypes.STATS))

    if call.data == 'dev_list':
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Устройства",
                              reply_markup=create_devices_menu(call.message.chat.id))

    if call.data == 'add_device':
        bot.set_state(call.message.chat.id, AddDeviceStates.name, call.message.chat.id)

        with bot.retrieve_data(call.message.chat.id, call.message.chat.id) as data:
            data['message_to_edit'] = call.message.message_id
            data['remove_messages'] = [bot.send_message(chat_id=call.message.chat.id, text="Введите имя устройства:").id]

    if 'device_' in call.data:
        _, dev_id, action = call.data.split('_')
        if action == 'remove':
            remove_device(call.message.chat.id, int(dev_id))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Устройства",
                              reply_markup=create_devices_menu(call.message.chat.id))

def main():
    bot.infinity_polling(skip_pending=True)


if __name__ == '__main__':
    main()

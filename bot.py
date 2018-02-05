from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)
import logging
import secrets

import database_manager
import datetime

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# ==============================================
# ================== PROPERTIES ================
# ==============================================

DIRECTION, DATETIME, DESTINATION, PASSENGERS, CONTACT = range(5)

F_DIRECTION, F_SELECT_RIDE = range(2)

M_RIDES = 0

share_or_find_keyboard = [['Создать поездку', 'Найти поездку'], ['Мои поездки']]
direction_keyboard = [['Из ПК', 'В ПК'], ['Главное меню']]

contact_keyboard_button = KeyboardButton(text="Показать телефон", request_contact=True)
contact_keyboard = [[ contact_keyboard_button ], ['Пропустить']]

# ==============================================
# =============== HELPER METHODS ===============
# ==============================================
def facts_to_str(user_data):
    facts = list()

    for key, value in user_data.items():
        facts.append('{} - {}'.format(key, value))

    return "\n".join(facts).join(['\n', '\n'])

def safe_cast(val, to_type, default=None):
    try:
        return to_type(val)
    except (ValueError, TypeError):
        return default


# ==============================================
# =========== CONVERSATION HANDLERS ============
# ==============================================


def start_sharing(bot, update, user_data):

    update.message.reply_text('Создание поездки. Выберите направление, пожалуйста',
                              reply_markup=ReplyKeyboardMarkup(direction_keyboard))

    user_data['isSharing'] = True
    return DIRECTION

def start_finding(bot, update, user_data):

    update.message.reply_text('Найти поездки. Выберите направление, пожалуйста',
                              reply_markup=ReplyKeyboardMarkup(direction_keyboard))

    user_data['isSharing'] = False
    return F_DIRECTION

def show_my_rides(bot, update, user_data):

    my_rides = database_manager.get_my_rides_from_table(update.message.from_user.id)

    if len(my_rides) == 0:
        update.message.reply_text('Вы пока не создали ни одной поездки',
                                  reply_markup=ReplyKeyboardMarkup(share_or_find_keyboard))
        user_data.clear()

        return ConversationHandler.END

    outstr = 'Созданные Вами поездки:\n'

    for index in range(len(my_rides)):
        ride = my_rides[index]

        num = index + 1

        datetimeinfo = ride['ride_datetime']

        passengers_info = str(ride['ride_passengers'] - ride['requests_rides']) + ' из ' + str(
            ride['ride_passengers']) + ' мест доступно'

        outstr += str(num) + '. ' + ride['ride_destination'] + ', ' + \
                  ' ' + datetimeinfo

        if ride['ride_passengers'] != 0:
            outstr += ', ' + passengers_info + '\n'


    user_data['my_rides'] = my_rides

    update.message.reply_text(outstr,
                              reply_markup=ReplyKeyboardMarkup([['Удалить мои поездки'], ['Главное меню']]))

    return M_RIDES

def delete_my_rides(bot, update, user_data):

    database_manager.delete_my_rides_from_table(update.message.from_user.id)

    update.message.reply_text('Ваши поездки удалены...',
                              reply_markup=ReplyKeyboardMarkup(share_or_find_keyboard))
    user_data.clear()

    return ConversationHandler.END



# ------------- CREATE RIDE -----------------

def direction(bot, update, user_data):
    text = update.message.text
    user_data['ride_direction'] = text

    if user_data['isSharing'] == True:
        update.message.reply_text('Введите дату и время в фомате: 01.01.2018 11:11, или нажмите кнопку'
                                  ' "Ближайшее время"',
                                  reply_markup=ReplyKeyboardMarkup([['Ближайшее время']]))

        del user_data['isSharing']
        return DATETIME
    else:
        del user_data['isSharing']
        return list_all_shares(bot, update, user_data)

def setdatetime(bot, update, user_data):
    text = update.message.text
    user_data['ride_datetime'] = text

    place_text = 'назначения' if user_data['ride_direction'] == 'Из ПК' else 'отправления'

    update.message.reply_text('Введите примерный пункт ' + place_text + ' (например: Тушинская, Глобус, Строгино и тд),'
                              ' или нажмите на одну из кнопок ниже',
                              reply_markup = ReplyKeyboardMarkup([['Москва', 'Нахабино', 'Глобус']]))
    return DESTINATION

def destination(bot, update, user_data):
    text = update.message.text
    user_data['ride_destination'] = text

    update.message.reply_text('Выберите количество пассажиров, которое можете подвезти',
                              reply_markup=ReplyKeyboardMarkup([['1', '2', '3', '4'],['4+']]))
    return PASSENGERS

def passengers(bot, update, user_data):
    text = update.message.text
    user_data['ride_passengers'] = safe_cast(text, int, 0)


    update.message.reply_text('Поделитесь своим номером телефона, по которому Вам смогут позвонить соседи,'
                              'или нажмите "Пропустить"',
                              reply_markup = ReplyKeyboardMarkup(contact_keyboard))

    return CONTACT

def contact(bot, update, user_data):
    user_contact = update.message.contact

    logging.info("Contact is {}".format(user_contact))

    user_data['user_phonenumber'] = user_contact['phone_number']

    return create_ride(update, user_data)

def skip_contact(bot, update, user_data):

    return create_ride(update, user_data)


def check_for_username(update, user_data):
    print(update.message.from_user)

    print(update.message.from_user.username != None)

    return update.message.from_user.username != None




def create_ride(update, user_data):

    print(update.message.from_user)

    if check_for_username(update, user_data) == False and 'user_phonenumber' not in user_data.keys():
        update.message.reply_text('Не удалось создать поездку (нет контактов). Расшарьте номер телефона, '
                                  'либо добавьте имя пользователя в настройках Телеграм:\n'
                                  '"Настройки -> Выбрать имя пользователя"',
                                  reply_markup=ReplyKeyboardMarkup([[ contact_keyboard_button ], ['Отменить создание']]))

        return CONTACT


    ride = {}

    for key,val in user_data.items():
        ride[key] = val

    ride['user_id'] = update.message.from_user.id
    ride['user_name'] = update.message.from_user.username
    ride['requests_rides'] = 0


    max_id = database_manager.get_max_id_from_table()

    if max_id == None:
        max_id = 1

    ride_id = max_id + 1

    if 'user_phonenumber' in ride.keys():
        phonenumber = ride['user_phonenumber']
    else:
        phonenumber = 'no phone number'

    database_manager.insert_to_db(ride_id,
                 ride['ride_direction'],
                 ride['ride_destination'],
                 ride['ride_datetime'],
                 ride['ride_passengers'],
                 ride['requests_rides'],
                 phonenumber,
                 ride['user_id'],
                 ride['user_name'],
                 str(datetime.datetime.now()))



    outstr = 'Вы создали поездку {} с параметрами:\n'.format(ride['ride_direction'])

    place_text = 'назначения' if user_data['ride_direction'] == 'Из ПК' else 'отправления'

    outstr += 'Пункт {}: {}'.format(place_text, ride['ride_destination']) + '\n'

    outstr += 'Время отправления: {}'.format(ride['ride_datetime']) + '\n'

    if ride['ride_passengers'] != 0:
        outstr += 'Пассажиров: {}'.format(ride['ride_passengers'])

    update.message.reply_text(outstr, reply_markup=ReplyKeyboardMarkup(share_or_find_keyboard))


    user_data.clear()

    return ConversationHandler.END


# -------------- FIND RIDE --------------

def list_all_shares(bot, update, user_data):

    user_id = update.message.from_user.id

    suitable_rides = database_manager.get_rides_from_table(user_id, user_data['ride_direction'])

    print(suitable_rides)

    outstr = ''
    if len(suitable_rides) > 0:
        outstr += 'Выберите поездку (введите номер или нажмите на одну из кнопок):\n'

        keyboard_row = []

        keyboard = []

        for index in range(len(suitable_rides)):
            ride = suitable_rides[index]

            num = index + 1

            datetimeinfo = ride['ride_datetime']

            seats_count = max(0, ride['ride_passengers'] - ride['requests_rides'])

            passengers_info = str(seats_count) + ' из ' + str(ride['ride_passengers']) + ' мест доступно'

            outstr += str(num) + '. ' + ride['ride_destination'] + ', ' +\
                      ' ' + datetimeinfo

            if ride['ride_passengers'] != 0:
                outstr += ', ' + passengers_info + '\n'

            keyboard_row.append(str(num))

            if num % 4 == 0:
                keyboard.append(keyboard_row)
                keyboard_row = []

        keyboard.append(keyboard_row)

        update.message.reply_text(outstr, reply_markup=ReplyKeyboardMarkup(keyboard))
        user_data['rides_for_select'] = suitable_rides

        print('suitable_rides = ', suitable_rides)

        return F_SELECT_RIDE
    else:
        outstr = "Нет созданных поездок {}".format(user_data['ride_direction'])

        update.message.reply_text(outstr, reply_markup=ReplyKeyboardMarkup(share_or_find_keyboard))
        user_data.clear()

        return ConversationHandler.END


def select_ride(bot, update, user_data):

    text = update.message.text

    suitable_rides = user_data['rides_for_select']

    selected_ride = suitable_rides[int(text) - 1]

    outstr = 'Вы выбрали поездку # {}'.format(text) + '\n'

    place_text = 'назначения' if user_data['ride_direction'] == 'Из ПК' else 'отправления'

    outstr += 'Пункт {}: {}'.format(place_text, selected_ride['ride_destination']) + '\n'

    outstr += 'Время отправления: {}'.format(selected_ride['ride_datetime']) + '\n'

    if selected_ride['user_name'] != 'None':
        outstr += 'Телеграм аккаунт водителя для связи: @{}'.format(selected_ride['user_name']) + '\n'

    if selected_ride['user_phonenumber'] != 'no phone number':
        phone_number =  selected_ride['user_phonenumber']
        if phone_number[:1] != '+':
            phone_number = '+' + phone_number
        outstr += 'Телефон водителя для связи: {}'.format(phone_number) + '\n'


    if selected_ride['ride_passengers'] != 0:
        database_manager.increment_requests_count(selected_ride['ride_id'], selected_ride['requests_rides'] + 1)

        seats_count = max(0, selected_ride['ride_passengers'] - selected_ride['requests_rides'])

        passengers_info = str(seats_count) + ' из ' + str(selected_ride['ride_passengers'])

        outstr += 'Мест свободно: {}'.format(passengers_info)



    update.message.reply_text(outstr, reply_markup=ReplyKeyboardMarkup(share_or_find_keyboard))

    user_data.clear()

    return ConversationHandler.END


# --------------- COMMANDS HANDLERS --------------

def start(bot, update):
    """Send a message when the command /start is issued."""

    reply_keyboard = share_or_find_keyboard
    user = update.message.from_user
    update.message.reply_text('Приветствую, ' + user.first_name + '!\n'
                              'Я - бот, который поможет Вам найти нужную поездку, или'
                              ' подвезти соседей :)',
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False))


def help(bot, update):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Введите команду /start для начала работы с ботом')

def echo(bot, update):
    """Echo the user message."""
    update.message.reply_text('Введите команду /start для начала работы с бото')

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)

def done(bot, update, user_data):

    update.message.reply_text('Отменено', reply_markup=ReplyKeyboardMarkup(share_or_find_keyboard))

    user_data.clear()
    return ConversationHandler.END

def cancel(bot, update):
    update.message.reply_text('Отменено', reply_markup=ReplyKeyboardMarkup(share_or_find_keyboard))
    return ConversationHandler.END


# ==============================================
# ==================== MAIN ====================
# ==============================================

def main():

    # ---- USE ONLY ONCE TO CREATE AND CONFIGURE DB ----
    # database_manager.create_db()
    # database_manager.create_db_table()
    # --------------------------------------------------

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(secrets.token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    ride_share_conv_handler = ConversationHandler(
        entry_points=[RegexHandler('^Создать поездку$', start_sharing, pass_user_data=True)],

        states={
            DIRECTION: [RegexHandler('^(Из ПК|В ПК)$', direction, pass_user_data=True)],
            DATETIME: [MessageHandler(Filters.text, setdatetime, pass_user_data=True)],
            DESTINATION: [MessageHandler(Filters.text, destination, pass_user_data=True)],
            PASSENGERS: [MessageHandler(Filters.text, passengers, pass_user_data=True)],
            CONTACT: [MessageHandler(Filters.contact, contact, pass_user_data=True),
                      CommandHandler('skip', skip_contact, pass_user_data=True),
                      RegexHandler('^Пропустить$', skip_contact, pass_user_data=True)]

        },

        fallbacks=[CommandHandler('cancel', cancel),
                   RegexHandler('^Главное меню$', done, pass_user_data=True),
                   RegexHandler('^Отменить создание$', done, pass_user_data=True)]
    )

    dp.add_handler(ride_share_conv_handler)

    ride_find_conv_handler = ConversationHandler(
        entry_points=[RegexHandler('^Найти поездку$', start_finding, pass_user_data=True)],

        states={
            F_DIRECTION: [RegexHandler('^(Из ПК|В ПК)$', direction, pass_user_data=True)],
            F_SELECT_RIDE: [MessageHandler(Filters.text, select_ride, pass_user_data=True)]

        },

        fallbacks=[CommandHandler('cancel', cancel),
                   RegexHandler('^Главное меню$', done, pass_user_data=True)]
    )

    dp.add_handler(ride_find_conv_handler)

    my_rides_conv_handler = ConversationHandler(
        entry_points=[RegexHandler('^Мои поездки$', show_my_rides, pass_user_data=True)],

        states={
            M_RIDES: [RegexHandler('^Удалить мои поездки$', delete_my_rides, pass_user_data=True)],


        },

        fallbacks=[CommandHandler('cancel', cancel),
                   RegexHandler('^Главное меню$', done, pass_user_data=True)]
    )

    dp.add_handler(my_rides_conv_handler)


    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    # dp.add_handler(CommandHandler("help", help))

    # on noncommand i.e message - echo the message on Telegram
    # dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
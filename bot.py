from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)
import logging
import secrets

import database_manager

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# ==============================================
# ================== PROPERTIES ================
# ==============================================

DIRECTION, DATETIME, DESTINATION, PASSENGERS, CONTACT = range(5)

F_DIRECTION, F_SELECT_RIDE = range(2)

share_or_find_keyboard = [['Создать поездку', 'Найти поездку']]
direction_keyboard = [['Из ПК', 'В ПК'], ['Главное меню']]


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

def start(bot, update):
    """Send a message when the command /start is issued."""

    reply_keyboard = share_or_find_keyboard
    user = update.message.from_user
    update.message.reply_text('Приветствую, ' + user.first_name + '!\n'
                              'Я - бот, который поможет Вам найти нужную поездку, или'
                              ' подвезти соседей :)',
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False))

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

def datetime(bot, update, user_data):
    text = update.message.text
    user_data['ride_datetime'] = text

    update.message.reply_text('Введите примерный пункт назначения (например: Тушинская, Глобус, Метро и тд),'
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

    location_keyboard = KeyboardButton(text="Send Contact", request_contact = True)

    update.message.reply_text('Поделитесь своим номером телефона, по которому Вам смогут позвонить соседи,'
                              'или нажмите "Пропустить"',
                              reply_markup = ReplyKeyboardMarkup([[ location_keyboard ], ['Пропустить']]))

    return CONTACT

def contact(bot, update, user_data):
    user_contact = update.message.contact

    logging.info("Contact is {}".format(user_contact))

    user_data['user_phonenumber'] = user_contact['phone_number']

    update.message.reply_text("Вы создали поездку с параметрами:"
                              "{} \n Спасибо! Ожидайте обращений соседей :)".format(facts_to_str(user_data)),
                              reply_markup=ReplyKeyboardMarkup(share_or_find_keyboard))

    return create_ride(update, user_data)

def skip_contact(bot, update, user_data):
    update.message.reply_text("Вы создали поездку с параметрами:"
                              "{} \n Спасибо! Ожидайте обращений соседей :)".format(facts_to_str(user_data)),
                              reply_markup=ReplyKeyboardMarkup(share_or_find_keyboard))


    return create_ride(update, user_data)




def create_ride(update, user_data):

    print(update.message.from_user)

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
                 ride['user_name'])

    user_data.clear()

    return ConversationHandler.END


# -------------- FIND RIDE --------------

def list_all_shares(bot, update, user_data):

    suitable_rides = database_manager.get_rides_from_table(user_data['ride_direction'])

    print(suitable_rides)

    outstr = ''
    if len(suitable_rides) > 0:
        outstr += 'Выберите поездку (введите номер или нажмите на одну из кнопок):\n'

        keyboard = []

        for index in range(len(suitable_rides)):
            ride = suitable_rides[index]

            num = index + 1

            datetimeinfo = ride['ride_datetime']

            passengers_info = str(ride['ride_passengers'] - ride['requests_rides']) + ' из ' + str(ride['ride_passengers']) + ' мест доступно'

            outstr += str(num) + '. ' + ride['ride_destination'] + ', ' +\
                      ' ' + datetimeinfo

            if ride['ride_passengers'] != 0:
                outstr += ', ' + passengers_info + '\n'

            keyboard.append(str(num))

        update.message.reply_text(outstr, reply_markup=ReplyKeyboardMarkup([keyboard]))
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

    outstr += 'Пункт назначения: {}'.format(selected_ride['ride_destination']) + '\n'

    outstr += 'Время отправления: {}'.format(selected_ride['ride_datetime']) + '\n'

    outstr += 'Телеграм аккаунт водителя для связи: @{}'.format(selected_ride['user_name']) + '\n'

    if selected_ride['user_phonenumber'] != 'no phone number':
        phone_number =  selected_ride['user_phonenumber']
        if phone_number[:1] != '+':
            phone_number = '+' + phone_number
        outstr += 'Телефон водителя для связи: {}'.format(phone_number) + '\n'


    passengers_info = str(selected_ride['ride_passengers'] - selected_ride['requests_rides']) + ' из ' + str(selected_ride['ride_passengers'])

    if selected_ride['ride_passengers'] != 0:
        outstr += 'Мест свободно: {}'.format(passengers_info)

    update.message.reply_text(outstr, reply_markup=ReplyKeyboardMarkup(share_or_find_keyboard))

    user_data.clear()

    return ConversationHandler.END


# --------------- COMMANDS HANDLERS --------------
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
    # create_db()
    # create_db_table()
    # --------------------------------------------------

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(secrets.token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    ride_share_conv_handler = ConversationHandler(
        entry_points=[RegexHandler('^Создать поездку$', start_sharing, pass_user_data=True)],

        states={
            DIRECTION: [RegexHandler('^(Из ПК|В ПК)$', direction, pass_user_data=True)],
            DATETIME: [MessageHandler(Filters.text, datetime, pass_user_data=True)],
            DESTINATION: [MessageHandler(Filters.text, destination, pass_user_data=True)],
            PASSENGERS: [MessageHandler(Filters.text, passengers, pass_user_data=True)],
            CONTACT: [MessageHandler(Filters.contact, contact, pass_user_data=True),
                      CommandHandler('skip', skip_contact, pass_user_data=True),
                      RegexHandler('^Пропустить$', skip_contact, pass_user_data=True)]

        },

        fallbacks=[CommandHandler('cancel', cancel),
                   RegexHandler('^Главное меню$', done, pass_user_data=True)]
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
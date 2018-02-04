from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)
import logging
import secrets

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# PROPERTIES
DIRECTION, DATETIME, DESTINATION, PASSENGERS, CONTACT = range(5)

F_DIRECTION, F_SELECT_RIDE = range(2)

share_or_find_keyboard = [['Share your ride', 'Find ride']]
direction_keyboard = [['From PK', 'To PK']]

rides_dict = {}

# HELPER METHODS
def facts_to_str(user_data):
    facts = list()

    for key, value in user_data.items():
        facts.append('{} - {}'.format(key, value))

    return "\n".join(facts).join(['\n', '\n'])


# CONVERSATION HANDLERS
def start(bot, update):
    """Send a message when the command /start is issued."""

    reply_keyboard = share_or_find_keyboard
    user = update.message.from_user
    update.message.reply_text('Welcome, ' + user.first_name + '! I\'m bot helping '
                              'you to find ride you need, or'
                              ' to share your ride with your neighbours',
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False))

def start_sharing(bot, update, user_data):
    """Send a message when the command /start is issued."""

    update.message.reply_text('Create share: Select direction please',
                              reply_markup=ReplyKeyboardMarkup(direction_keyboard))

    user_data['isSharing'] = True
    return DIRECTION

def start_finding(bot, update, user_data):
    """Send a message when the command /start is issued."""

    update.message.reply_text('Finding shares: Select direction please',
                              reply_markup=ReplyKeyboardMarkup(direction_keyboard))

    user_data['isSharing'] = False
    return F_DIRECTION

def direction(bot, update, user_data):
    text = update.message.text
    user_data['ride_direction'] = text

    if user_data['isSharing'] == True:
        update.message.reply_text('Enter date and time please in format: 01.01.2018 11:11',
                                  reply_markup=ReplyKeyboardMarkup([['ближайшее время']]))

        del user_data['isSharing']
        return DATETIME
    else:
        del user_data['isSharing']
        return list_all_shares(bot, update, user_data)

def datetime(bot, update, user_data):
    text = update.message.text
    user_data['ride_datetime'] = text

    update.message.reply_text('Enter your destination (eg: Tushinskaya, Globus)',
                              reply_markup = ReplyKeyboardMarkup([['Moscow', 'Nahabino', 'Globus']]))
    return DESTINATION

def destination(bot, update, user_data):
    text = update.message.text
    user_data['ride_destination'] = text

    update.message.reply_text('Enter passengers count you can drive',
                              reply_markup=ReplyKeyboardMarkup([['1', '2', '3', '4'],['4+']]))
    return PASSENGERS

def passengers(bot, update, user_data):
    text = update.message.text
    user_data['ride_passengers'] = text

    location_keyboard = KeyboardButton(text="Send Contact", request_contact = True)

    update.message.reply_text('Add your contact or enter /skip',
                              reply_markup = ReplyKeyboardMarkup([[ location_keyboard ], ['/skip']]))

    return CONTACT

def contact(bot, update, user_data):
    user_contact = update.message.contact

    logging.info("Contact is {}".format(user_contact))

    user_data['user_phonenumber'] = user_contact['phone_number']

    update.message.reply_text("You've created ride with parameters:"
                              "{}".format(facts_to_str(user_data)),
                              reply_markup=ReplyKeyboardMarkup(share_or_find_keyboard))

    return create_ride(update, user_data)

def skip_contact(bot, update, user_data):
    update.message.reply_text("You've created ride with parameters:"
                              "{}".format(facts_to_str(user_data)),
                              reply_markup=ReplyKeyboardMarkup(share_or_find_keyboard))


    return create_ride(update, user_data)


def create_ride(update, user_data):

    print(rides_dict)
    print(update.message.from_user)

    ride = {}

    for key,val in user_data.items():
        ride[key] = val

    ride['user_id'] = update.message.from_user.id
    ride['user_name'] = update.message.from_user.username
    ride['requests_rides'] = 0

    if rides_dict:
        ride_id = max(rides_dict.keys()) + 1
    else:
        ride_id = 1

    rides_dict[ride_id] = ride

    user_data.clear()

    return ConversationHandler.END



# =========== FIND RIDE ========

def list_all_shares(bot, update, user_data):

    suitable_rides = []

    print('rides_dict = ', rides_dict)

    for key, val in rides_dict.items():
        if val['ride_direction'] == user_data['ride_direction']:
            suitable_rides.append(rides_dict[key])

    outstr = ''
    if len(suitable_rides) > 0:
        outstr += 'Select ride:\n'

        keyboard = []

        for index in range(len(suitable_rides)):
            ride = suitable_rides[index]

            num = index + 1

            datetimeinfo = ride['ride_datetime']

            passengers_info = str(int(ride['ride_passengers']) - int(ride['requests_rides'])) + ' из ' + str(ride['ride_passengers']) + ' мест доступно'

            outstr += str(num) + '. ' + ride['ride_destination'] + ', ' +\
                      ' ' + ' ' + datetimeinfo + ', ' +\
                      ' ' + passengers_info + '\n'
            keyboard.append(str(num))

        update.message.reply_text(outstr, reply_markup=ReplyKeyboardMarkup([keyboard]))
        user_data['rides_for_select'] = suitable_rides

        print('suitable_rides = ', suitable_rides)

        return F_SELECT_RIDE
    else:
        outstr = "No rides {}".format(user_data['ride_direction'])

        update.message.reply_text(outstr, reply_markup=ReplyKeyboardMarkup(share_or_find_keyboard))
        user_data.clear()

        return ConversationHandler.END


def select_ride(bot, update, user_data):

    text = update.message.text

    suitable_rides = user_data['rides_for_select']

    selected_ride = suitable_rides[int(text) - 1]

    outstr = 'You selected ride # {}'.format(text) + '\n'

    outstr += 'Destination: {}'.format(selected_ride['ride_destination']) + '\n'

    outstr += 'Start time: {}'.format(selected_ride['ride_datetime']) + '\n'

    outstr += 'Username: @{}'.format(selected_ride['user_name']) + '\n'

    if selected_ride['user_phonenumber'] != None:
        outstr += 'Phone number: +{}'.format(selected_ride['user_phonenumber']) + '\n'

    passengers_info = str(int(selected_ride['ride_passengers']) - int(selected_ride['requests_rides'])) + ' из ' + str(selected_ride['ride_passengers'])

    outstr += 'Мест свободно: {}'.format(passengers_info)

    update.message.reply_text(outstr, reply_markup=ReplyKeyboardMarkup(share_or_find_keyboard))

    user_data.clear()

    return ConversationHandler.END


def done(bot, update, user_data):

    update.message.reply_text("I learned these facts about you:"
                              "{}"
                              "Until next time!".format(facts_to_str(user_data)))

    user_data.clear()
    return ConversationHandler.END

def cancel(bot, update):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('Bye! I hope we can talk again some day.',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


# COMMANDS HANDLERS
def help(bot, update):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Use menu please')

def echo(bot, update):
    """Echo the user message."""
    update.message.reply_text('Use /help command to get help')

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


# MAIN
def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(secrets.token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    ride_share_conv_handler = ConversationHandler(
        entry_points=[RegexHandler('^Share your ride$', start_sharing, pass_user_data=True)],

        states={
            DIRECTION: [RegexHandler('^(From PK|To PK)$', direction, pass_user_data=True)],
            DATETIME: [MessageHandler(Filters.text, datetime, pass_user_data=True)],
            DESTINATION: [MessageHandler(Filters.text, destination, pass_user_data=True)],
            PASSENGERS: [MessageHandler(Filters.text, passengers, pass_user_data=True)],
            CONTACT: [MessageHandler(Filters.contact, contact, pass_user_data=True),
                      CommandHandler('skip', skip_contact, pass_user_data=True)]

        },

        fallbacks=[CommandHandler('cancel', cancel),
                   RegexHandler('^Done$', done, pass_user_data=True)]
    )

    dp.add_handler(ride_share_conv_handler)

    ride_find_conv_handler = ConversationHandler(
        entry_points=[RegexHandler('^Find ride$', start_finding, pass_user_data=True)],

        states={
            F_DIRECTION: [RegexHandler('^(From PK|To PK)$', direction, pass_user_data=True)],
            F_SELECT_RIDE: [MessageHandler(Filters.text, select_ride, pass_user_data=True)]

        },

        fallbacks=[CommandHandler('cancel', cancel),
                   RegexHandler('^Done$', done, pass_user_data=True)]
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
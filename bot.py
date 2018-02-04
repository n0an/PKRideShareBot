from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)
import logging
import secrets

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

DIRECTION, DATETIME, DESTINATION, PASSENGERS, DONE, LISTALLSHARES = range(6)

share_or_find_keyboard = [['Share your ride', 'Find ride']]
direction_keyboard = [['To Moscow', 'To Nahabino'],
                      ['From Moscow', 'From Nahabino']]

rides_dict = {}

def facts_to_str(user_data):
    facts = list()

    for key, value in user_data.items():
        facts.append('{} - {}'.format(key, value))

    return "\n".join(facts).join(['\n', '\n'])

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
    return DIRECTION

def type(bot, update, user_data):
    text = update.message.text
    user_data['isSharing'] = text == share_or_find_keyboard[0][0]

    update.message.reply_text('Select direction please',
                              reply_markup=ReplyKeyboardMarkup(direction_keyboard))
    return DIRECTION

def direction(bot, update, user_data):
    text = update.message.text
    user_data['ride_direction'] = text

    if user_data['isSharing'] == True:
        update.message.reply_text('Enter date and time please in format: 01.01.2018 11:11',
                                  reply_markup=ReplyKeyboardRemove())

        del user_data['isSharing']
        return DATETIME
    else:
        del user_data['isSharing']
        return list_all_shares(bot, update, user_data)

def datetime(bot, update, user_data):
    text = update.message.text
    user_data['ride_datetime'] = text

    update.message.reply_text('Enter your destination metro station (eg: Tushinskaya)')
    return DESTINATION

def destination(bot, update, user_data):
    text = update.message.text
    user_data['ride_destination'] = text

    update.message.reply_text('Enter passengers count you can drive')
    return PASSENGERS

def passengers(bot, update, user_data):
    text = update.message.text
    user_data['ride_passengers'] = text

    update.message.reply_text("You've created ride with parameters:"
                              "{}".format(facts_to_str(user_data)))

    print(rides_dict)
    print(update.message.from_user)

    ride = {}

    for key,val in user_data.items():
        ride[key] = val

    ride['user_id'] = update.message.from_user.id

    if rides_dict:
        ride_id = max(rides_dict.keys()) + 1
    else:
        ride_id = 1

    rides_dict[ride_id] = ride

    user_data.clear()

    return ConversationHandler.END

def list_all_shares(bot, update, user_data):
    update.message.reply_text("You asked to find rides with params:"
                              "{}".format(facts_to_str(user_data)),
                              reply_markup=ReplyKeyboardRemove())

    suitable_rides = []

    print('rides_dict = ', rides_dict)

    for key, val in rides_dict.items():
        if val['ride_direction'] == user_data['ride_direction']:
            suitable_rides.append(rides_dict[key])


    if len(suitable_rides) > 0:
        outstr = ''
        for ride in suitable_rides:
            outstr = ride['ride_destination'] + ' ' + str(ride['user_id']) + '\n'
        update.message.reply_text(outstr)
    else:
        update.message.reply_text("No suitable rides to {}".format(user_data['ride_direction']), reply_markup=ReplyKeyboardRemove())


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


def help(bot, update):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Use menu please')

def echo(bot, update):
    """Echo the user message."""
    update.message.reply_text('Use /help command to get help')

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)

def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(secrets.token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            # TYPE: [RegexHandler('^(Share your ride|Find ride)$', type, pass_user_data=True)],

            DIRECTION: [RegexHandler('^(To Moscow|To Nahabino|From Moscow|From Nahabino)$', direction, pass_user_data=True)],
            DATETIME: [MessageHandler(Filters.text, datetime, pass_user_data=True)],
            DESTINATION: [MessageHandler(Filters.text, destination, pass_user_data=True)],
            PASSENGERS: [MessageHandler(Filters.text, passengers, pass_user_data=True)],

        },

        fallbacks=[CommandHandler('cancel', cancel),
                   RegexHandler('^Done$', done, pass_user_data=True)]
    )

    ride_share_conv_handler = ConversationHandler(
        entry_points=[RegexHandler('^Share your ride$', start_sharing, pass_user_data=True)],

        states={
            DIRECTION: [
                RegexHandler('^(To Moscow|To Nahabino|From Moscow|From Nahabino)$', direction, pass_user_data=True)],
            DATETIME: [MessageHandler(Filters.text, datetime, pass_user_data=True)],
            DESTINATION: [MessageHandler(Filters.text, destination, pass_user_data=True)],
            PASSENGERS: [MessageHandler(Filters.text, passengers, pass_user_data=True)],

        },

        fallbacks=[CommandHandler('cancel', cancel),
                   RegexHandler('^Done$', done, pass_user_data=True)]
    )

    dp.add_handler(ride_share_conv_handler)

    ride_find_conv_handler = ConversationHandler(
        entry_points=[RegexHandler('^Find ride$', start_finding, pass_user_data=True)],

        states={
            DIRECTION: [
                RegexHandler('^(To Moscow|To Nahabino|From Moscow|From Nahabino)$', direction, pass_user_data=True)],
        },

        fallbacks=[CommandHandler('cancel', cancel),
                   RegexHandler('^Done$', done, pass_user_data=True)]
    )

    dp.add_handler(ride_find_conv_handler)


    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    # dp.add_handler(CommandHandler("help", help))
    # dp.add_handler(CommandHandler("subnet", parse_ip,
    #                               pass_args=True,
    #                               pass_chat_data=True))



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
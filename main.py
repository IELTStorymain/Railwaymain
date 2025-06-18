import os
import json
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from scoring import evaluate_score
from messages import messages

# States for conversation handler
ASKING = 0

# Load questions from JSON file
with open("questions.json", "r") as f:
    questions = json.load(f)

# Initialize Flask app
app = Flask(__name__)

# Initialize Telegram application (without polling components)
# The webhook_url and secret_token will be set via setWebhook API call by the user
telegram_app = Application.builder().token(os.environ["BOT_TOKEN"]).updater(None).build()

@app.route("/")
def home():
    return "✅ IELTS Tori Bot is Running 24/7"

@app.route("/webhook", methods=["POST"])
async def webhook():
    """Handle incoming webhook updates from Telegram."""
    try:
        # Get the update from Telegram
        update = Update.de_json(request.get_json(), telegram_app.bot)
        
        # Process the update
        await telegram_app.process_update(update)
        
        return "OK", 200
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return "Error", 500

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks the first question."""
    user_id = update.effective_user.id
    context.user_data["current_question_index"] = 0
    context.user_data["correct_answers"] = 0

    # Determine language based on user\s locale or default to English
    lang = "en" # Default language
    if update.effective_user.language_code and update.effective_user.language_code.startswith("fa"):
        lang = "fa"
    context.user_data["lang"] = lang

    question_data = questions[context.user_data["current_question_index"]]
    options = question_data["options"]
    reply_keyboard = [[option] for option in options]

    await update.message.reply_text(
        messages[f"start_{lang}"],
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    await update.message.reply_text(question_data["question"])
    return ASKING

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles user\s answer, checks correctness, and asks next question or ends quiz."""
    user_answer = update.message.text
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")

    current_question_index = context.user_data.get("current_question_index", 0)
    correct_answers = context.user_data.get("correct_answers", 0)

    if current_question_index < len(questions):
        question_data = questions[current_question_index]
        if user_answer == question_data["answer"]:
            correct_answers += 1
            context.user_data["correct_answers"] = correct_answers

        current_question_index += 1
        context.user_data["current_question_index"] = current_question_index

        if current_question_index < len(questions):
            next_question_data = questions[current_question_index]
            options = next_question_data["options"]
            reply_keyboard = [[option] for option in options]
            await update.message.reply_text(
                next_question_data["question"],
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
            )
            return ASKING
        else:
            # Quiz finished
            level, ielts_band = evaluate_score(correct_answers)
            result_message = messages[f"result_{lang}"].format(level=level, ielts=ielts_band)
            await update.message.reply_text(result_message)
            return ConversationHandler.END
    else:
        # This case should ideally not be reached if conversation flow is correct
        await update.message.reply_text("Something went wrong. Please start again with /start")
        return ConversationHandler.END

# Set up conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={ASKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]},
    fallbacks=[]
)

# Add handlers to the application
telegram_app.add_handler(conv_handler)

# Railway automatically runs the Flask app object named `app`
# No need for app.run() here as Railway handles the server



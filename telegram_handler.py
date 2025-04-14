# telegram_handler.py
from telegram import Update
from telegram.ext import ContextTypes, filters, MessageHandler
from workers import imagegen_worker
from utils import is_addressed_to_bot, is_crypto_request, is_topics_command, is_topic_id_command, is_image_command, is_som_command, is_game_command, is_news_command, logger

def create_message_handler(telegram_agent, tg_plugin):
    """Creates a message handler for the Telegram bot"""
    
    async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handles incoming messages"""
        # Ignore messages from the bot itself
        if update.message.from_user.id == tg_plugin.bot.id:
            logger.info("Ignoring message from the bot itself")
            return

        # Get data from the message
        chat_id = str(update.effective_chat.id)
        message_id = update.message.message_id
        text = update.message.text
        from_user = update.effective_user.username or update.effective_user.first_name
        
        logger.info(f"Received message: {text} from {from_user} in chat {chat_id}")

        is_game, token = is_game_command(text)
        if is_game:
            try:
                worker = telegram_agent.get_worker("option_game_worker")
                task = f'User started an option game for token {token} in chat {chat_id}. ' \
                    f'Use the start_option_game function with the specified token to start the game.'
                worker.run(task)
            except Exception as e:
                logger.error(f"Error starting option game: {e}")
                await update.message.reply_text("An error occurred while starting the game.")
            return

        is_som, query = is_som_command(text)
        if is_som:
            try:
                worker = telegram_agent.get_worker("stateofmika_worker")
                task = f'User sent a request to StateOfMika in chat {chat_id}: "{query}". ' \
                    f'Use the process_som_response function with this query to process the response. ' \
                    f'After receiving the answer, send the result to the user through reply_to_message.'
                worker.run(task)
            except Exception as e:
                logger.error(f"Error processing StateOfMika request: {e}")
                await update.message.reply_text("An error occurred while processing the request.")
            return
        
        is_news, news_query = is_news_command(text)
        if is_news:
            try:
                worker = telegram_agent.get_worker("stateofmika_worker")
                task = f'User requested news in chat {chat_id}: "{news_query}". ' \
                    f'Use the process_som_response function with this request to process the response, ' \
                    f'setting the is_news_request parameter to True.'
                worker.run(task)
            except Exception as e:
                logger.error(f"Error processing news request: {e}")
                await update.message.reply_text("An error occurred while getting the news.")
            return

        # Check if the user is requesting a list of topics
        if is_topics_command(text):
            worker = telegram_agent.get_worker("allora_worker")
            task = f'User requested a list of all topics command "{text}" in chat {chat_id}. ' \
                   f'Use the get_all_topics function to get available topics. ' \
                   f'After receiving the data, send the result to the user through reply_to_message.'
            try:
                worker.run(task)
            except Exception as e:
                logger.error(f"Error processing topic request: {e}")
                await update.message.reply_text("An error occurred while getting the list of topics.")
            return
        
        # Check if the user is requesting an image generation
        is_image, prompt = is_image_command(text)
        if is_image:
            if imagegen_worker:  # Проверяем, что воркер существует
                worker = telegram_agent.get_worker("imagegen_worker")
                task = f'User requested an image generation in chat {chat_id} with the description: "{prompt}". ' \
                    f'Use the generate_image function with the specified query to generate an image. ' \
                    f'After generating the image, use send_generated_image to send the result to the user.'
                try:
                    worker.run(task)
                except Exception as e:
                    logger.error(f"Error processing image generation request: {e}")
                    await update.message.reply_text("An error occurred while generating the image.")
            else:
                await update.message.reply_text("Sorry, the image generation function is not available.")
            return
            
        # Check if the user is requesting data for a topic by ID
        is_topic, topic_id = is_topic_id_command(text)
        if is_topic:
            worker = telegram_agent.get_worker("allora_worker")
            task = f'User requested data for topic with ID {topic_id} command "{text}" in chat {chat_id}. ' \
                   f'Use the get_inference_by_topic_id function with ID {topic_id} to get the data. ' \
                   f'After receiving the data, send the result to the user through reply_to_message.'
            try:
                worker.run(task)
            except Exception as e:
                logger.error(f"Error processing topic request: {e}")
                await update.message.reply_text(f"An error occurred while getting the data for topic {topic_id}.")
            return
        
        # Check if the user is addressing the bot
        is_question = is_addressed_to_bot(text)
        
        if is_question:
            if is_crypto_request(text):
                # Use the Allora worker
                worker = telegram_agent.get_worker("allora_worker")
                task = f'User asked about a cryptocurrency: "{text}" from {from_user} in chat {chat_id}. ' \
                       f'Analyze the request and use the appropriate Allora function to get the data. ' \
                       f'After receiving the data, send the result to the user through reply_to_message.'
            else:
                # Regular request - use the message_tracker
                worker = telegram_agent.get_worker("message_tracker")
                task = f'Received a question from the user: "{text}" from {from_user} in chat {chat_id}. ' \
                       f'Analyze the question and give an answer, ' \
                       f'using the reply_to_message function.'
        else:
            # Regular message
            worker = telegram_agent.get_worker("message_tracker")
            task = f'Received a message: "{text}" from {from_user} in chat {chat_id}. ' \
                   f'The agent is not asked, only save the message.'
        
        try:
            worker.run(task)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await update.message.reply_text("An error occurred while processing your message.")


    
    return message_handler

def setup_telegram_handler(telegram_agent, tg_plugin):
    """Sets up the Telegram bot message handler"""
    message_handler = create_message_handler(telegram_agent, tg_plugin)
    tg_plugin.add_handler(MessageHandler(filters.TEXT, message_handler))
    logger.info("Telegram bot message handler configured")
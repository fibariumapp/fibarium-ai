import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

from proxy_server import start_proxy_thread
import time
import random

# Запускаем прокси-сервер
proxy_thread = start_proxy_thread()

from utils import logger
from plugins import tg_plugin
from workers import message_tracker_worker, allora_worker, imagegen_worker, som_worker, option_game_worker
from telegram_handler import setup_telegram_handler
from game_sdk.game.agent import Agent
from game_sdk.game.custom_types import FunctionResult

# Check if the required environment variables are present
game_api_key = os.environ.get("GAME_API_KEY")
if not game_api_key:
    raise ValueError("GAME_API_KEY is not specified in the environment variables")

# Function to update the agent state
def get_agent_state_fn(function_result: FunctionResult, current_state: dict) -> dict:
    """
    Agent state management function.
    
    Maintains high-level agent state that may differ from
    individual worker states or aggregate them.
    
    Args:
        function_result (FunctionResult): Result of the previous function execution.
        current_state (dict): Current agent state.
        
    Returns:
        dict: Updated agent state.
    """
    
    if current_state is None:
        # Initialize empty state on the first run
        new_state = {
            "messages": [],
            "last_activity": None,
            "settings": {
                "max_messages_history": 50
            }
        }
    else:
        # Use the current state
        new_state = current_state
        
        # If necessary, you can process the function result
        # and add information to the state
        
    return new_state

def create_agent_with_retry(api_key, name, agent_goal, agent_description, get_agent_state_fn, workers, model_name, max_retries=5):
    for attempt in range(max_retries):
        try:
            return Agent(
                api_key=api_key,
                name=name,
                agent_goal=agent_goal,
                agent_description=agent_description,
                get_agent_state_fn=get_agent_state_fn,
                workers=workers,
                model_name=model_name
            )
        except ValueError as e:
            if "Too Many Requests" in str(e) and attempt < max_retries - 1:
                # Calculate the wait time with exponential increase
                wait_time = (2 * attempt) + random.uniform(50, 100)
                logger.warning(f"Rate limit exceeded (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                raise

if __name__ == "__main__":
    try:
        telegram_agent = create_agent_with_retry(
            api_key=game_api_key,
            name="Telegram Assistant",
            agent_goal="""Monitoring chat messages and responding to user questions. Also able to retrieve and provide data from Allora Network.""",
            agent_description="""An intelligent Telegram bot that:
            1. Saves chat message history
            2. Responds to questions and messages addressed to the bot
            3. Can provide cryptocurrency price predictions and other data from Allora Network
            4. Strives to be helpful and provide accurate information
            5. Responds in the same language used by the user
            
            When the bot is directly addressed or asked a question, it should respond
            using the reply_to_message function with chat_id and response text arguments.
            
            If a user asks about cryptocurrency prices or predictions, the bot can
            use functions from Allora Network through the allora_worker.""",
            get_agent_state_fn=get_agent_state_fn,
            workers=[message_tracker_worker, allora_worker, imagegen_worker, som_worker, option_game_worker],
            model_name="Llama-3.1-405B-Instruct"
        )
        
        # Initialize the agent
        telegram_agent.compile()
        
        # Configure the message handler
        setup_telegram_handler(telegram_agent, tg_plugin)
        
        logger.info("Bot started and ready to work!")
        
        # Start the bot
        tg_plugin.start_polling()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
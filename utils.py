# utils.py
import logging

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Имена бота для обнаружения обращений
BOT_NAMES = ["bot", "agent", "@tronpumper_bot", "tronpumper_bot", "бот", "агент", "@razer_fiba_dev_pass_bot", "razer_fiba_dev_pass_bot"]

TOPICS_COMMANDS = ["/topics", "/топики"]
TOPIC_ID_COMMANDS = ["/topic", "/топик"]
IMAGE_COMMANDS = ["/image", "/картинка", "/img"]
SOM_COMMANDS = ["/som", "/stateofmika", "/analyze", "/price"]
GAME_COMMANDS = ["/game", "/игра", "/опцион", "/option"]
NEWS_COMMANDS = ["/news", "/новости"]


def is_som_command(message: str) -> tuple[bool, str]:
    """
    Checks if the message is a command for StateOfMika.
    Returns (True, query) if this is a StateOfMika command, otherwise (False, None).
    """
    lowerMsg = message.lower().strip()
    parts = lowerMsg.split(maxsplit=1)
    
    if len(parts) >= 1 and parts[0] in SOM_COMMANDS:
        if parts[0] == "/price" and len(parts) > 1:
            # For the /price command, automatically add "price" before the token
            token = parts[1].strip()
            query = f"price of {token} at the moment"
        else:
            query = parts[1] if len(parts) > 1 else "tell me about your capabilities" 
        return True, query
    
    return False, None

def is_news_command(message: str) -> tuple[bool, str]:
    """
    Checks if the message is a command for getting news.
    Returns (True, request) if this is a news command, otherwise (False, None).
    
    Examples:
    - /news crypto
    - /news
    - /news bitcoin
    - /новости биткоин
    """
    lowerMsg = message.lower().strip()
    parts = lowerMsg.split(maxsplit=1)
    
    if len(parts) >= 1 and parts[0] in NEWS_COMMANDS:
        if len(parts) > 1:
            # The user specified a specific request
            request = f"get latest and most important news about {parts[1]}"
        else:
            # The user sent just /news
            request = "provide latest most important news for today date"
        return True, request
    
    return False, None

# Add a function to check the topics command
def is_topics_command(message: str) -> bool:
    """Checks if the message is a command to get a list of topics"""
    lowerMsg = message.lower().strip()
    parts = lowerMsg.split()
    
    return len(parts) >= 1 and parts[0] in TOPICS_COMMANDS

def is_game_command(message: str) -> tuple[bool, str]:
    """
    Checks if the message is a command to play an option game.
    Returns (True, token) if this is an option game command, otherwise (False, None).
    
    Examples:
    - /game BTC
    - /игра ETH
    """
    lowerMsg = message.lower().strip()
    parts = lowerMsg.split(maxsplit=1)
    
    if len(parts) >= 2 and parts[0] in GAME_COMMANDS:
        token = parts[1].upper()  # Приводим токен к верхнему регистру
        return True, token
    
    return False, None

def is_topic_id_command(message: str) -> (bool, int):
    """
    Checks if the message is a command to get data by topic ID.
    Returns (True, topic_id) if this is a topic command, otherwise (False, None).
    """
    lowerMsg = message.lower().strip()
    parts = lowerMsg.split()
    
    if len(parts) >= 2 and parts[0] in TOPIC_ID_COMMANDS:
        try:
            topic_id = int(parts[1])
            return True, topic_id
        except ValueError:
            pass
    
    return False, None

# Проверяем, обращаются ли к боту
def is_addressed_to_bot(message: str) -> bool:
    lowerMsg = message.lower()

    # Проверяем прямое упоминание имени бота
    if any(name in lowerMsg for name in BOT_NAMES):
        return True

    # Проверяем на вопросительные конструкции
    if message.endswith("?") and len(message) > 15:
        return True

    # Проверяем на команды (начинаются с /)
    if message.startswith("/") and len(message) > 1:
        return True

    return False

# Проверка на запрос криптоданных
def is_crypto_request(text: str) -> bool:
    crypto_keywords = ['криптовалюта', 'биткоин', 'эфириум', 'btc', 'eth', 
                      'bitcoin', 'ethereum', 'цена', 'прогноз', 'allora', 'crypto']
    return any(word in text.lower() for word in crypto_keywords)

def is_image_command(message: str) -> tuple[bool, str]:
    """
    Checks if the message is a command to generate an image.
    Returns (True, prompt) if this is an image generation command, otherwise (False, None).
    
    Examples:
    - /image beautiful sunset on the beach
    - /картинка космический корабль в стиле киберпанк
    """
    lowerMsg = message.lower().strip()
    parts = lowerMsg.split(maxsplit=1)
    
    if len(parts) >= 1 and parts[0] in IMAGE_COMMANDS:
        prompt = parts[1] if len(parts) > 1 else "beautiful landscape" # Default prompt
        return True, prompt
    
    return False, None

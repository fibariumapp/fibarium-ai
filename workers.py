from typing import Tuple
from game_sdk.game.custom_types import Function, Argument, FunctionResult, FunctionResultStatus, FunctionResultStatus
from game_sdk.game.agent import WorkerConfig
import time
import threading
from plugins import tg_plugin, allora_plugin, imagegen_plugin, stateofmika_plugin
from utils import logger

# ===== Telegram Worker =====

# Функции для telegram бота
def store_message_executable(chat_id: str, message_id: int, text: str, sender: str) -> tuple[FunctionResultStatus, str, dict]:
    """Saves the message to the history"""
    logger.info(f"Saved message from {sender} in chat {chat_id}: {text}")
    return FunctionResultStatus.DONE, "Message successfully saved", {}

def reply_to_message_executable(chat_id: str, text: str) -> tuple[FunctionResultStatus, str, dict]:
    """Responds to the user's message in Telegram"""
    try:
        # Используем плагин для отправки сообщения
        tg_plugin.send_message(chat_id=chat_id, text=text)
        logger.info(f"Sent answer to chat {chat_id}: {text}")
        return FunctionResultStatus.DONE, "Answer successfully sent", {}
    except Exception as e:
        logger.error(f"Error sending answer: {e}")
        return FunctionResultStatus.FAILED, f"Error sending answer: {str(e)}", {}

def do_nothing_executable() -> tuple[FunctionResultStatus, str, dict]:
    """Does nothing, just skips the turn"""
    return FunctionResultStatus.DONE, "Nothing to do", {}

# Создаем функции для telegram
store_message_fn = Function(
    fn_name="store_message",
    fn_description="Saves the message to the history",
    args=[
        Argument(name="chat_id", description="Chat ID"),
        Argument(name="message_id", description="Message ID"),
        Argument(name="text", description="Message text"),
        Argument(name="sender", description="Sender"),
    ],
    executable=store_message_executable
)

reply_to_message_fn = Function(
    fn_name="reply_to_message",
    fn_description="Отвечает на сообщение пользователя в Telegram",
    args=[
        Argument(name="chat_id", description="Chat ID"),
        Argument(name="text", description="Answer text"),
    ],
    executable=reply_to_message_executable
)

do_nothing_fn = Function(
    fn_name="do_nothing",
    fn_description="Skips the turn without performing any actions",
    args=[],
    executable=do_nothing_executable
)

# Состояние для telegram worker
def get_telegram_worker_state_fn(function_result: FunctionResult, current_state: dict) -> dict:
    """Updates and returns the worker state"""
    if current_state is None:
        # Initialize the state
        return {"messages": []}
    
    # In the real bot, here you could save the message history
    return current_state

# ===== Allora Worker =====

# Получаем функции Allora
get_price_inference_fn = allora_plugin.get_function("get_price_inference")
get_all_topics_fn = allora_plugin.get_function("get_all_topics")
get_inference_by_topic_id_fn = allora_plugin.get_function("get_inference_by_topic_id")

# Состояние для Allora worker
def get_allora_state_fn(function_result: FunctionResult, current_state: dict) -> dict:
    """Updates and returns the Allora worker state"""
    if current_state is None:
        return {"last_query": None, "results": []}
    
    # Update the state with information from the function result
    if function_result and hasattr(function_result, 'info') and function_result.info:
        new_state = current_state.copy()
        new_state.update({"last_result": function_result.info})
        return new_state
    
    return current_state

def send_price_inference_executable(chat_id: str, asset: str, timeframe: str, price_inference: str) -> tuple[FunctionResultStatus, str, dict]:
    """Sends the price prediction result to the chat"""
    try:
        message = f"Price prediction for {asset} in the interval {timeframe}: {price_inference}"
        tg_plugin.send_message(chat_id=chat_id, text=message)
        logger.info(f"Sent price prediction to chat {chat_id}: {message}")
        return FunctionResultStatus.DONE, "Price prediction sent", {}
    except Exception as e:
        logger.error(f"Error sending price prediction: {e}")
        return FunctionResultStatus.FAILED, f"Error sending price prediction: {str(e)}", {}

# Создаем функцию
send_price_inference_fn = Function(
    fn_name="send_price_inference",
    fn_description="Sends the price prediction result to the user",
    args=[
        Argument(name="chat_id", description="Chat ID"),
        Argument(name="asset", description="Asset symbol (BTC, ETH, etc.)"),
        Argument(name="timeframe", description="Timeframe"),
        Argument(name="price_inference", description="Price prediction"),
    ],
    executable=send_price_inference_executable
)

# ===== Worker Configs =====

# Создаем конфигурацию воркера для Telegram
message_tracker_worker = WorkerConfig(
    id="message_tracker",
    worker_description="Tracks and saves messages from the Telegram chat",
    action_space=[store_message_fn, do_nothing_fn, reply_to_message_fn],
    get_state_fn=get_telegram_worker_state_fn
)

# Создаем конфигурацию воркера для Allora
allora_worker = WorkerConfig(
    id="allora_worker",
    worker_description="Specialized worker for getting data and predictions from Allora Network. Can get price predictions for cryptocurrencies, all available topics and data predictions by topic ID.",
    action_space=[get_price_inference_fn, get_all_topics_fn, get_inference_by_topic_id_fn, send_price_inference_fn, reply_to_message_fn],
    get_state_fn=get_allora_state_fn,
    instruction="""You are an expert in working with Allora Network. Use functions to get price predictions for cryptocurrencies and other data.

1. For price predictions: If the user requests a price prediction or uses the /prognoz or /прогноз command, use get_price_inference with the arguments:
   - asset (asset symbol, e.g. BTC, ETH)
   - timeframe (timeframe, e.g. 5m, 8h, 24h)
   After receiving the prediction, must use reply_to_message to send the result to the user.

2. For getting all topics: If the user requests information about available topics or uses the /topics or /топики command, use get_all_topics. 
   After receiving the topics, must usereply_to_message to send the result to the user.

3. For getting data by a specific topic: If the user requests data by topic ID or uses the /topic_id command, use get_inference_by_topic_id with the topic ID.
   After receiving the data, must use reply_to_message to send the result to the user.

IMPORTANT: After executing any function, always send the result to the user through reply_to_message.
"""
)

# ===== ImageGen Worker =====

# Проверяем, что плагин успешно инициализирован
generate_image_fn = imagegen_plugin.get_function("generate_image")

    # Функция для отправки сгенерированного изображения
def send_generated_image_executable(chat_id: str, image_url: str, prompt: str) -> tuple[FunctionResultStatus, str, dict]:
    """Sends the generated image to the chat"""
    try:
        # Проверяем, есть ли у tg_plugin метод send_photo
        if not hasattr(tg_plugin, "send_media"):
            # Если метода нет, добавляем его
            setattr(tg_plugin, "send_media", lambda chat_id, media_type, media, caption=None: 
                tg_plugin.send_media(chat_id=chat_id, media_type=media_type, media=media, caption=caption))
            
        # Отправляем фото через Telegram API
        tg_plugin.send_media(chat_id=chat_id, media_type="photo", media=image_url, caption=f"Сгенерировано по запросу: {prompt}")
        logger.info(f"Sent image to chat {chat_id} by request: {prompt}")
        return FunctionResultStatus.DONE, "Image sent", {}
    except Exception as e:
        logger.error(f"Error sending image: {e}")
        return FunctionResultStatus.FAILED, f"Error sending image: {str(e)}", {}

    # Создаем функцию для отправки изображения
send_generated_image_fn = Function(
    fn_name="send_generated_image",
    fn_description="Sends the generated image to the user in Telegram",
    args=[
        Argument(name="chat_id", description="Chat ID"),
        Argument(name="image_url", description="URL of the generated image"),
        Argument(name="prompt", description="Request by which the image was generated"),
    ],
    executable=send_generated_image_executable
    )

    # Состояние для ImageGen worker
def get_imagegen_state_fn(function_result: FunctionResult, current_state: dict) -> dict:
    """Updates the ImageGen worker state"""
    if current_state is None:
        return {"last_query": None, "results": []}
    
    # Обновляем состояние с информацией из результата функции
    if function_result and hasattr(function_result, 'info') and function_result.info:
        new_state = current_state.copy()
        new_state.update({"last_result": function_result.info})
        return new_state
    
    return current_state

    # Создаем конфигурацию воркера для ImageGen
imagegen_worker = WorkerConfig(
    id="imagegen_worker",
    worker_description="Image generation by user request using neural network models",
    action_space=[generate_image_fn, send_generated_image_fn, reply_to_message_fn],
    get_state_fn=get_imagegen_state_fn,
    instruction="""You are an expert in generating images using neural networks.

1. If the user asks to generate an image, requests a picture, or uses the /image or /картинка command, use the generate_image function with the argument:
    - prompt (description of the image to generate)
    
2. After successfully generating an image, must use the send_generated_image function to send the image to the user in the chat. The function takes the arguments:
    - chat_id (Chat ID where the image should be sent)
    - image_url (URL of the generated image, received after calling generate_image)
    - prompt (request by which the image was generated)
    
IMPORTANT: Always send the results of generation to the user through send_generated_image. If an error occurs, send an error message through reply_to_message.
"""
)

# ===== StateOfMika Worker =====

som_route_query_fn = stateofmika_plugin.get_function()

def get_stateofmika_state_fn(function_result: FunctionResult, current_state: dict) -> dict:
    """Updates the StateOfMika worker state"""
    init_state = {
        "previous_queries": [],
        "previous_routes": []
    }
    
    if current_state is None:
        return init_state
    
    # Обновляем состояние с информацией из результата функции
    if function_result and hasattr(function_result, 'info') and function_result.info:
        new_state = current_state.copy()
        if "previous_queries" not in new_state:
            new_state["previous_queries"] = []
        if "previous_routes" not in new_state:
            new_state["previous_routes"] = []
            
        new_state["previous_queries"].append(function_result.info.get("query", ""))
        new_state["previous_routes"].append(function_result.info.get("route", {}))
        return new_state
    
    return current_state


# Создаем функцию-обработчик для StateOfMika
def process_som_response_executable(chat_id: str, query: str, is_news_request: bool = False) -> tuple[FunctionResultStatus, str, dict]:
    """Обрабатывает запрос к StateOfMika и форматирует ответ"""
    try:
        
        # Вызываем StateOfMika API
        result = stateofmika_plugin._execute_query(query)
        
        if result and result[0] == FunctionResultStatus.DONE:
            _, _, info = result
            logger.info(f"Получен ответ от StateOfMika: {info}")
            response = info.get('response', {})
            
            # Форматирование ответа для пользователя
            if isinstance(response, dict) and 'processed_response' in response:
                processed = response['processed_response']
                
                # Специальная обработка новостных запросов
                if is_news_request and 'original_response' in response:
                    try:
                        import re
                        
                        # Извлекаем структуру новостей
                        original = response['original_response']
                        
                        # Шаблоны для извлечения данных
                        url_pattern = re.compile(r"url='(https?://[^']+)'")
                        domain_pattern = re.compile(r"domain='([^']+)'")
                        title_pattern = re.compile(r"title='([^']+)'")
                        
                        # Собираем информацию
                        domains = domain_pattern.findall(original)
                        urls = url_pattern.findall(original)
                        titles = title_pattern.findall(original)
                        
                        # Форматируем новости с источниками и ссылками
                        if domains and urls and len(domains) == len(urls):
                            news_lines = processed.strip().split('\n')
                            formatted_news = []
                            
                            for i, line in enumerate(news_lines):
                                if i < len(domains) and i < len(urls):
                                    # Добавляем источник и ссылку к новости
                                    formatted_news.append(f"{line} [Source: {domains[i]} - {urls[i]}]")
                                else:
                                    formatted_news.append(line)
                            
                            processed = '\n\n'.join(formatted_news)
                    except Exception as e:
                        logger.error(f"Ошибка при форматировании новостей: {e}")
                
                # Используем стандартную логику для извлечения ответа
                if isinstance(processed, dict) and 'summary' in processed:
                    final_message = processed['summary']
                else:
                    final_message = str(processed)
            else:
                final_message = str(response)
            
            # Отправка ответа пользователю
            tg_plugin.send_message(chat_id=chat_id, text=final_message)
            logger.info(f"Отправлен ответ от StateOfMika в чат {chat_id}")
            return FunctionResultStatus.DONE, "Ответ от StateOfMika отправлен", {}
        else:
            error_msg = result[1] if result and len(result) > 1 else "Не удалось получить корректный ответ от StateOfMika"
            tg_plugin.send_message(chat_id=chat_id, text=f"Ошибка: {error_msg}")
            return FunctionResultStatus.FAILED, error_msg, {}
    except Exception as e:
        logger.error(f"Ошибка при обработке ответа от StateOfMika: {e}")
        tg_plugin.send_message(chat_id=chat_id, text=f"Ошибка: {str(e)}")
        return FunctionResultStatus.FAILED, f"Ошибка при обработке ответа: {str(e)}", {}

# Создаем функцию
process_som_response_fn = Function(
    fn_name="process_som_response",
    fn_description="Processes the StateOfMika request, formats and sends the answer to the user",
    args=[
        Argument(name="chat_id", description="Chat ID"),
        Argument(name="query", description="StateOfMika request"),
        Argument(name="is_news_request", description="Is the request a news request", default=False),
    ],
    executable=process_som_response_executable
)

# Обновляем конфигурацию воркера для StateOfMika
som_worker = WorkerConfig(
    id="stateofmika_worker",
    worker_description="Intelligent assistant with the ability to analyze images, parse websites, get news, information about tokens and mathematical calculations",
    action_space=[som_route_query_fn, process_som_response_fn, reply_to_message_fn],
    get_state_fn=get_stateofmika_state_fn,
    instruction="""You are an expert in working with the multi-functional StateOfMika service.

For processing user requests, ALWAYS use the process_som_response function, which:
1. Sends the request to StateOfMika
2. Correctly extracts and formats the answer
3. Automatically sends the result to the user

The process_som_response function takes the following arguments:
- chat_id: Chat ID where the answer should be sent
- query: StateOfMika request (e.g. "What is the current price of Ethereum?")

Examples of requests that can be processed:
- Image analysis: "What is depicted in this image: https://example.com/image.jpg"
- Website parsing: "Get the content of the page https://example.com"
- News: "What are the latest news about Bitcoin?"
- Token information: "What is the current price of Ethereum?"
- Mathematical calculations: "Calculate the integral of x^2 + 3x"

IMPORTANT: DO NOT use the som_route_query function directly, ALWAYS use process_som_response!
"""
)

# ===== Option Game Worker =====

# Структура для хранения игр
active_games = {}

# Функция для создания опроса (голосования)
def create_poll_executable(chat_id: str, token: str, current_price: str, predicted_price: str, timeframe: str) -> tuple[FunctionResultStatus, str, dict]:
    """Creates a poll for the option game"""
    try:
        # Создаем опрос с вариантами выше/ниже предсказанной цены
        title = f"🎮 Option Game: Where will {token} go?"
        question = f"Through {timeframe} the price of {token} will be higher or lower than {predicted_price}? Now: {current_price}"
        options = ["↗️ Higher", "↘️ Lower"]
        
        # Записываем ID опроса, возвращаемый плагином телеграм
        poll_message = tg_plugin.create_poll(
            chat_id=chat_id,
            question=question,
            options=options,
            is_anonymous=False,
            allows_multiple_answers=False
        )
        
        # Сохраняем информацию об игре
        temp_poll_id = f"{token}_{int(time.time())}"
        
        active_games[temp_poll_id] = {
            "chat_id": chat_id,
            "token": token,
            "current_price": current_price,
            "predicted_price": predicted_price,
            "timeframe": timeframe,
            "poll_id": temp_poll_id,  # Temporary ID, in a real scenario replace with poll_message.poll.id
            "message_id": None,  # In a real scenario replace with poll_message.message_id
            "start_time": time.time(),
            "participants": {},
            "completed": False
        }
        
        # Запускаем таймер для завершения игры
        timeframe_minutes = int(timeframe.replace("m", ""))
        
        # Возвращаем успешный результат с ID опроса для дальнейшего отслеживания
        logger.info(f"Created a poll for token {token} with ID {temp_poll_id}")
        return FunctionResultStatus.DONE, "Poll successfully created", {"poll_id": temp_poll_id}
    except Exception as e:
        logger.error(f"Error creating a poll: {e}")
        return FunctionResultStatus.FAILED, f"Error creating a poll: {str(e)}", {}

# Функция для проверки результатов игры
def check_game_results_executable(chat_id: str, poll_id: str, token: str) -> tuple[FunctionResultStatus, str, dict]:
    """Checks the game results and announces the winners"""
    logger.info(f"CALLING CHECKING RESULTS for {token} with ID {poll_id}")
    try:
        if poll_id in game_timers:
            game_timers[poll_id].cancel()
            del game_timers[poll_id]
            logger.info(f"Timer for game {poll_id} canceled")
        
        # Проверяем, существует ли игра с указанным ID
        game_exists = False
        for game_id in active_games:
            if game_id == poll_id or (active_games[game_id]["token"] == token and not active_games[game_id]["completed"]):
                poll_id = game_id  # Используем найденный ID
                game_info = active_games[game_id]
                game_exists = True
                break
        
        if not game_exists:
            return FunctionResultStatus.FAILED, "Game not found or already completed", {}
        
        if active_games[poll_id]["completed"]:
            return FunctionResultStatus.FAILED, "Game already completed", {"winner": active_games[poll_id].get("winner_option")}
        
        # Получаем текущую цену токена через StateOfMika
        query = f"price of {token} at the moment"
        result = stateofmika_plugin._execute_query(query)
        
        if result and result[0] == FunctionResultStatus.DONE:
            # Извлекаем текущую цену
            _, _, info = result
            current_price_str = str(info.get('response', {}).get('processed_response', '0'))
            
            try:
                current_price = float(current_price_str)
                predicted_price = float(game_info["predicted_price"])
                
                # Определяем результат
                if current_price > predicted_price:
                    winner_option = "↗️ Higher"
                    result_emoji = "⬆️"
                else:
                    winner_option = "↘️ Lower"
                    result_emoji = "⬇️"
                
                # Формируем сообщение с результатами
                message = f"🎮 Results of the 'Option' game for {token}:\n\n"
                message += f"🕒 Prediction: {game_info['predicted_price']}\n"
                message += f"💰 Starting price: {game_info['current_price']}\n"
                message += f"💲 Current price: {current_price_str}\n"
                message += f"🏆 The winner option: {result_emoji} {winner_option}\n\n"
                
                # Отправляем сообщение с результатами
                tg_plugin.send_message(chat_id=chat_id, text=message)
                
                # Помечаем игру как завершенную
                active_games[poll_id]["completed"] = True
                active_games[poll_id]["end_price"] = current_price_str
                active_games[poll_id]["winner_option"] = winner_option
                
                logger.info(f"Game for token {token} completed, the winner option is {winner_option}")
                return FunctionResultStatus.DONE, "Results announced successfully", {"winner": winner_option}
            except (ValueError, TypeError):
                error_msg = f"Error parsing price: {current_price_str}"
                logger.error(error_msg)
                tg_plugin.send_message(chat_id=chat_id, text=f"Error checking results: {error_msg}")
                return FunctionResultStatus.FAILED, error_msg, {}
        else:
            error_msg = "Unable to get the current price of the token"
            logger.error(error_msg)
            tg_plugin.send_message(chat_id=chat_id, text=f"Error checking results: {error_msg}")
            return FunctionResultStatus.FAILED, error_msg, {}
    except Exception as e:
        logger.error(f"Error checking results: {e}")
        tg_plugin.send_message(chat_id=chat_id, text=f"Error checking results: {str(e)}")
        return FunctionResultStatus.FAILED, f"Error checking results: {str(e)}", {}
    
game_timers = {}

# Функция для запуска проверки результатов с задержкой
def schedule_game_check(chat_id: str, poll_id: str, token: str, delay_seconds: int):
    """Plans a check of the game results after a specified time"""
    logger.info(f"CREATING TIMER: scheduled check in {delay_seconds} seconds for {token}")
    
    def check_game_callback():
        try:
            logger.info(f"TIMER ACTIVATION: scheduled check for {token} is being performed")
            result = check_game_results_executable(chat_id, poll_id, token)
            if result[0] != FunctionResultStatus.DONE:
                logger.error(f"Error checking results: {result[1]}")
        except Exception as e:
            logger.error(f"Error in the game check timer: {e}")
    
    # Создаем и запускаем таймер
    timer = threading.Timer(delay_seconds, check_game_callback)
    timer.daemon = True
    timer.start()
    
    # Сохраняем таймер для возможности отмены
    game_timers[poll_id] = timer
    
    logger.info(f"TIMER STARTED: {token} will be checked in {delay_seconds} seconds")

# Создаем функции
create_poll_fn = Function(
    fn_name="create_poll",
    fn_description="Creates a poll for the option game",
    args=[
        Argument(name="chat_id", description="Chat ID"),
        Argument(name="token", description="Token symbol (BTC, ETH, etc.)"),
        Argument(name="current_price", description="Current price of the token"),
        Argument(name="predicted_price", description="Predicted price of the token"),
        Argument(name="timeframe", description="Timeframe for the game (e.g., 5m)"),
    ],
    executable=create_poll_executable
)

check_game_results_fn = Function(
    fn_name="check_game_results",
    fn_description="Checks the game results and announces the winners",
    args=[
        Argument(name="chat_id", description="Chat ID"),
        Argument(name="poll_id", description="Poll ID"),
        Argument(name="token", description="Token symbol (BTC, ETH, etc.)"),
    ],
    executable=check_game_results_executable
)

# Function to start the option game
def start_option_game_executable(chat_id: str, token: str) -> tuple[FunctionResultStatus, str, dict]:
    """Starts the option game for a given token"""
    try:
        # Step 1: Get the current price of the token through StateOfMika
        logger.info(f"Starting game for token {token}")
        query = f"price of {token} at the moment"
        som_result = stateofmika_plugin._execute_query(query)
        
        if som_result and som_result[0] == FunctionResultStatus.DONE:
            # Extract the current price
            _, _, info = som_result
            response = info.get('response', {})
            
            # Analyze the answer and extract the price
            if isinstance(response, dict) and 'processed_response' in response:
                current_price_str = str(response['processed_response'])
            else:
                current_price_str = str(response)
            
            logger.info(f"Current price of {token}: {current_price_str}")
            
            # Step 2: Get the prediction through Allora
            timeframe = "5m"  # 5 minutes by condition
            allora_result = allora_plugin.get_price_inference(asset=token, timeframe=timeframe)
            
            if allora_result and allora_result[0] == FunctionResultStatus.DONE:
                # Extract the predicted price
                _, _, allora_info = allora_result
                predicted_price = allora_info.get('price_inference', '0')
                logger.info(f"Predicted price of {token} through {timeframe}: {predicted_price}")
                
                # Step 3: Create a poll
                poll_result = create_poll_executable(
                    chat_id=chat_id,
                    token=token,
                    current_price=current_price_str,
                    predicted_price=predicted_price,
                    timeframe=timeframe
                )
                
                if poll_result and poll_result[0] == FunctionResultStatus.DONE:
                    poll_id = poll_result[2].get('poll_id')
                    
                    # Send a message about the game start
                    message = f"🎮 Option game for {token} started!\n"
                    message += f"⏱️ Current price: {current_price_str}\n"
                    message += f"🔮 Prediction through {timeframe}: {predicted_price}\n"
                    message += f"🎯 Choose your option in the poll above!\n"
                    message += f"🕒 Results will be after {timeframe}."
                    
                    tg_plugin.send_message(chat_id=chat_id, text=message)
                    
                    # Шаг 4: Планируем проверку результатов через 5 минут
                    timeframe_minutes = int(timeframe.replace('m', ''))
                    wait_seconds = timeframe_minutes * 60

                    
                    # Для демонстрационных целей можно использовать меньшую задержку
                    # wait_seconds = 30  # 30 секунд для тестирования
                    
                    # Планируем проверку результатов
                    schedule_game_check(chat_id, poll_id, token, wait_seconds)
                    

                    
                    # Return information for further checking the results
                    return FunctionResultStatus.DONE, "Game successfully started", {"poll_id": poll_id, "token": token}
                else:
                    error_msg = "Unable to create a poll for the game"
                    logger.error(error_msg)
                    tg_plugin.send_message(chat_id=chat_id, text=f"Error: {error_msg}")
                    return FunctionResultStatus.FAILED, error_msg, {}
            else:
                error_msg = "Unable to get the price prediction through Allora"
                logger.error(error_msg)
                tg_plugin.send_message(chat_id=chat_id, text=f"Ошибка: {error_msg}")
                return FunctionResultStatus.FAILED, error_msg, {}
        else:
            error_msg = "Unable to get the current price of the token"
            logger.error(error_msg)
            tg_plugin.send_message(chat_id=chat_id, text=f"Error: {error_msg}")
            return FunctionResultStatus.FAILED, error_msg, {}
    except Exception as e:
        logger.error(f"Error starting the game: {e}")
        tg_plugin.send_message(chat_id=chat_id, text=f"Error starting the game: {str(e)}")
        return FunctionResultStatus.FAILED, f"Error starting the game: {str(e)}", {}

start_option_game_fn = Function(
    fn_name="start_option_game",
    fn_description="Starts the option game for a given token",
    args=[
        Argument(name="chat_id", description="Chat ID"),
        Argument(name="token", description="Token symbol (BTC, ETH, etc.)"),
    ],
    executable=start_option_game_executable
)

# Состояние для Option Game worker
def get_option_game_state_fn(function_result: FunctionResult, current_state: dict) -> dict:
    """Updates the Option Game worker state"""
    if current_state is None:
        return {"games": {}}
    
    # Обновляем состояние с информацией из результата функции
    if function_result and hasattr(function_result, 'info') and function_result.info:
        new_state = current_state.copy()
        
        # Если это результат start_option_game, добавляем новую игру
        if 'poll_id' in function_result.info and 'token' in function_result.info:
            poll_id = function_result.info['poll_id']
            token = function_result.info['token']
            
            if 'games' not in new_state:
                new_state['games'] = {}
            
            new_state['games'][poll_id] = {
                'token': token,
                'status': 'active',
                'start_time': time.time()
            }
            
            logger.info(f"Added a new game to the state: {poll_id} for token {token}")
        
        # Если это результат check_game_results, обновляем статус игры
        if 'winner' in function_result.info:
            # Ищем соответствующую игру среди активных
            for poll_id, game_info in new_state.get('games', {}).items():
                if game_info.get('token') == function_result.info.get('token'):
                    new_state['games'][poll_id]['status'] = 'completed'
                    new_state['games'][poll_id]['winner'] = function_result.info['winner']
                    logger.info(f"Updated the status of the game {poll_id} to completed")
                    break
        
        return new_state
    
    return current_state

# Создаем конфигурацию воркера для Option Game
option_game_worker = WorkerConfig(
    id="option_game_worker",
    worker_description="Worker for the option game, predicting the price movement of cryptocurrencies",
    action_space=[start_option_game_fn, create_poll_fn, check_game_results_fn, reply_to_message_fn],
    get_state_fn=get_option_game_state_fn,
    instruction="""You are an expert in organizing option games in Telegram. 

1. When a user uses the /game or /игра command with a token specified (e.g., /game BTC), use ONLY the start_option_game function to start the game.

2. The start_option_game function automatically performs all necessary actions:
   - Gets the current price of the token through StateOfMika
   - Gets the price prediction through Allora for 5 minutes ahead
   - Creates a poll for users with options "Higher" and "Lower"
   - Sends a message about the game start to the chat
   - Plans an automatic check of the results through 5 minutes

3. DO NOT use check_game_results immediately after starting the game. This function will be automatically called by the timer after 5 minutes.

4. The check_game_results function should be called ONLY:
   - Automatically through 5 minutes (through the timer)
   - When the user explicitly requests a check with the /check_game command

IMPORTANT: NEVER call check_game_results immediately after start_option_game!
"""
)
import sys
import os
from telegram_plugin_gamesdk.telegram_plugin import TelegramPlugin

from enum import Enum
from utils import logger

class ChainSlug(str, Enum):
    TESTNET = "testnet"
    MAINNET = "mainnet"

sys.path.append(os.path.join(os.path.dirname(__file__), 'plugins'))
from allora import AlloraPlugin
from imagegen import ImageGenPlugin
from stateofmika import SOMRouter


# Telegram plugin
def init_telegram_plugin():
    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not specified in the environment variables")

    tg_plugin = TelegramPlugin(bot_token=telegram_bot_token)
    logger.info("Telegram plugin initialized")
    return tg_plugin


# Allora plugin
def init_allora_plugin():
    allora_plugin = AlloraPlugin(
        chain_slug=os.environ.get("ALLORA_CHAIN_SLUG", ChainSlug.MAINNET),
        api_key=os.environ.get("ALLORA_API_KEY"),
    )
    logger.info("Allora plugin initialized")
    return allora_plugin


# Imagegen plugin
def init_imagegen_plugin():
    try:
        imagegen_plugin = ImageGenPlugin(
            api_key=os.environ.get("TOGETHER_API_KEY")
        )
        logger.info("Imagegen plugin initialized")
        return imagegen_plugin
    except Exception as e:
        logger.error(f"Error initializing Imagegen plugin: {e}")
        return None


def init_stateofmika_plugin():
    try:
        stateofmika_plugin = SOMRouter(
            api_key=os.environ.get("SOM_API_KEY")
        )
        logger.info("StateOfMika plugin initialized")
        return stateofmika_plugin
    except Exception as e:
        logger.error(f"Error initializing StateOfMika plugin: {e}")
        return None


# Initialize plugins
tg_plugin = init_telegram_plugin()
allora_plugin = init_allora_plugin()
imagegen_plugin = init_imagegen_plugin()
stateofmika_plugin = init_stateofmika_plugin()

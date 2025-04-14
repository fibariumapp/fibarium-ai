import json
import requests
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from game_sdk.game.custom_types import Argument, Function, FunctionResultStatus

# Определяем эти классы локально, чтобы не зависеть от SDK
class ChainSlug(str, Enum):
    TESTNET = "testnet"
    MAINNET = "mainnet"

class ChainID(str, Enum):
    TESTNET = "allora-testnet-1"
    MAINNET = "allora-mainnet-1"

class PriceInferenceToken(str, Enum):
    BTC = "BTC"
    ETH = "ETH"

class PriceInferenceTimeframe(str, Enum):
    FIVE_MIN = "5m"
    EIGHT_HOURS = "8h"

class SignatureFormat(str, Enum):
    ETHEREUM_SEPOLIA = "ethereum-11155111"

DEFAULT_ALLORA_BASE_API_URL = "http://localhost:4200/v2"
DEFAULT_ALLORA_API_KEY = "UP-17f415babba7482cb4b446a1"

class AlloraPlugin:
    """
    Allora Network plugin using direct HTTP requests instead of SDK.
    """

    def __init__(
        self,
        chain_slug: Optional[str] = ChainSlug.TESTNET,
        api_key: Optional[str] = DEFAULT_ALLORA_API_KEY,
        base_api_url: Optional[str] = DEFAULT_ALLORA_BASE_API_URL,
    ):
        """
        Initialize the Allora client.

        Args:
            chain_slug (str): The chain slug to use for the Allora client
            api_key (str): Allora API key
            base_api_url (str): The base API URL to use for the Allora client
        """
        self.chain_id = ChainID.TESTNET.value if chain_slug == ChainSlug.TESTNET else ChainID.MAINNET.value
        self.api_key = api_key
        self.base_api_url = base_api_url

        # Available client functions
        self._functions: Dict[str, Function] = {
            "get_all_topics": Function(
                fn_name="get_all_topics",
                fn_description="Get all the topics available on Allora Network.",
                args=[],
                hint="This function is used to get all the topics available on Allora Network.",
                executable=self.get_all_topics,
            ),
            "get_inference_by_topic_id": Function(
                fn_name="get_inference_by_topic_id",
                fn_description="Fetches an inference from Allora Network given a topic id.",
                args=[
                    Argument(
                        name="topic_id",
                        description="The topic_id corresponds to the unique id of one of an active topic on Allora Network",
                        type="number",
                    )
                ],
                hint="This function is used to get the inference by topic id.",
                executable=self.get_inference_by_topic_id,
            ),
            "get_price_inference": Function(
                fn_name="get_price_inference",
                fn_description="Fetches from Allora Network the future price inference for a given crypto asset and timeframe.",
                args=[
                    Argument(
                        name="asset",
                        description="The crypto asset symbol to get the price inference for. Example: BTC, ETH, SOL, SHIB, etc.",
                        type="string",
                    ),
                    Argument(
                        name="timeframe",
                        description="The timeframe to get the price inference for. Example: 5m, 8h, 24h, etc.",
                        type="string",
                    ),
                ],
                hint="This function is used to get the price inference for a given crypto asset and timeframe.",
                executable=self.get_price_inference,
            ),
        }

    @property
    def available_functions(self) -> List[str]:
        """Get list of available function names."""
        return list(self._functions.keys())

    def get_function(self, fn_name: str) -> Function:
        """
        Get a specific function by name.

        Args:
            fn_name: Name of the function to retrieve

        Raises:
            ValueError: If function name is not found

        Returns:
            Function object
        """
        if fn_name not in self._functions:
            raise ValueError(
                f"Function '{fn_name}' not found. Available functions: {', '.join(self.available_functions)}"
            )
        return self._functions[fn_name]

    def make_api_request(self, endpoint: str) -> Any:
        """
        Make an HTTP request to the Allora API.
        
        Args:
            endpoint: The API endpoint
            
        Returns:
            The JSON response
        """
        url = f"{self.base_api_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def get_all_topics(self, **kwargs) -> Tuple[FunctionResultStatus, str, dict]:
        """Get all topics available on Allora Network."""
        try:
            endpoint = f"allora/{self.chain_id}/topics"
            response_data = self.make_api_request(endpoint)
            
            # Get the topics from the response
            topics = response_data.get("data", {}).get("topics", [])
            topics_json = json.dumps(topics, indent=4)
            
            return (
                FunctionResultStatus.DONE,
                f"Successfully retrieved all topics from Allora Network.",
                {
                    "topics": topics_json,
                },
            )
        except Exception as e:
            return (
                FunctionResultStatus.FAILED,
                f"An error occurred while fetching Allora Network topics: {str(e)}",
                {},
            )

    def get_inference_by_topic_id(
        self, topic_id: int, **kwargs
    ):
        """Get inference by topic id."""
        try:
            sig_format = SignatureFormat.ETHEREUM_SEPOLIA.value
            endpoint = f"allora/consumer/{sig_format}?allora_topic_id={topic_id}&inference_value_type=uint256"
            response_data = self.make_api_request(endpoint)
            
            # Извлекаем данные инференса из ответа
            inference_data = response_data.get("data", {}).get("inference_data", {})
            normalized_inference = inference_data.get("network_inference_normalized", "")
            
            return (
                FunctionResultStatus.DONE,
                f"Successfully retrieved inference for topic with id {topic_id}. The inference is: {normalized_inference}",
                {
                    "topic_id": topic_id,
                    "inference": normalized_inference,
                },
            )
        except Exception as e:
            return (
                FunctionResultStatus.FAILED,
                f"An error occurred while fetching inference from Allora Network: {str(e)}",
                {
                    "topic_id": topic_id,
                },
            )

    def get_price_inference(
        self, asset: str, timeframe: str, **kwargs
    ):
        """Get price inference of a given asset for a given timeframe."""
        asset = asset.upper()
        timeframe = timeframe.lower()

        # Проверяем поддерживаемые активы
        supported_assets = [token.value for token in PriceInferenceToken]
        if asset not in supported_assets:
            return (
                FunctionResultStatus.FAILED,
                f"Unsupported asset: {asset}. Supported assets are: {', '.join(supported_assets)}",
                {
                    "asset": asset,
                    "timeframe": timeframe,
                },
            )

        # Проверяем поддерживаемые временные рамки
        supported_timeframes = [tf.value for tf in PriceInferenceTimeframe]
        if timeframe not in supported_timeframes:
            return (
                FunctionResultStatus.FAILED,
                f"Unsupported timeframe: {timeframe}. Supported timeframes are: {', '.join(supported_timeframes)}",
                {
                    "asset": asset,
                    "timeframe": timeframe,
                },
            )

        try:
            sig_format = SignatureFormat.ETHEREUM_SEPOLIA.value
            endpoint = f"allora/consumer/price/{sig_format}/{asset}/{timeframe}"
            response_data = self.make_api_request(endpoint)
            
            # Извлекаем данные инференса из ответа
            inference_data = response_data.get("data", {}).get("inference_data", {})
            normalized_price_inference = inference_data.get("network_inference_normalized", "")
            
            return (
                FunctionResultStatus.DONE,
                f"The price inference for {asset} in {timeframe} is: {normalized_price_inference}",
                {
                    "asset": asset,
                    "timeframe": timeframe,
                    "price_inference": normalized_price_inference,
                },
            )
        except Exception as e:
            print(
                f"An error occurred while fetching price inference from Allora Network: {str(e)}"
            )
            return (
                FunctionResultStatus.FAILED,
                f"An error occurred while fetching price inference from Allora Network: {str(e)}",
                {
                    "asset": asset,
                    "timeframe": timeframe,
                },
            )
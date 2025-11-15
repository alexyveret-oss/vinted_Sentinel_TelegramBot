import asyncio
from api.vinted_api import VintedAPI
from bot.telegram_bot import TelegramBot
from db.product_database import ProductDatabase
import logging

logger = logging.getLogger(__name__)

class VintedMonitor:
    def __init__(self, config):
        self.config = config
        self.db = ProductDatabase()
        self.bot = TelegramBot(config['token'], config['channel_id'])

    async def start_monitoring(self):
        while True:
            try:
                for country_code in self.config['countries']:
                    # Start a new API session for each country
                    self.api = VintedAPI(country_code)
                    
                    for search_term in self.config['search_terms']:
                        logger.debug(f"Searching for term: {search_term} in {country_code}")
                        items = await self.api.search_products(search_term)
                        
                        for item in items:
                            try:
                                item_id = str(item.get('id'))
                                if not item_id or self.db.is_product_seen(item_id):
                                    continue
                                
                                self.db.add_product(item)
                                
                                # Create the message to send to Telegram
                                message_text = self.create_message(item, country_code)
                                
                                # Send the message with image and link
                                self.bot.send_message(
                                    message_text,
                                    image_url=item.get('image_url'),  # Pass the image URL
                                    product_url=item['url']           # Pass the product link
                                )
                                logger.info(f"New product found and posted: {item.get('title')}")
                            except Exception as e:
                                logger.error(f"Error processing item: {str(e)}")
                                continue

                await asyncio.sleep(self.config['refresh_delay'])
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(30)
    
    def create_message(self, item, country_code):
        country_name = self.get_country_name_from_code(country_code)
        
        # Product details
        title = item['title']
        price = item['price']
        url = item['url']
        image_url = item.get('image_url')  # Assume the image is in the 'item' object
        
        # Create the message
        message_text = f"New Product in {country_name}: {title}\nPrice: {price}€\nCountry: {country_name}\nLink: {url}"
        
        return message_text

    def get_country_name_from_code(self, country_code):
        country_map = {
            ".de": "Germany",
            ".it": "Italy",
            ".fr": "France",
            ".es": "Spain",
            ".uk": "United Kingdom"
        }
        return country_map.get(country_code, "Unknown Country")

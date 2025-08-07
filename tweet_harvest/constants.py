import os
from datetime import datetime

TWITTER_SEARCH_URL = "https://x.com/search?q={query}&f=live"

NOW = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
FOLDER_DESTINATION = "tweets-data"
os.makedirs(FOLDER_DESTINATION, exist_ok=True)

FILTERED_FIELDS = [
    "created_at",
    "id_str",
    "full_text",
    "quote_count",
    "reply_count",
    "retweet_count",
    "favorite_count",
    "lang",
    "user_id_str",
    "conversation_id_str",
    "username",
    "tweet_url",
    "image_url",
    "location",
    "in_reply_to_screen_name",
]

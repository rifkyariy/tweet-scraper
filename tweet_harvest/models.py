from pydantic import BaseModel, Field
from typing import List, Optional

# --- MODELS UPDATED TO BE MORE FLEXIBLE ---
class UserCore(BaseModel):
    name: Optional[str] = ""
    screen_name: Optional[str] = ""

class Location(BaseModel):
    location: Optional[str] = ""

class UserLegacy(BaseModel):
    created_at: Optional[str] = ""
    description: Optional[str] = ""
    followers_count: Optional[int] = 0
    friends_count: Optional[int] = 0
    media_count: Optional[int] = 0
    statuses_count: Optional[int] = 0
    profile_image_url_https: Optional[str] = ""

class User(BaseModel):
    legacy: Optional[UserLegacy] = None
    core: Optional[UserCore] = None
    location: Optional[Location] = None

class TweetLegacy(BaseModel):
    created_at: Optional[str] = ""
    conversation_id_str: Optional[str] = ""
    full_text: Optional[str] = ""
    favorite_count: Optional[int] = 0
    quote_count: Optional[int] = 0
    reply_count: Optional[int] = 0
    retweet_count: Optional[int] = 0
    lang: Optional[str] = ""
    id_str: str  # id_str is essential, so we keep it required
    user_id_str: Optional[str] = ""
    in_reply_to_screen_name: Optional[str] = None
    entities: Optional[dict] = {}

class TweetResult(BaseModel):
    rest_id: Optional[str] = ""
    legacy: Optional[TweetLegacy] = None
    core: Optional[dict] = {} 

class TweetItem(BaseModel):
    item_content: Optional[dict] = Field(None, alias='itemContent')
    
class EntryContent(BaseModel):
    item_content: Optional[dict] = Field(None, alias='itemContent')
    items: Optional[List[TweetItem]] = None

class Entry(BaseModel):
    entry_id: str = Field(..., alias='entryId')
    content: Optional[EntryContent] = None
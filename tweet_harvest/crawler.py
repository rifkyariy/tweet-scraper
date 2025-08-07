import csv
import os
import re
import time
from datetime import datetime
from urllib.parse import quote

from pydantic import ValidationError
from playwright.sync_api import sync_playwright, Page, Response
from rich.console import Console
from rich.syntax import Syntax

from .constants import FOLDER_DESTINATION, NOW, FILTERED_FIELDS
from .features.backoff import wait_for_rate_limit
from .features.network import block_media_requests
from .helpers.page_helpers import (log_error, log_info, log_success, scroll_down, log_warning)
from .models import Entry, TweetResult, User

# Initialize Rich Console for better logging
console = Console()

class TwitterCrawler:
    def __init__(self, access_token: str, search_keywords: str = None, from_user: str = None,
                 target_tweet_count: int = 10, output_filename: str = None,
                 from_date: str = None, to_date: str = None,
                 delay_seconds: int = 3, lang: str = None):
        self.access_token = access_token
        self.search_keywords = search_keywords
        self.from_user = from_user
        self.target_tweet_count = target_tweet_count
        self.from_date = from_date
        self.to_date = to_date
        self.delay_seconds = delay_seconds
        self.lang_filter = lang
        
        if self.from_user:
            self.crawl_mode = 'USER'
            log_info(f"Scraping tweets from user: @{self.from_user}")
            filename = (output_filename or f"from_{self.from_user}_{NOW}").replace(" ", "_")
        else:
            self.crawl_mode = 'SEARCH'
            log_info(f"Scraping tweets with keyword: '{self.search_keywords}'")
            filename = (output_filename or f"{self.search_keywords}_{NOW}").replace(" ", "_")

        self.filepath = os.path.join(FOLDER_DESTINATION, f"{filename}.csv")
        
        self.all_tweets = []
        self.rate_limit_attempts = 0
        console.print(f"📝 Out file will be: [bold cyan]{self.filepath}[/]", justify="center")
        if self.lang_filter:
            console.print(f"🌐 Filtering for language: [bold yellow]{self.lang_filter}[/bold yellow]")


    def _build_search_query(self) -> str:
        """Builds the search query string for the URL."""
        console.print("[magenta]Building search query...[/magenta]")
        query = self.search_keywords
        if self.from_date:
            query += f" since:{self.from_date}"
        if self.to_date:
            query += f" until:{self.to_date}"
        return quote(query)

    def _handle_response(self, response: Response):
        """
        This function is called for every network response and routes to the parser.
        """
        if "api/graphql" in response.url and ("SearchTimeline" in response.url or "UserTweets" in response.url) and response.status == 200:
            try:
                response_json = response.json()
                self._parse_and_save(response_json)
            except Exception:
                log_warning(f"Failed to parse a response from {response.url}")

    def _parse_and_save(self, response_json: dict):
        """Parses the JSON response and saves tweet data to a CSV file."""
        entries = []
        
        # --- MODIFIED: Handle both Search and User Profile data structures ---
        if response_json.get("data", {}).get("search_by_raw_query"): # Handling Search Data
            try:
                entries = response_json.get("data", {}).get("search_by_raw_query", {}).get("search_timeline", {}).get("timeline", {}).get("instructions", [{}])[0].get("entries", [])
            except (IndexError, AttributeError): pass
        elif response_json.get("data", {}).get("user"): # Handling User Profile Data
            try:
                instructions = response_json.get("data", {}).get("user", {}).get("result", {}).get("timeline", {}).get("timeline", {}).get("instructions", [])
                for instruction in instructions:
                    if instruction.get("type") == "TimelineAddEntries":
                        entries.extend(instruction.get("entries", []))
                    elif instruction.get("type") == "TimelinePinEntry":
                        entry = instruction.get("entry")
                        if entry:
                            entries.append(entry)
            except (IndexError, AttributeError): pass
        
        if not entries:
            return

        newly_scraped_tweets = []
        for entry_data in entries:
            try:
                entry = Entry.model_validate(entry_data)
                if "tweet" not in entry.entry_id:
                    continue

                if entry.content and entry.content.item_content:
                    tweet_data = entry.content.item_content.get("tweet_results", {}).get("result", {})
                    if not tweet_data: continue

                    user_data = tweet_data.get("core", {}).get("user_results", {}).get("result", {})
                    if not user_data: continue
                    
                    tweet = TweetResult.model_validate(tweet_data)
                    user = User.model_validate(user_data)

                    if self.lang_filter and tweet.legacy and tweet.legacy.lang != self.lang_filter:
                        continue
                    
                    row = self._prepare_csv_row(tweet, user)
                    
                    if row['id_str'] not in {t['id_str'] for t in self.all_tweets}:
                        self.all_tweets.append(row)
                        newly_scraped_tweets.append(row)

            except ValidationError:
                pass 
        
        if newly_scraped_tweets:
            console.print(f"[magenta]Parsed and saved {len(newly_scraped_tweets)} new tweets.[/magenta]")
            self._write_to_csv(newly_scraped_tweets)
            log_info(f"Total tweets scraped: {len(self.all_tweets)} / {self.target_tweet_count}")


    def _prepare_csv_row(self, tweet: TweetResult, user: User) -> dict:
        """Prepares a dictionary for a single CSV row."""
        clean_text = re.sub(r'(\s+|https?://[^\s]+)', ' ', tweet.legacy.full_text, flags=re.MULTILINE).strip()

        username = user.core.screen_name if user.core else ""
        location = user.location.location if user.location else ""
        
        return {
            "created_at": tweet.legacy.created_at if tweet.legacy else "",
            "id_str": tweet.legacy.id_str if tweet.legacy else "",
            "full_text": clean_text,
            "quote_count": tweet.legacy.quote_count if tweet.legacy else 0,
            "reply_count": tweet.legacy.reply_count if tweet.legacy else 0,
            "retweet_count": tweet.legacy.retweet_count if tweet.legacy else 0,
            "favorite_count": tweet.legacy.favorite_count if tweet.legacy else 0,
            "lang": tweet.legacy.lang if tweet.legacy else "",
            "user_id_str": tweet.legacy.user_id_str if tweet.legacy else "",
            "conversation_id_str": tweet.legacy.conversation_id_str if tweet.legacy else "",
            "username": username,
            "tweet_url": f"https://x.com/{username}/status/{tweet.legacy.id_str if tweet.legacy else ''}",
            "image_url": tweet.legacy.entities.get("media", [{}])[0].get("media_url_https", "") if tweet.legacy else "",
            "location": location,
            "in_reply_to_screen_name": tweet.legacy.in_reply_to_screen_name if tweet.legacy else ""
        }

    def _write_to_csv(self, tweets: list):
        """Appends a list of tweets to the CSV file."""
        is_new_file = not os.path.exists(self.filepath)
        with open(self.filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FILTERED_FIELDS)
            if is_new_file:
                writer.writeheader()
            writer.writerows(tweets)
        console.print(f"[magenta]Wrote {len(tweets)} tweets to [bold cyan]{self.filepath}[/bold cyan][/magenta]")


    def crawl(self):
        with sync_playwright() as p:
            console.print("[magenta]🚀 Launching browser...[/magenta]")
            browser = p.firefox.launch(headless=True)
            context = browser.new_context(
                storage_state={
                    "cookies": [
                        {"name": "auth_token", "value": self.access_token, "domain": ".x.com", "path": "/"}
                    ]
                }
            )
            page = context.new_page()
            block_media_requests(page)

            console.print("[magenta]Navigating to X.com to verify login status...[/magenta]")
            page.goto("https://x.com/home", wait_until="domcontentloaded")

            try:
                console.print("[magenta]Checking for login confirmation element...[/magenta]")
                page.wait_for_selector('[data-testid="SideNav_NewTweet_Button"]', timeout=20000)
                log_success("✅ Login successful. Proceeding to scrape.")
            except Exception:
                log_error("Login failed. The auth_token may be invalid or expired.")
                browser.close()
                return

            if self.crawl_mode == 'SEARCH':
                query = self._build_search_query()
                target_url = f"https://x.com/search?q={query}&src=typed_query&f=live"
            else: # USER mode
                target_url = f"https://x.com/{self.from_user}"

            console.print(f"[magenta]Navigating to target URL: [link={target_url}]{target_url}[/link][/magenta]")
            page.goto(target_url, wait_until="domcontentloaded")
            
            page.on("response", self._handle_response)
            
            console.print("[bold cyan]--- Start continuous scrolling loop ---[/bold cyan]")
            
            consecutive_scrolls_with_no_new_tweets = 0
            MAX_NO_NEW_TWEETS_SCROLLS = 5

            while len(self.all_tweets) < self.target_tweet_count:
                tweets_before_scroll = len(self.all_tweets)
                
                scroll_down(page)
                time.sleep(self.delay_seconds)
                
                tweets_after_scroll = len(self.all_tweets)

                if tweets_before_scroll == tweets_after_scroll:
                    consecutive_scrolls_with_no_new_tweets += 1
                else:
                    consecutive_scrolls_with_no_new_tweets = 0

                if consecutive_scrolls_with_no_new_tweets >= MAX_NO_NEW_TWEETS_SCROLLS:
                    log_warning(f"No new tweets found for {MAX_NO_NEW_TWEETS_SCROLLS} consecutive scrolls. Ending session.")
                    break
            
            page.remove_listener("response", self._handle_response)
            
            log_success(f"Crawl finished. Scraped a total of {len(self.all_tweets)} tweets. Data saved to: {self.filepath}")
            browser.close()
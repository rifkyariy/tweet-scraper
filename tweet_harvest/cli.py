import argparse
import os
from dotenv import load_dotenv
import questionary
from rich.console import Console

from .crawler import TwitterCrawler

def main():
    load_dotenv()
    console = Console()

    parser = argparse.ArgumentParser(description="TweetHarvest: A Twitter Crawler")
    parser.add_argument("-t", "--token", help="Twitter auth token (or set TWITTER_AUTH_TOKEN in .env)")
    parser.add_argument("-s", "--search-keyword", help="Search keyword or phrase. Mutually exclusive with --from-user.")
    parser.add_argument("-u", "--from-user", help="Scrape tweets from a specific user profile (e.g., 'elonmusk'). Mutually exclusive with --search-keyword.")
    parser.add_argument("-l", "--limit", type=int, help="Limit number of tweets to crawl")
    parser.add_argument("-f", "--from-date", help="From date (YYYY-MM-DD), only works with --search-keyword")
    parser.add_argument("-to", "--to-date", help="To date (YYYY-MM-DD), only works with --search-keyword")
    parser.add_argument("-o", "--output-filename", help="Output filename (without extension)")
    parser.add_argument("--lang", help="Filter tweets by language (e.g., 'en' for English, 'es' for Spanish)")
    
    args = parser.parse_args()

    # --- Mode Validation ---
    if args.search_keyword and args.from_user:
        console.print("[bold red]Error: Please provide either --search-keyword or --from-user, but not both.[/]")
        return
        
    if not args.search_keyword and not args.from_user:
        console.print("[bold red]Error: You must provide a --search-keyword or a --from-user to start scraping.[/]")
        return

    auth_token = args.token or os.getenv("TWITTER_AUTH_TOKEN")
    if not auth_token:
        auth_token = questionary.password("What's your Twitter auth token?").ask()

    limit = args.limit
    if not limit:
        limit_str = questionary.text("How many tweets do you want to crawl?", default="100").ask()
        limit = int(limit_str)

    if not all([auth_token, limit]):
        console.print("[bold red]Missing required information. Exiting.[/]")
        return
        
    crawler = TwitterCrawler(
        access_token=auth_token,
        search_keywords=args.search_keyword,
        from_user=args.from_user,
        target_tweet_count=limit,
        from_date=args.from_date,
        to_date=args.to_date,
        output_filename=args.output_filename,
        lang=args.lang 
    )
    crawler.crawl()

if __name__ == "__main__":
    main()
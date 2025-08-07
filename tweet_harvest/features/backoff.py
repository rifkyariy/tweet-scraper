import time

def wait_for_rate_limit(attempt: int, base_timeout_secs: int = 60, max_timeout_secs: int = 600) -> int:
    """Calculates and waits for an exponential backoff period."""
    wait_time = min(base_timeout_secs * (2 ** attempt), max_timeout_secs)
    
    from tweet_harvest.helpers.page_helpers import log_warning
    log_warning(f"Rate limit hit. Waiting for {wait_time} seconds before retrying...")
    time.sleep(wait_time)
    return wait_time

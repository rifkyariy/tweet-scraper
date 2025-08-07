from playwright.sync_api import Page
from rich.console import Console

console = Console()

def scroll_down(page: Page):
    """Scrolls to the bottom by simulating a key press and removes media."""
    
    # --- MODIFIED SCROLLING LOGIC ---
    # Pressing the 'End' key is a more reliable way to scroll on complex pages.
    # It simulates a user directly asking the browser to go to the end of the content.
    console.print("[magenta]Simulating 'End' key press to scroll...[/magenta]")
    page.keyboard.press("End")
    # Wait a moment for the page to react and load new content
    page.wait_for_timeout(2000)
    # --- END OF MODIFIED LOGIC ---

    # Remove images/videos to prevent memory overload
    page.evaluate("""
        () => {
            const mediaSelectors = [
                'div[data-testid="tweetPhoto"]', 
                'div[aria-label="Image"]',
                'div[aria-label="Embedded video"]'
            ];
            document.querySelectorAll(mediaSelectors.join(', ')).forEach(el => el.remove());
        }
    """)
    
def log_error(message: str):
    """Logs an error message to the console with rich formatting."""
    console.print(f"[bold red]ERROR:[/] {message}")

def log_info(message: str):
    """Logs an info message to the console with rich formatting."""
    console.print(f"[bold blue]INFO:[/] {message}")

def log_success(message: str):
    """Logs a success message to the console."""
    console.print(f"[bold green]SUCCESS:[/] {message}")

def log_warning(message: str):
    """Logs a warning message to the console."""
    console.print(f"[bold yellow]WARN:[/] {message}")
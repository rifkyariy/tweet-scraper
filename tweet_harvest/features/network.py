from playwright.sync_api import Page, Route

def block_media_requests(page: Page):
    """Block requests for images and videos to speed up scraping."""
    def handle_route(route: Route):
        if route.request.resource_type in ["image", "media", "font"]:
            route.abort()
        else:
            route.continue_()
    
    page.route("**/*", handle_route)

import cloudscraper

from .constants import MAX_CONCURRENT_REQUESTS

scraper = cloudscraper.create_scraper(
    interpreter='js2py',
    delay=5,
    max_concurrent_requests=MAX_CONCURRENT_REQUESTS + 1,
    enable_stealth=True,
    stealth_options={
        'min_delay': 2.0,
        'max_delay': 6.0,
        'human_like_delays': True,
        'randomize_headers': True,
        'browser_quirks': True,
    },
    browser='chrome',
)

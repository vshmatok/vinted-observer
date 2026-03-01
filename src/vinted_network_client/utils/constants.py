from typing import Final


SESSION_COOKIE_NAME: Final[str] = "access_token_web"
TIMEOUT_SECONDS: Final[int] = 10
BASE_DOMAIN: Final[str] = "https://www.vinted"
REQUEST_RETRIES: Final[int] = 3
RETRY_STATUS_CODES: Final[list[int]] = [401, 429]

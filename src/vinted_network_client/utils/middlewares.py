import aiohttp
import logging

logger = logging.getLogger(__name__)


async def logging_middleware(
    req: aiohttp.ClientRequest, handler: aiohttp.ClientHandlerType
) -> aiohttp.ClientResponse:
    logger.info(
        f"Request: [{req.method}] {req.url}\n"
        f"Proxy: {req.proxy}\n"
        f"Headers: {str(dict(req.headers))}\n"
        f"Parameters: {str(dict(req.url.query))}"
    )
    resp = await handler(req)

    log_message = (
        f"Response: [{resp.method}] {resp.url}\n"
        f"Proxy: {req.proxy}\n"
        f"Status: {resp.status} {resp.reason}"
    )

    if resp.status >= 400:
        try:
            error_body = await resp.text()
            log_message += f"\nError Message: {error_body}"
        except Exception as e:
            log_message += f"\nCould not read error body: {e}"

        logger.error(log_message)
    else:
        logger.info(log_message)

    return resp

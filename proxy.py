import asyncio
import time
from aiohttp import web, ClientSession, ClientError, ClientTimeout
from itertools import cycle

from logger import setup_logger

from dotenv import load_dotenv
import os

load_dotenv()  # loads variables from .env

logger = setup_logger("proxy")

BACKENDS = [
    os.getenv("BACKEND_1", "http://127.0.0.1:9001"),
    os.getenv("BACKEND_2", "http://127.0.0.1:9002"),
]

backend_pool = cycle(BACKENDS)
MAX_RETRIES = int(os.getenv("MAX_RETRIES", len(BACKENDS)))

# TIMEOUT CONFIG
TIMEOUT = ClientTimeout(
    total=float(os.getenv("REQUEST_TIMEOUT_TOTAL", 1.5)),
    connect=float(os.getenv("REQUEST_TIMEOUT_CONNECT", 0.5))
)

PROXY_PORT = int(os.getenv("PROXY_PORT", 8080))


async def proxy_handler(request):
    start_time = time.perf_counter()
    body = await request.read()

    for attempt in range(MAX_RETRIES):
        backend = next(backend_pool)
        target_url = f"{backend}{request.rel_url}"

        logger.info(f"Attempt {attempt + 1} -> {backend}")

        try:
            async with ClientSession(timeout=TIMEOUT) as session:
                async with session.request(
                    method=request.method,
                    url=target_url,
                    headers=request.headers,
                    data=body,
                ) as resp:

                    response_body = await resp.read()
                    duration_ms = (time.perf_counter() - start_time) * 1000

                    logger.info(
                        f"Success | backend={backend} | "
                        f"status={resp.status} | "
                        f"latency={duration_ms:.2f}ms"
                    )

                    return web.Response(
                        body=response_body,
                        status=resp.status,
                        headers=resp.headers
                    )

        except asyncio.TimeoutError:
            logger.warning(f"Backend timeout: {backend}")

        except ClientError as e:
            logger.error(f"Backend failed: {backend} | error={e}")


    duration_ms = (time.perf_counter() - start_time) * 1000
    logger.critical(
        f"All backends down | latency={duration_ms:.2f}ms"
    )

    return web.Response(
        status=502,
        text="Bad Gateway: All backend servers are unavailable"
    )


app = web.Application()
app.router.add_route("*", "/{tail:.*}", proxy_handler)

if __name__ == "__main__":
    logger.info("Starting proxy server on port 8080")
    web.run_app(app, host="127.0.0.1", port=PROXY_PORT)

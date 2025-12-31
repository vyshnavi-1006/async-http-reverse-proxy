from aiohttp import web
from logger import setup_logger

logger = setup_logger("backend-2")

async def handle(request):
    logger.info(f"Received request: {request.method} {request.path}")
    return web.json_response({
        "backend": "backend-2",
        "message": "Hello from backend 2"
    })

app = web.Application()
app.router.add_route("*", "/{tail:.*}", handle)

if __name__ == "__main__":
    logger.info("Starting backend-2 on port 9002")
    web.run_app(app, host="127.0.0.1", port=9002)

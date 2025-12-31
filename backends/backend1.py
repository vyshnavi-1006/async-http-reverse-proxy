from aiohttp import web
from logger import setup_logger

logger = setup_logger("backend-1")  # unique name per backend

async def handle(request):
    logger.info(f"Received request: {request.method} {request.path}")
    return web.json_response({
        "backend": "backend-1",
        "message": "Hello from backend 1"
    })

app = web.Application()
app.router.add_route("*", "/{tail:.*}", handle)

if __name__ == "__main__":
    logger.info("Starting backend-1 on port 9001")
    web.run_app(app, host="127.0.0.1", port=9001)

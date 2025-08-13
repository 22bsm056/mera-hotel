from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import config as Config

app = FastAPI()

VERIFY_TOKEN = Config.INSTAGRAM_APP_SECRET  # Your Instagram verify token

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge)
    else:
        return PlainTextResponse("Webhook verification failed", status_code=403)

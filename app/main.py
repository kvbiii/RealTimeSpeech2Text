from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles


from utils.base_logger import logger
from client import Client
from transcription_utils.speech2text import Speech2TextPipeline
from transcription_utils.voice_detection import VoiceActivityDetectionPipeline

app = FastAPI(
    title="Whisper API",
    description="API for real time speech to text transcription",
    debug=True,
)
app.mount("/app/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up the application")
    global client
    client = Client(
        speech2text_pipeline=Speech2TextPipeline(),
        vad_pipeline=VoiceActivityDetectionPipeline(),
        sampling_rate=16000,
        samples_width=2,
        chunk_length_seconds=2.5,
        chunk_offset_seconds=0.1,
    )


@app.get("/", response_class=HTMLResponse)
def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/listen")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await client.handle_websocket(websocket)

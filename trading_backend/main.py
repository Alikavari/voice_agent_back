# app/main.py
import os
from turtle import position
import uuid
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import aiofiles
from contextlib import asynccontextmanager
import assemblyai as aai
from dotenv import load_dotenv
import os

# import requests
import time
from .llm_agent.agent import generate_trade_command

# --- Configuration ---
UPLOAD_DIR = "uploads"
aii_config = []
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit (adjust as needed)
ALLOWED_CONTENT_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/mpeg",
    "audio/ogg",
    "audio/x-wav",
}
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
    aii_config.append(aai.TranscriptionConfig(speech_model=aai.SpeechModel.universal))

    print("starting service")
    yield
    print("🛑 Shutting down... cleanup if needed")


# --- App init ---
app = FastAPI(title="Voice Upload API", lifespan=lifespan)

# TODO: remove
# # Update origins to include the dev server(s) you use (Vite typically runs on 5173)
# origins = [
#     "http://localhost:5173",
#     "http://localhost:3000",
#     "http://localhost:8000",
#     "http://127.0.0.1:5173",
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)


@app.get("/")
async def root():
    return {"status": "ok"}


@app.post("/upload")
async def upload_voice(voice: UploadFile = File(...)):
    """
    Accepts multipart/form-data with field `voice` (UploadFile).
    Saves file to uploads/ with a UUID prefix; returns JSON with filename & size.
    """
    # 1) basic validation
    if voice.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400, detail=f"Unsupported content type: {voice.content_type}"
        )

    # create safe file name
    unique_name = f"{uuid.uuid4().hex}_{voice.filename}"
    dest_path = os.path.join(UPLOAD_DIR, unique_name)

    # 2) stream-save file with size check
    size = 0
    try:
        async with aiofiles.open(dest_path, "wb") as out_file:
            while True:
                chunk = await voice.read(1024 * 1024)  # read 1MB at a time
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    # clean up partial file
                    await out_file.close()
                    os.remove(dest_path)
                    raise HTTPException(status_code=413, detail="File too large")
                await out_file.write(chunk)
            logging.info(f"file has been saved as name {unique_name}")
            time.sleep(1)
            ##   ---   Starting STT service
            print(len(aii_config))
            transcript = aai.Transcriber(config=aii_config[0]).transcribe(
                "./uploads/" + unique_name
            )
            print("the trnscript:   ", transcript.text)
            if transcript.text:
                json_out = generate_trade_command(transcript.text)
                if json_out:
                    print("json out :   ", json_out)
                    amount = json_out.amount
                    token = json_out.token
                    leverage = json_out.leverage
                    position = json_out.position
                    return {
                        "amount": amount,
                        "token": token,
                        "leverage": leverage,
                        "position": position,
                    }
    except HTTPException:
        raise
    except Exception as exc:
        logging.exception("Failed to save uploaded file")
        # ensure no half-file remains
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except OSError:
                pass
        raise HTTPException(status_code=500, detail="Internal server error")

    logging.info("Saved upload: %s (%d bytes)", dest_path, size)

    # return transcript.text
    # return {"filename": unique_name, "content_type": voice.content_type, "size": size}
    return {"amount": 10, "token": "BTC", "leverage": 5, "position": "long"}


def main():
    import uvicorn
    uvicorn.run("trading_backend.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()

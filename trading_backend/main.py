# app/main.py
import os
import uuid
import logging
import time
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import aiofiles
from contextlib import asynccontextmanager
import assemblyai as aai
from dotenv import load_dotenv
from llm_agent.agent import generate_trade_command
from deepgram import DeepgramClient
from deepgram import PrerecordedOptions, FileSource, DeepgramClient

# --- Configuration ---
UPLOAD_DIR = "uploads"
aii_config = []
deepgram_handler = []
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/mpeg",
    "audio/ogg",
    "audio/x-wav",
}
load_dotenv()
stt = os.getenv("STT")


@asynccontextmanager
async def lifespan(app: FastAPI):
    aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
    aii_config.append(aai.TranscriptionConfig(speech_model=aai.SpeechModel.universal))
    deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
    deepgram_handler.append(DeepgramClient(deepgram_api_key))

    print(f"🚀 Starting service wit {stt} STT")
    yield
    print("🛑 Shutting down... cleanup if needed")


# --- App init ---
app = FastAPI(title="Voice Upload API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)


async def deepgram_stt(deepgram, file_dir):
    async with aiofiles.open(file_dir, mode="rb") as f:
        buffer_data = await f.read()

    payload: FileSource = {
        "buffer": buffer_data,
    }

    options = PrerecordedOptions(model="nova-3")

    # Async transcription request
    response = await deepgram.listen.asyncrest.v("1").transcribe_file(payload, options)
    return response


@app.get("/")
async def root():
    return {"status": "ok"}


@app.post("/upload")
async def upload_voice(voice: UploadFile = File(...)):
    if voice.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400, detail=f"Unsupported content type: {voice.content_type}"
        )

    unique_name = f"{uuid.uuid4().hex}_{voice.filename}"
    dest_path = os.path.join(UPLOAD_DIR, unique_name)

    size = 0
    try:
        async with aiofiles.open(dest_path, "wb") as out_file:
            while True:
                chunk = await voice.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    await out_file.close()
                    os.remove(dest_path)
                    raise HTTPException(status_code=413, detail="File too large")
                await out_file.write(chunk)

        logging.info(f"✅ File saved as {unique_name}")

        # --- STT timing ---
        stt_start = time.perf_counter()
        if stt == "ASSEMBLY_AI":
            transcript = (
                aai.Transcriber(config=aii_config[0]).transcribe(dest_path).text
            )
        else:
            response = await deepgram_stt(
                deepgram=deepgram_handler[0], file_dir=dest_path
            )
            transcript = response["results"]["channels"][0]["alternatives"][0][
                "transcript"
            ]
        stt_end = time.perf_counter()
        logging.info(f"🕒 STT response time: {stt_end - stt_start:.2f} sec")

        if True:
            # --- OpenAI timing ---
            openai_start = time.perf_counter()
            json_out = generate_trade_command(transcript)
            logging.info(f"the json output: {json_out}")
            openai_end = time.perf_counter()
            logging.info(
                f"🕒 OpenAI response time: {openai_end - openai_start:.2f} sec"
            )

            if json_out:
                return {
                    "amount": json_out.amount,
                    "token": json_out.token,
                    "leverage": json_out.leverage,
                    "position": json_out.position,
                    "assemblyai_duration": round(stt_end - stt_start, 2),
                    "openai_duration": round(openai_end - openai_start, 2),
                }

    except HTTPException:
        raise
    except Exception as exc:
        logging.exception("❌ Failed to process uploaded file")
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except OSError:
                pass
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"amount": 10, "token": "BTC", "leverage": 5, "position": "long"}


def main():
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()

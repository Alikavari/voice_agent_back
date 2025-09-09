# Install the assemblyai package by executing the command "pip install assemblyai"

import assemblyai as aai

aai.settings.api_key = "a5594b783178462c97da7ca5764bd3ca"

# audio_file = "./local_file.mp3"
audio_file = "./uploads/11f6b16029494daf8abfb6afa8e57ecc_recording.webm"

config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.universal)

transcript = aai.Transcriber(config=config).transcribe(audio_file)

if transcript.status == "error":
    raise RuntimeError(f"Transcription failed: {transcript.error}")

print(transcript.text)

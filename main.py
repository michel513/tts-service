import asyncio
import io
import os
from typing import Annotated
from fastapi import FastAPI, Query, HTTPException, Security, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
import edge_tts
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TTS_API_KEY = os.getenv("TTS_API_KEY", "default-secret-key-change-me")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == TTS_API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
    )

app = FastAPI(
    title="TCF Express TTS API",
    description="Service de génération de voix haute qualité pour la plateforme TCF Express.",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "TCF Express TTS Service is running. Access /docs for API documentation."}

@app.get("/speak", tags=["TTS"])
async def speak(
    text: Annotated[str, Query(description="Le texte à convertir en parole")],
    voice: Annotated[str, Query(description="Le nom de la voix edge-tts (ex: fr-FR-DeniseNeural)")] = "fr-FR-DeniseNeural",
    api_key: str = Depends(get_api_key)
):
    """
    Génère un flux audio MP3 à partir du texte fourni.
    Nécessite une clé API valide dans l'en-tête 'X-API-Key'.
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Le texte ne peut pas être vide")

    try:
        communicate = edge_tts.Communicate(text, voice)
        
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])
        
        audio_data.seek(0)
        
        return StreamingResponse(
            audio_data, 
            media_type="audio/mpeg",
            headers={"Content-Disposition": 'inline; filename="speech.mp3"'}
        )
    except Exception as e:
        print(f"Error generating TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/voices", tags=["TTS"])
async def list_voices(api_key: str = Depends(get_api_key)):
    """Retourne la liste complète des voix disponibles chez Microsoft Edge TTS."""
    try:
        voices = await edge_tts.VoicesManager.create()
        return voices.voices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Use PORT from environment variable or default to 8000
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
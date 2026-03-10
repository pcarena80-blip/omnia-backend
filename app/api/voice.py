from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import uuid
import os
import sys
import base64
import asyncio

# Need to ensure we can import the agent
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'desktop'))
try:
    from local_agent import run_agent
except ImportError:
    run_agent = None

from openai import OpenAI
import edge_tts

router = APIRouter(prefix="/api/voice", tags=["Voice"])

@router.post("")
async def handle_voice(audio: UploadFile = File(...)):
    if not run_agent:
        raise HTTPException(status_code=500, detail="Cannot load Llama-3 Agent from desktop folder.")

    temp_m4a = f"temp_mobile_{uuid.uuid4().hex[:8]}.m4a"
    try:
        # Save incoming audio snippet
        with open(temp_m4a, "wb") as buffer:
            buffer.write(await audio.read())
            
        # 1. Transcribe with Whisper
        groq_client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"), 
            base_url="https://api.groq.com/openai/v1"
        )
        
        with open(temp_m4a, "rb") as af:
            transcription = groq_client.audio.transcriptions.create(
                file=(temp_m4a, af.read()),
                model="whisper-large-v3-turbo",
                prompt="Transcribe the mobile user's voice command natively. English or Urdu or mixed. Words might include 'Ali', 'gana suna do'.",
                temperature=0.0
            )
            
        user_text = transcription.text.strip()
        if not user_text:
            return JSONResponse(status_code=400, content={"error": "No speech detected"})
            
        print(f"📱 Mobile User (Cloud REST): {user_text}")
        
        # 2. Process with Llama-3 Agent
        # Normally would load DB history here for a multi-user cloud app, but keeping single-user logic for now
        history = []
        ai_response = run_agent(user_text, history)
        print(f"🧠 Cloud Brain: {ai_response}")
        
        # 3. Generate Audio Response (Edge-TTS)
        import re
        voice_name = "ur-PK-UzmaNeural" if bool(re.search(r'[\u0600-\u06FF]', ai_response)) else "en-US-JennyNeural"
        temp_mp3 = f"temp_mobile_response_{uuid.uuid4().hex[:8]}.mp3"
        
        communicate = edge_tts.Communicate(ai_response, voice_name)
        await communicate.save(temp_mp3)
        
        # Read back as base64 for mobile 
        with open(temp_mp3, "rb") as mf:
            audio_base64 = base64.b64encode(mf.read()).decode('utf-8')
            
        return {
            "transcription": user_text,
            "response": ai_response,
            "audio_base64": audio_base64
        }
        
    except Exception as e:
        print(f"Cloud API Voice Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_m4a):
            os.remove(temp_m4a)
        temp_mp3 = f"temp_mobile_response_{uuid.uuid4().hex[:8]}.mp3"
        if os.path.exists(temp_mp3):
            os.remove(temp_mp3)

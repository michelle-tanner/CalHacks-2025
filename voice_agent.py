# voice_mental_health_agent.py
from uagents import Agent, Context, Model
from uagents.setup import fund_agent_if_low
from typing import Dict, List, Optional, Tuple
import json
import re
from datetime import datetime
import asyncio
import base64
import audioop
import numpy as np
from scipy import stats
import speech_recognition as sr
from gtts import gTTS
import pygame
import io
import threading

# Data Models
class VoiceMessage(Model):
    audio_data: str  # base64 encoded audio
    session_id: str
    age: Optional[int] = None
    timestamp: str

class VoiceResponse(Model):
    audio_response: str  # base64 encoded audio response
    text_response: str
    tone_analysis: Dict
    concerns_detected: List[str] = []
    safety_alert: bool = False
    session_id: str

class ToneAnalysis(Model):
    emotional_tone: str
    confidence: float
    features: Dict
    risk_indicator: bool

# Initialize the agent
voice_mental_health_agent = Agent(
    name="voice_mental_health_support",
    port=8001,
    endpoint=["http://localhost:8001/submit"],
    seed="voice_mental_health_agent_seed_456"
)

fund_agent_if_low(voice_mental_health_agent.wallet.address())

class VoiceProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        # Calibrate microphone for ambient noise
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
        
    def record_audio(self, duration: int = 5) -> Optional[bytes]:
        """Record audio from microphone"""
        try:
            print("🎤 Listening...")
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=duration)
            return audio.get_wav_data()
        except sr.WaitTimeoutError:
            print("No speech detected")
            return None
        except Exception as e:
            print(f"Recording error: {e}")
            return None
    
    def audio_to_text(self, audio_data: bytes) -> Tuple[Optional[str], float]:
        """Convert audio to text with confidence score"""
        try:
            audio = sr.AudioData(audio_data, 16000, 2)  # 16kHz, 16-bit
            text = self.recognizer.recognize_google(audio)
            confidence = 0.8  # Placeholder - Google API doesn't return confidence
            return text, confidence
        except sr.UnknownValueError:
            return None, 0.0
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            return None, 0.0
    
    def text_to_speech(self, text: str) -> bytes:
        """Convert text to speech audio"""
        try:
            tts = gTTS(text=text, lang='en', slow=False)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            return audio_buffer.read()
        except Exception as e:
            print(f"TTS error: {e}")
            return None
    
    def play_audio(self, audio_data: bytes):
        """Play audio through speakers"""
        try:
            audio_buffer = io.BytesIO(audio_data)
            pygame.mixer.init()
            pygame.mixer.music.load(audio_buffer)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
        except Exception as e:
            print(f"Audio playback error: {e}")

class ToneAnalyzer:
    def __init__(self):
        self.emotional_indicators = {
            'sad': ['low pitch', 'slow speech', 'monotone', 'quiet'],
            'anxious': ['high pitch', 'fast speech', 'trembling', 'stuttering'],
            'angry': ['loud', 'sharp tones', 'fast pace', 'high intensity'],
            'happy': ['varied pitch', 'moderate pace', 'clear articulation', 'energetic'],
            'calm': ['steady pitch', 'moderate pace', 'smooth', 'consistent volume']
        }
    
    def analyze_audio_features(self, audio_data: bytes) -> Dict:
        """Analyze audio features for emotional tone"""
        try:
            # Convert to numpy array for analysis
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Basic audio features
            features = {
                'volume_mean': np.mean(np.abs(audio_array)),
                'volume_std': np.std(audio_array),
                'pitch_variance': self._calculate_pitch_variance(audio_array),
                'speech_rate': self._estimate_speech_rate(audio_array),
                'clarity': self._calculate_clarity(audio_array)
            }
            
            return features
        except Exception as e:
            print(f"Audio analysis error: {e}")
            return {}
    
    def _calculate_pitch_variance(self, audio_data: np.array) -> float:
        """Calculate pitch variance as emotional indicator"""
        try:
            # Simple pitch estimation using zero-crossing rate
            zero_crossings = np.where(np.diff(np.signbit(audio_data)))[0]
            if len(zero_crossings) > 1:
                return np.std(np.diff(zero_crossings))
            return 0.0
        except:
            return 0.0
    
    def _estimate_speech_rate(self, audio_data: np.array) -> float:
        """Estimate speech rate from audio energy"""
        try:
            # Calculate energy variations
            energy = audio_data.astype(float) ** 2
            energy_std = np.std(energy)
            return min(energy_std / 1000, 1.0)  # Normalize
        except:
            return 0.5
    
    def _calculate_clarity(self, audio_data: np.array) -> float:
        """Calculate speech clarity"""
        try:
            # Simple clarity measure using signal-to-noise ratio approximation
            rms = np.sqrt(np.mean(audio_data**2))
            if rms > 0:
                return min(rms / 10000, 1.0)
            return 0.5
        except:
            return 0.5
    
    def detect_emotional_tone(self, audio_features: Dict, text: str) -> ToneAnalysis:
        """Detect emotional tone from audio features and text"""
        emotional_scores = {
            'sad': 0.0,
            'anxious': 0.0, 
            'angry': 0.0,
            'happy': 0.0,
            'calm': 0.0
        }
        
        # Analyze based on audio features
        if audio_features.get('volume_mean', 0) < 1000:
            emotional_scores['sad'] += 0.3
        elif audio_features.get('volume_mean', 0) > 5000:
            emotional_scores['angry'] += 0.3
        
        if audio_features.get('pitch_variance', 0) > 50:
            emotional_scores['anxious'] += 0.3
        elif audio_features.get('pitch_variance', 0) < 10:
            emotional_scores['sad'] += 0.2
        
        if audio_features.get('speech_rate', 0) > 0.7:
            emotional_scores['anxious'] += 0.3
        elif audio_features.get('speech_rate', 0) < 0.3:
            emotional_scores['sad'] += 0.2
        
        # Text-based emotional analysis
        text_lower = text.lower()
        sad_words = ['sad', 'unhappy', 'cry', 'miserable', 'hopeless']
        anxious_words = ['worried', 'nervous', 'scared', 'anxious', 'afraid']
        angry_words = ['angry', 'mad', 'hate', 'frustrated', 'upset']
        happy_words = ['happy', 'good', 'great', 'excited', 'love']
        
        for word in sad_words:
            if word in text_lower:
                emotional_scores['sad'] += 0.2
        
        for word in anxious_words:
            if word in text_lower:
                emotional_scores['anxious'] += 0.2
        
        for word in angry_words:
            if word in text_lower:
                emotional_scores['angry'] += 0.2
        
        for word in happy_words:
            if word in text_lower:
                emotional_scores['happy'] += 0.2
        
        # Determine dominant emotion
        dominant_emotion = max(emotional_scores, key=emotional_scores.get)
        confidence = emotional_scores[dominant_emotion]
        
        # Risk indicator for concerning emotional states
        risk_indicator = dominant_emotion in ['sad', 'anxious', 'angry'] and confidence > 0.5
        
        return ToneAnalysis(
            emotional_tone=dominant_emotion,
            confidence=confidence,
            features=audio_features,
            risk_indicator=risk_indicator
        )

class VoiceMentalHealthEngine:
    def __init__(self):
        self.voice_processor = VoiceProcessor()
        self.tone_analyzer = ToneAnalyzer()
        self.conversation_sessions = {}
        
        # Response templates with emotional awareness
        self.emotional_responses = {
            'sad': [
                "I hear the sadness in your voice. It's okay to feel this way. Would you like to talk about what's making you feel sad?",
                "That sounds really difficult. I can hear you're feeling down. What usually helps when you feel this way?",
                "Your feelings are completely valid. I'm here to listen whenever you're ready to share more."
            ],
            'anxious': [
                "I can hear some worry in your voice. Would it help to take a deep breath together?",
                "It sounds like you're feeling anxious. What's been on your mind that's causing these worries?",
                "I understand that anxious feeling. Sometimes talking about it can help make it feel smaller."
            ],
            'angry': [
                "I can hear the frustration in your voice. It's okay to feel angry. Want to talk about what's bothering you?",
                "That sounds really frustrating. What would help you feel better right now?",
                "Anger is a normal emotion. Let's figure out what's behind these feelings together."
            ],
            'happy': [
                "It's great to hear the happiness in your voice! What's been making you feel good lately?",
                "I love hearing you sound so positive! Want to share what's been going well?",
                "Your happy energy is wonderful! What's been the best part of your day?"
            ],
            'calm': [
                "You sound very thoughtful. What's on your mind today?",
                "I appreciate how clearly you're expressing yourself. What would you like to talk about?",
                "You seem very centered today. How have things been going for you?"
            ]
        }
    
    def process_voice_message(self, audio_data: bytes, session_id: str, age: Optional[int]) -> VoiceResponse:
        """Process voice message and generate response"""
        # Convert speech to text
        text, confidence = self.voice_processor.audio_to_text(audio_data)
        
        if not text:
            return self._generate_fallback_response()
        
        # Analyze tone from audio
        audio_features = self.tone_analyzer.analyze_audio_features(audio_data)
        tone_analysis = self.tone_analyzer.detect_emotional_tone(audio_features, text)
        
        # Generate appropriate text response
        text_response = self._generate_emotional_response(text, tone_analysis, age)
        
        # Convert response to speech
        audio_response = self.voice_processor.text_to_speech(text_response)
        
        # Detect concerns from text
        concerns = self._detect_concerns(text)
        safety_alert = self._check_safety_concerns(text)
        
        # Update session
        self._update_session(session_id, text, tone_analysis, concerns)
        
        return VoiceResponse(
            audio_response=base64.b64encode(audio_response).decode() if audio_response else "",
            text_response=text_response,
            tone_analysis={
                'emotional_tone': tone_analysis.emotional_tone,
                'confidence': tone_analysis.confidence,
                'risk_indicator': tone_analysis.risk_indicator
            },
            concerns_detected=concerns,
            safety_alert=safety_alert,
            session_id=session_id
        )
    
    def _generate_emotional_response(self, text: str, tone_analysis: ToneAnalysis, age: Optional[int]) -> str:
        """Generate response based on emotional tone"""
        emotional_tone = tone_analysis.emotional_tone
        
        # Get emotional response template
        if emotional_tone in self.emotional_responses:
            import random
            base_response = random.choice(self.emotional_responses[emotional_tone])
        else:
            base_response = "Thanks for sharing that with me. Can you tell me more about how you're feeling?"
        
        # Age-appropriate adjustments
        if age and age < 7:
            base_response = self._simplify_language(base_response)
        
        return base_response
    
    def _simplify_language(self, text: str) -> str:
        """Simplify language for young children"""
        simplifications = {
            'frustrated': 'upset',
            'anxious': 'worried', 
            'difficult': 'hard',
            'completely valid': 'okay',
            'centered': 'good'
        }
        
        for complex_word, simple_word in simplifications.items():
            text = text.replace(complex_word, simple_word)
        
        return text
    
    def _detect_concerns(self, text: str) -> List[str]:
        """Detect mental health concerns from text"""
        concerns = []
        text_lower = text.lower()
        
        concern_patterns = {
            'depression': ['sad', 'hopeless', 'tired', 'no energy', 'cant sleep'],
            'anxiety': ['worried', 'nervous', 'scared', 'panic', 'anxious'],
            'self_harm': ['hurt myself', 'cut myself', 'want to die'],
            'bullying': ['tease me', 'bullied', 'no friends', 'everyone hates']
        }
        
        for concern, keywords in concern_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                concerns.append(concern)
        
        return concerns
    
    def _check_safety_concerns(self, text: str) -> bool:
        """Check for immediate safety concerns"""
        safety_keywords = ['kill myself', 'suicide', 'hurt myself', 'want to die']
        return any(keyword in text.lower() for keyword in safety_keywords)
    
    def _generate_fallback_response(self) -> VoiceResponse:
        """Generate response when speech isn't understood"""
        fallback_text = "I didn't quite catch that. Could you please try saying it again?"
        fallback_audio = self.voice_processor.text_to_speech(fallback_text)
        
        return VoiceResponse(
            audio_response=base64.b64encode(fallback_audio).decode() if fallback_audio else "",
            text_response=fallback_text,
            tone_analysis={'emotional_tone': 'unknown', 'confidence': 0.0, 'risk_indicator': False},
            concerns_detected=[],
            safety_alert=False,
            session_id="fallback"
        )
    
    def _update_session(self, session_id: str, text: str, tone_analysis: ToneAnalysis, concerns: List[str]):
        """Update conversation session"""
        if session_id not in self.conversation_sessions:
            self.conversation_sessions[session_id] = {
                'history': [],
                'emotional_patterns': [],
                'start_time': datetime.now()
            }
        
        session = self.conversation_sessions[session_id]
        session['history'].append({
            'text': text,
            'tone': tone_analysis.emotional_tone,
            'confidence': tone_analysis.confidence,
            'timestamp': datetime.now(),
            'concerns': concerns
        })
        session['emotional_patterns'].append(tone_analysis.emotional_tone)

# Initialize the engine
voice_engine = VoiceMentalHealthEngine()

@voice_mental_health_agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"Voice Mental Health Agent started: {voice_mental_health_agent.name}")
    ctx.logger.info(f"Agent address: {voice_mental_health_agent.address}")

@voice_mental_health_agent.on_message(model=VoiceMessage)
async def handle_voice_message(ctx: Context, sender: str, msg: VoiceMessage):
    ctx.logger.info(f"Received voice message from {sender}")
    
    # Decode audio data
    audio_data = base64.b64decode(msg.audio_data)
    
    # Process voice message
    response = voice_engine.process_voice_message(audio_data, msg.session_id, msg.age)
    
    # Send response back
    await ctx.send(sender, response)
    
    ctx.logger.info(f"Sent voice response with tone: {response.tone_analysis['emotional_tone']}")

if __name__ == "__main__":
    voice_mental_health_agent.run()
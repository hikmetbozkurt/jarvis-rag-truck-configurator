import speech_recognition as sr
import pyttsx3
import threading

class VoiceEngine:
    def __init__(self):
        # Initialize Text-to-Speech engine
        self.tts_engine = pyttsx3.init()
        self.setup_voice()
        
        # Initialize Speech Recognizer
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

    def setup_voice(self):
        """Configure the voice properties to sound like an expert specialist."""
        voices = self.tts_engine.getProperty('voices')
        # Try to find a clear, professional voice (usually the first one on macOS/Windows)
        self.tts_engine.setProperty('voice', voices[0].id)
        self.tts_engine.setProperty('rate', 175)  # Slightly slower for clarity
        self.tts_engine.setProperty('volume', 0.9)

    def speak(self, text):
        """Speak the text in a separate thread to avoid blocking the main loop."""
        print(f"Jarvis is speaking...")
        # Clean text of JSON or special formatting for better speech
        clean_text = text.replace("--- JARVIS RESPONSE ---", "").strip()
        
        def _speak():
            self.tts_engine.say(clean_text)
            self.tts_engine.runAndWait()
        
        threading.Thread(target=_speak).start()

    def listen(self):
        """Listen for a voice command and return the transcribed text."""
        with self.microphone as source:
            print("\nListening... (Speak now)")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                print("Processing speech...")
                text = self.recognizer.recognize_google(audio)
                print(f"You said: {text}")
                return text
            except sr.WaitTimeoutError:
                print("No speech detected.")
                return None
            except sr.UnknownValueError:
                print("Sorry, I didn't catch that.")
                return None
            except Exception as e:
                print(f"Voice error: {e}")
                return None


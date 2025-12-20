import os
import sys
from ingest import ingest_data
from rag_engine import get_rag_chain
from voice_engine import VoiceEngine

def run_app():
    print("=== AI Vehicle Configuration Assistant (Voice Enabled) ===")
    
    # Initialize Voice
    voice = None
    voice_mode = False
    try:
        voice = VoiceEngine()
        print("Voice Engine Initialized.")
    except Exception as e:
        print(f"Warning: Microphone not detected or voice engine failed: {e}")
        print("Continuing in Text Mode only.")

    # Check for Vector DB
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, "db", "vehicle_config_db")
    if not os.path.exists(DB_PATH):
        print("Knowledge base not found. Initializing indexing...")
        ingest_data()
    
    print("Loading AI Engine (Mistral 7B via Ollama)...")
    try:
        chain = get_rag_chain()
        print("Engine Ready.\n")
    except Exception as e:
        print(f"Failed to load AI Engine: {e}")
        sys.exit(1)

    print("Commands: 'voice' to toggle microphone, 'exit' to quit.")

    while True:
        try:
            if voice_mode and voice:
                user_input = voice.listen()
                if not user_input:
                    continue
            else:
                try:
                    user_input = input("\nUser (Text): ").strip()
                except EOFError:
                    print("\nExiting...")
                    break
                if not user_input:
                    continue

            if user_input.lower() == "voice":
                if voice is None:
                    print("Error: Voice Engine is not available. Please check your microphone.")
                    voice_mode = False
                else:
                    voice_mode = not voice_mode
                    status = "ON" if voice_mode else "OFF"
                    print(f"Voice Mode is now {status}.")
                continue

            if user_input.lower() in ["exit", "quit"]:
                print("Exiting...")
                break
            
            print("Jarvis is thinking...")
            full_response = chain.invoke(user_input)
            
            # Separate reasoning from Jarvis response
            if "--- JARVIS RESPONSE ---" in full_response:
                parts = full_response.split("--- JARVIS RESPONSE ---")
                reasoning_part = parts[0].replace("--- INTERNAL REASONING ---", "").strip()
                jarvis_speech = parts[1].strip()
                
                # Print reasoning in gray
                print("\n\033[90m" + f"[Reasoning]: {reasoning_part}" + "\033[0m")
                print(f"Jarvis: {jarvis_speech}")
                
                # Speak if voice mode is on
                if voice_mode and voice:
                    voice.speak(jarvis_speech)
            else:
                print(f"\nJarvis: {full_response}")
                if voice_mode and voice:
                    voice.speak(full_response)

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            # If the error is repeated rapidly, this would still loop, 
            # but by fixing the 'voice' variable we solve the primary cause.
            # Let's add a small sleep or a way to exit on repeated errors if needed.
            if "voice" in str(e).lower():
                print("Disabling voice mode due to error.")
                voice_mode = False

if __name__ == "__main__":
    run_app()


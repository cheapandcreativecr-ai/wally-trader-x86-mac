"""Voice command listener for Hermes (Windows). Uses speech_recognition (PyAudio).

Wake word: "Hermes" -- followed by command phrase mapped to slash commands.
"""
from __future__ import annotations
import sys
import re
import argparse


PHRASE_MAP = {
    r"status|estado": "/status",
    r"cierre.*todo|close.*all": "/punk-watch",  # use punk-watch for cierre review
    r"vigilar|watch": "/punk-watch",
    r"riesgo|risk": "/risk",
    r"morning|mañana": "/morning",
    r"hunt|caza": "/punk-hunt",
    r"signal|señal": "/signal",
    r"journal|diario": "/journal",
}


def map_phrase_to_command(phrase: str) -> str | None:
    """Map a transcribed phrase to a slash command."""
    phrase = phrase.lower()
    for pattern, cmd in PHRASE_MAP.items():
        if re.search(pattern, phrase):
            return cmd
    return None


def listen_loop(wake_word: str = "hermes"):
    """Listen for wake word + command. Requires speech_recognition + pyaudio."""
    try:
        import speech_recognition as sr
    except ImportError:
        print("speech_recognition not installed. Install via: pip install SpeechRecognition pyaudio", file=sys.stderr)
        return 1

    r = sr.Recognizer()
    mic = sr.Microphone()

    print(f"Listening for wake word '{wake_word}'... (Ctrl+C to stop)")

    while True:
        with mic as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                continue

        try:
            text = r.recognize_google(audio).lower()
            print(f"  Heard: {text}")
            if wake_word in text:
                # Extract command after wake word
                idx = text.find(wake_word)
                phrase_after = text[idx + len(wake_word):].strip()
                cmd = map_phrase_to_command(phrase_after)
                if cmd:
                    print(f"  -> Command: {cmd}")
                    # Forward to hermes (assume hermes CLI in PATH)
                    import subprocess
                    subprocess.run(["hermes", "agent", "--message", cmd], check=False)
                else:
                    print(f"  (no mapping for: {phrase_after})")
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print(f"  STT error: {e}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--wake-word", default="hermes")
    p.add_argument("--test-phrase", help="Test mapping without listening")
    args = p.parse_args()

    if args.test_phrase:
        cmd = map_phrase_to_command(args.test_phrase)
        if cmd:
            print(f"Phrase '{args.test_phrase}' -> {cmd}")
        else:
            print(f"No mapping for '{args.test_phrase}'")
        return

    listen_loop(args.wake_word)


if __name__ == "__main__":
    main()

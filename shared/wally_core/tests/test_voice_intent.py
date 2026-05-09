import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "adapters/hermes"))


# Conditionally importable (don't require speech_recognition just to run tests)
def test_phrase_mapping_status():
    import voice_listener
    assert voice_listener.map_phrase_to_command("show me the status") == "/status"


def test_phrase_mapping_morning():
    import voice_listener
    assert voice_listener.map_phrase_to_command("ejecuta el morning") == "/morning"


def test_phrase_mapping_unknown():
    import voice_listener
    assert voice_listener.map_phrase_to_command("hola que tal") is None


def test_phrase_mapping_spanish():
    import voice_listener
    assert voice_listener.map_phrase_to_command("ver mi riesgo") == "/risk"
    assert voice_listener.map_phrase_to_command("hacer una caza") == "/punk-hunt"

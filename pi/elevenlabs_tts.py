"""
ElevenLabs Text-to-Speech module for announcing detected objects.

Usage:
    from elevenlabs_tts import announce_detections

    # Detection format: [(object_name, camera_id, distance_metres), ...]
    detections = [("person", "cam1", 2.5), None, ("car", "cam3", 5.0)]
    announce_detections(detections)

Requirements:
    pip install elevenlabs python-dotenv

Setup:
    Add your API key to pi/.env file:
    ELEVENLABS_API_KEY=your_key_here
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the same directory as this script
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)
from typing import List, Tuple, Optional
from elevenlabs.client import ElevenLabs
import subprocess
import tempfile

# Map camera_id from server to human-readable names
# Supports both string ("cam1") and numeric (1, 1.0) camera IDs
CAMERA_ID_TO_NAME = {
    # String keys
    "cam1": "front-left",
    "cam2": "front-right",
    "cam3": "back-centre",
    # Numeric keys (server may return these)
    1: "front-left",
    2: "front-right",
    3: "back-centre",
    1.0: "front-left",
    2.0: "front-right",
    3.0: "back-centre",
}

def elevenlabs_play(audio):
    """Play audio using system audio player."""
    # Write audio to temp file and play with aplay
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        for chunk in audio:
            f.write(chunk)
        temp_path = f.name

    try:
        # Use mpv or ffplay to play mp3, fallback to aplay
        try:
            subprocess.run(["mpv", "--no-video", temp_path], check=True, capture_output=True)
        except FileNotFoundError:
            try:
                subprocess.run(["ffplay", "-nodisp", "-autoexit", temp_path], check=True, capture_output=True)
            except FileNotFoundError:
                # Convert to wav and use aplay
                subprocess.run(["ffmpeg", "-i", temp_path, "-f", "wav", "-"], stdout=subprocess.PIPE, check=True)
    finally:
        import os
        os.unlink(temp_path)


# Default voice ID (George - clear male voice)
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"

# Default model
DEFAULT_MODEL_ID = "eleven_multilingual_v2"


def get_client(api_key: Optional[str] = None) -> ElevenLabs:
    """
    Get an ElevenLabs client.

    Args:
        api_key: API key. If None, uses ELEVENLABS_API_KEY env var.

    Returns:
        ElevenLabs client instance
    """
    key = api_key or os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise ValueError(
            "API key required. Set ELEVENLABS_API_KEY env var or pass api_key parameter."
        )
    return ElevenLabs(api_key=key)


def build_announcement_text(
    detections: List[Optional[Tuple[str, str, float]]]
) -> Optional[str]:
    """
    Build announcement text from detections.

    Args:
        detections: List of 3 elements (one per camera).
                   Each element is either None (no detection) or
                   a tuple of (object_name, camera_id, distance_metres).

    Returns:
        Announcement string, or None if no detections
    """
    if len(detections) != 3:
        raise ValueError("Expected exactly 3 detection entries (one per camera)")

    announcements = []

    for i, detection in enumerate(detections):
        if detection is not None:
            obj_name, camera_id, distance = detection
            camera_name = CAMERA_ID_TO_NAME.get(camera_id, camera_id)
            print(f"[DEBUG] Detection {i}: obj={obj_name}, camera_id={camera_id} -> camera_name={camera_name}, distance={distance:.1f}m")
            announcements.append(
                f"I see {obj_name} on {camera_name} {distance:.1f} metres away"
            )
        else:
            print(f"[DEBUG] Detection {i}: None")

    if not announcements:
        return None

    return ". ".join(announcements) + "."


def announce_detections(
    detections: List[Optional[Tuple[str, str, float]]],
    api_key: Optional[str] = None,
    voice_id: str = DEFAULT_VOICE_ID,
    model_id: str = DEFAULT_MODEL_ID
) -> bool:
    """
    Announce detected objects via text-to-speech.

    Args:
        detections: List of 3 elements (one per camera).
                   Each element is either None (no detection) or
                   a tuple of (object_name, camera_id, distance_metres).
        api_key: ElevenLabs API key (uses env var if not provided)
        voice_id: Voice to use
        model_id: Model to use

    Returns:
        True if audio was played, False if no detections to announce
    """
    print(f"[DEBUG] announce_detections called with: {detections}")
    print(f"[DEBUG] CAMERA_ID_TO_NAME mapping: {CAMERA_ID_TO_NAME}")

    text = build_announcement_text(detections)

    if text is None:
        print("No detections to announce")
        return False

    print(f"[DEBUG] Final announcement text: {text}")

    client = get_client(api_key)

    audio = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format="mp3_44100_128",
    )

    elevenlabs_play(audio)
    return True


def speak_text(
    text: str,
    api_key: Optional[str] = None,
    voice_id: str = DEFAULT_VOICE_ID,
    model_id: str = DEFAULT_MODEL_ID
) -> None:
    """
    Speak arbitrary text.

    Args:
        text: Text to speak
        api_key: ElevenLabs API key (uses env var if not provided)
        voice_id: Voice to use
        model_id: Model to use
    """
    client = get_client(api_key)

    audio = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format="mp3_44100_128",
    )

    elevenlabs_play(audio)


# Example usage
if __name__ == "__main__":
    # Example detections: person on front-left at 2.5m, car on back-centre at 5m
    example_detections = [
        ("person", "cam1", 2.5),   # cam1 = front-left
        None,                       # cam2 = front-right (no detection)
        ("car", "cam3", 5.0),       # cam3 = back-centre
    ]

    print("Testing announcement...")
    print(f"Text: {build_announcement_text(example_detections)}")

    # Uncomment to actually play audio (requires API key)
    # announce_detections(example_detections)

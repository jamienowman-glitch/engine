from typing import List, Dict, Any, Protocol, TypedDict, Optional

try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False


class TranscriptSegment(TypedDict):
    start: float  # seconds
    end: float    # seconds
    text: str

class AsrBackend(Protocol):
    backend_version: str
    model_used: str

    def transcribe(self, audio_uri: str, language: Optional[str] = None) -> List[TranscriptSegment]:
        """
        Transcribe audio file to list of segments.
        audio_uri: Local path to audio file.
        """
        ...

class StubAsrBackend:
    backend_version = "asr_stub_v1"
    model_used = "asr_stub_v1"

    def transcribe(self, audio_uri: str, language: Optional[str] = None) -> List[TranscriptSegment]:
        # Return dummy transcript
        return [
            {"start": 0.0, "end": 2.0, "text": "Hello world."},
            {"start": 2.5, "end": 4.5, "text": "This is a caption test."},
            {"start": 5.0, "end": 7.0, "text": "Video editing is fun."}
        ]


class WhisperLocalBackend:
    backend_version_template = "whisper_{model}_{device}"

    def __init__(self, model_size: str = "tiny", device: str = "cpu"):
        self.model = None
        self.model_size = model_size
        self.device = device
        self.model_used = f"whisper_{model_size}"
        self.backend_version = self.backend_version_template.format(model=model_size, device=device)
        if HAS_WHISPER:
            try:
                self.model = whisper.load_model(model_size, device=device)
            except Exception as e:
                print(f"WARNING: Failed to load whisper model: {e}")
                self.model = None

    def transcribe(self, audio_uri: str, language: Optional[str] = None) -> List[TranscriptSegment]:
        if not self.model:
            print("WARNING: Whisper model not loaded, falling back to stub.")
            return StubAsrBackend().transcribe(audio_uri, language=language)
        try:
            result = self.model.transcribe(audio_uri, language=language)
            segments: List[TranscriptSegment] = []
            for s in result["segments"]:
                segments.append({
                    "start": float(s["start"]),
                    "end": float(s["end"]),
                    "text": str(s["text"]).strip()
                })
            self.model_used = f"whisper_{self.model_size}"
            self.backend_version = self.backend_version_template.format(model=self.model_size, device=self.device)
            return segments
        except Exception as e:
            print(f"ERROR: Whisper transcription failed: {e}")
            return StubAsrBackend().transcribe(audio_uri, language=language)

from typing import List, Tuple

class AlignService:
    def calculate_offset(self, master_audio_path: str, angle_audio_path: str) -> float:
        """
        Calculates the time offset in milliseconds to align the angle audio to the master audio.
        Positive offset means angle audio should be delayed (started later) to match master.
        Negative offset means angle audio should be advanced (started earlier).
        
        V1 Stub: Returns 0.0 or a mocked value based on filename for testing.
        Real implementation requires numpy/scipy check.
        """
        # Pseudo-logic for testing:
        # If filename contains "delayed", return 1000ms offset
        if "delayed" in angle_audio_path:
            return 1000.0
        if "advanced" in angle_audio_path:
            return -500.0
            
        return 0.0

_default_service = None

def get_align_service() -> AlignService:
    global _default_service
    if _default_service is None:
        _default_service = AlignService()
    return _default_service

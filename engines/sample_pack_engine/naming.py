from typing import Dict, Any

class SamplePackNamer:
    def __init__(self, pack_name: str):
        self.pack_name = pack_name
        self.counters: Dict[str, int] = {}

    def get_path(self, role: str, tags: list[str], bpm: float = None) -> str:
        role = role.lower()
        folder = "Misc"
        filename_prefix = role
        
        if role in ["kick", "snare", "hat", "clap", "tom", "cymbal", "shaker"]:
            folder = f"Drums/{role.capitalize()}s"
        elif role in ["bass", "808"]:
            folder = "Bass"
        elif role in ["loop"]:
            folder = "Loops"
            if "drums" in tags: folder = "Loops/Drums"
            elif "music" in tags or "keys" in tags: folder = "Loops/Music"
            
        key = f"{folder}/{filename_prefix}"
        count = self.counters.get(key, 0) + 1
        self.counters[key] = count
        
        bpm_str = f"_{int(bpm)}bpm" if bpm else ""
        
        filename = f"{filename_prefix}_{count:02d}{bpm_str}.wav"
        return f"{folder}/{filename}"

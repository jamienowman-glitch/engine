from __future__ import annotations
from typing import Optional
from engines.audio_mix_buses.models import MixGraph
from engines.audio_mix_buses.presets import MIX_GRAPHS

class AudioMixBusesService:
    def get_mix_graph(self, preset_id: str = "default_mix") -> Optional[MixGraph]:
        return MIX_GRAPHS.get(preset_id)

_default_service: Optional[AudioMixBusesService] = None

def get_audio_mix_buses_service() -> AudioMixBusesService:
    global _default_service
    if _default_service is None:
        _default_service = AudioMixBusesService()
    return _default_service

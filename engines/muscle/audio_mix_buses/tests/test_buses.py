from engines.audio_mix_buses.service import AudioMixBusesService
from engines.audio_mix_buses.presets import MIX_GRAPHS

def test_get_mix_graph():
    svc = AudioMixBusesService()
    g = svc.get_mix_graph("default_mix")
    assert g is not None
    assert g.id == "default_mix"
    assert len(g.buses) == 6
   
    # Check Drums
    drums = next(b for b in g.buses if b.id == "bus_drums")
    assert "kick" in drums.roles
    dialogue = next(b for b in g.buses if b.id == "bus_dialogue")
    assert "vox" in dialogue.roles

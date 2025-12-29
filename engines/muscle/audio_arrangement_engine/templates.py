from typing import Dict
from engines.audio_arrangement_engine.models import ArrangementTemplate, ArrangementSection

STRUCTURE_TEMPLATES: Dict[str, ArrangementTemplate] = {
    "pop_standard": ArrangementTemplate(
        id="pop_standard",
        sections=[
            ArrangementSection(name="Intro", bars=4, active_roles=["drums", "keys"]),
            ArrangementSection(name="Verse 1", bars=8, active_roles=["drums", "bass", "keys"]),
            ArrangementSection(name="Chorus 1", bars=8, active_roles=["drums", "bass", "keys", "vocals"]),
            ArrangementSection(name="Verse 2", bars=8, active_roles=["drums", "bass", "keys"]),
            ArrangementSection(name="Chorus 2", bars=8, active_roles=["drums", "bass", "keys", "vocals"]),
            ArrangementSection(name="Outro", bars=4, active_roles=["keys"])
        ]
    ),
    "trap_banger": ArrangementTemplate(
        id="trap_banger",
        sections=[
            ArrangementSection(name="Intro", bars=8, active_roles=["keys", "pads"]),
            ArrangementSection(name="Build", bars=4, active_roles=["keys", "snare", "fxcymbal"]), # Risers?
            ArrangementSection(name="Drop", bars=8, active_roles=["808", "kick", "snare", "hat", "keys"]),
            ArrangementSection(name="Break", bars=4, active_roles=["keys"]),
            ArrangementSection(name="Drop 2", bars=8, active_roles=["808", "kick", "snare", "hat", "keys"]),
            ArrangementSection(name="Outro", bars=8, active_roles=["keys"])
        ]
    )
}

from engines.video_presets.service import get_preset_service

def test_anon_presets_exist():
    svc = get_preset_service()
    presets = svc.list_filter_presets("built_in", "global")
    
    strong = next((p for p in presets if p.name == "anonymise_faces_strong"), None)
    medium = next((p for p in presets if p.name == "anonymise_faces_medium"), None)
    
    assert strong is not None
    assert strong.filters[0].type == "face_blur"
    assert strong.filters[0].params["strength"] == 1.0
    
    assert medium is not None
    assert medium.filters[0].type == "face_blur"
    assert medium.filters[0].params["strength"] == 0.6

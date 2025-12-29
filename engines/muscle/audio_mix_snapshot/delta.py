from engines.audio_mix_snapshot.models import MixSnapshot, MixDelta

def compute_delta(snap_a: MixSnapshot, snap_b: MixSnapshot) -> MixDelta:
    added = []
    removed = []
    changed = {}
    
    tracks_a = set(snap_a.tracks.keys())
    tracks_b = set(snap_b.tracks.keys())
    
    added = list(tracks_b - tracks_a)
    removed = list(tracks_a - tracks_b)
    
    # Check intersection for changes
    common = tracks_a.intersection(tracks_b)
    
    for name in common:
        t_a = snap_a.tracks[name]
        t_b = snap_b.tracks[name]
        
        diffs = {}
        # round floats to avoid epsilon diffs
        if abs(t_a.gain_db - t_b.gain_db) > 0.01:
            diffs["gain_db"] = (t_a.gain_db, t_b.gain_db)
            
        if abs(t_a.pan - t_b.pan) > 0.01:
            diffs["pan"] = (t_a.pan, t_b.pan)
            
        if t_a.active != t_b.active:
            diffs["active"] = (t_a.active, t_b.active)
            
        if t_a.effects != t_b.effects:
            diffs["effects"] = (t_a.effects, t_b.effects)
            
        if diffs:
            changed[name] = diffs
            
    return MixDelta(
        snapshot_a_id=snap_a.id,
        snapshot_b_id=snap_b.id,
        added_tracks=sorted(added),
        removed_tracks=sorted(removed),
        changed_tracks=changed,
        complexity_delta=snap_b.complexity_score - snap_a.complexity_score
    )

from typing import List, Dict, Tuple, Any, Optional
from engines.audio_timeline.models import AudioSequence, AudioClip
from engines.media_v2.service import MediaService
from engines.audio_mix_buses.models import MixGraph, BusConfig

EXPORT_PRESETS: Dict[str, Dict[str, Any]] = {
    "default": {"limiter_thresh": -0.1, "headroom_db": -1.0, "loudnorm_target": None, "dither": False},
    "podcast": {"limiter_thresh": -1.0, "headroom_db": -2.0, "loudnorm_target": -16.0, "dither": True},
    "music": {"limiter_thresh": -0.1, "headroom_db": -0.5, "loudnorm_target": -14.0, "dither": False},
    "voiceover": {"limiter_thresh": -1.0, "headroom_db": -3.0, "loudnorm_target": -18.0, "dither": False}
}


def _normalize_preset(preset: str) -> Dict[str, Any]:
    if preset not in EXPORT_PRESETS:
        raise ValueError(f"Unknown export preset: {preset}")
    return EXPORT_PRESETS[preset]


def get_export_preset_config(preset: str) -> Dict[str, Any]:
    return _normalize_preset(preset)


def _format_value(val: float) -> str:
    return f"{val:.3f}"


def _piecewise_expr(points: List[Tuple[float, float]], duration: float, base_value: float, value_formatter=None) -> Optional[str]:
    if duration <= 0:
        return None
    segments = []
    prev_time = 0.0
    prev_value = base_value

    for time, value in points:
        time = max(0.0, min(duration, time))
        if time < prev_time:
            continue
        segments.append((prev_time, time, prev_value, value))
        prev_time = time
        prev_value = value

    if prev_time < duration:
        segments.append((prev_time, duration, prev_value, prev_value))

    if not segments:
        formatted = value_formatter(base_value) if value_formatter else f"{_format_value(base_value)}"
        return formatted

    expr = _format_value(base_value)
    for start, end, start_val, end_val in reversed(segments):
        if end == start:
            seg_value = start_val
            seg = value_formatter(seg_value) if value_formatter else _format_value(seg_value)
        else:
            seg_value = start_val
            seg = value_formatter(seg_value) if value_formatter else _format_value(seg_value)
        condition = f"between(t,{_format_value(start)},{_format_value(end)})"
        expr = f"if({condition},{seg},{expr})"
    return expr


def _build_volume_expression(clip: AudioClip, base_gain: float) -> Optional[str]:
    duration = clip.duration_ms / 1000.0
    if duration <= 0:
        return None
    points = []
    for param_pts in clip.automation.get("gain", []):
        points.append(((param_pts.time_ms - clip.start_ms) / 1000.0, param_pts.value))
    expr = _piecewise_expr(points, duration, base_gain)
    if not expr:
        return None
    return f"pow(10,({expr})/20)"


def _build_bus_metadata_entry(
    bus_id: str,
    roles: List[str],
    gain_db: float,
    preset: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    return {
        "bus_id": bus_id,
        "roles": roles,
        "gain_db": gain_db,
        "export_preset": preset,
        "limiter_thresh": config["limiter_thresh"],
        "headroom_db": config["headroom_db"],
        "loudnorm_target": config["loudnorm_target"],
        "dithered": config["dither"],
    }


def build_ffmpeg_mix_plan(
    sequence: AudioSequence,
    media_service: MediaService,
    mix_graph: Optional[MixGraph] = None,
    export_preset: str = "default"
) -> Tuple[List[str], str, Dict[str, str], Dict[str, Dict[str, Any]]]:
    """
    Returns (list_of_input_files, filter_complex_string, output_maps)
    output_maps: dict like {"master": "[out]"} or {"drums": "[bus_drums_out]", ...}
    """
    
    config = get_export_preset_config(export_preset)

    # 1. Gather all clips and resolve URIs (deterministic ordering)
    unique_uris = set()
    clip_entries = [] # (clip, track, resolved_uri)
    
    ordered_tracks = sorted(sequence.tracks, key=lambda t: (t.order, t.name, t.role))
    for track in ordered_tracks:
        if track.mute:
            continue
        role_source = track.role or track.meta.get("role")
        if role_source and role_source.lower() == "music" and track.name:
            role_source = track.name
        role_label = (role_source or track.name or "track").lower()
        for clip in sorted(track.clips, key=lambda c: c.start_ms):
            # Resolve URI
            uri = None
            if clip.artifact_id:
                art = media_service.get_artifact(clip.artifact_id)
                if art:
                    uri = art.uri
            elif clip.asset_id:
                asset = media_service.get_asset(clip.asset_id)
                if asset:
                    uri = asset.source_uri
            
            if uri:
                unique_uris.add(uri)
                clip_entries.append((clip, track, uri, role_label))

    sorted_uris = sorted(list(unique_uris))
    uri_to_idx = {u: i for i, u in enumerate(sorted_uris)}
    
    inputs = sorted_uris
    
    if not clip_entries:
        return (
            [],
            "anullsrc=r=44100:cl=stereo:d=5[out]",
            {"master": "[out]"},
            {
                "master": _build_bus_metadata_entry(
                    "master",
                    ["master"],
                    0.0,
                    export_preset,
                    config
                )
            }
        )
        
    filters = []
    # Clip filtering
    # Map clip result to a node.
    # Group by bus if graph exists.

    bus_assignments = {}
    bus_metadata: Dict[str, Dict[str, Any]] = {}
    # Default bus if mix graph missing
    default_bus_id = "master_bus"
    if mix_graph:
        for bus in mix_graph.buses:
            bus_assignments[bus.id] = []
            bus_metadata[bus.id] = _build_bus_metadata_entry(
                bus.id,
                bus.roles,
                bus.gain_db,
                export_preset,
                config
            )
    else:
        bus_assignments[default_bus_id] = []
        bus_metadata[default_bus_id] = _build_bus_metadata_entry(
            default_bus_id,
            ["master"],
            0.0,
            export_preset,
            config
        )

    for i, (clip, track, uri, role) in enumerate(clip_entries):
        inp_idx = uri_to_idx[uri]
        chain_id = f"c{i}"
        
        # Trim / Fade / Gain / Delay
        # ... (Same logic as P3)
        start_sec = clip.source_offset_ms / 1000.0
        dur_sec = clip.duration_ms / 1000.0
        
        fade_in_dur = max(clip.fade_in_ms, clip.crossfade_in_ms) / 1000.0
        fade_out_dur = max(clip.fade_out_ms, clip.crossfade_out_ms) / 1000.0
        fade_curve = clip.fade_curve
        if (clip.crossfade_in_ms > 0 or clip.crossfade_out_ms > 0) and clip.crossfade_curve:
            fade_curve = clip.crossfade_curve

        f_trim = f"[{inp_idx}:a]atrim=start={start_sec}:duration={dur_sec},asetpts=PTS-STARTPTS"
        f_fade = ""
        if fade_in_dur > 0:
            f_fade += f",afade=t=in:st=0:d={fade_in_dur}:curve={fade_curve}"
        if fade_out_dur > 0:
            st_out = max(0.0, dur_sec - fade_out_dur)
            f_fade += f",afade=t=out:st={st_out}:d={fade_out_dur}:curve={fade_curve}"

        start_ms_int = int(clip.start_ms)
        f_delay = f",adelay={start_ms_int}|{start_ms_int}"

        base_label = f"[{chain_id}_base]"
        filters.append(f"{f_trim}{f_fade}{f_delay}{base_label}")

        total_db = clip.gain_db + track.gain_db
        vol_expr = _build_volume_expression(clip, total_db)
        current_label = base_label
        if vol_expr:
            vol_label = f"[{chain_id}_vol]"
            filters.append(f"{current_label}volume={vol_expr}{vol_label}")
            current_label = vol_label

        # Pan automation currently recorded but not enacted (future work)
        
        # Assign to bus
        assigned = False
        if mix_graph:
            for bus in mix_graph.buses:
                bus_roles = [r.lower() for r in bus.roles]
                if any(role == r or role in r or r in role for r in bus_roles):
                    bus_assignments[bus.id].append(current_label)
                    assigned = True
                    break

        if not assigned:
            if mix_graph:
                first_id = mix_graph.buses[0].id
                bus_assignments[first_id].append(current_label)
            else:
                bus_assignments[default_bus_id].append(current_label)

    # Mix Buses
    bus_out_nodes = []
    output_maps = {}

    for bid in list(bus_assignments.keys()):
        nodes = bus_assignments[bid]
        if not nodes:
            # Generate silence for this bus if empty?
            # Or skip.
            # If stem needed, we need silence.
            # anullsrc...
            # For simplicity, skip if no inputs.
            continue

        bus_mix_label = f"mix_{bid}"
        count = len(nodes)
        node_str = "".join(nodes)

        # amix inputs
        # normalize=0 -> sum.
        filters.append(f"{node_str}amix=inputs={count}:dropout_transition=0:normalize=0[{bus_mix_label}_raw]")
        
        # Apply Bus Processing (Gain)
        gain_db = 0.0
        if mix_graph:
            # Find config
            cfg = next((b for b in mix_graph.buses if b.id == bid), None)
            if cfg: gain_db = cfg.gain_db
        bus_metadata.setdefault(bid, _build_bus_metadata_entry(
            bid,
            [],
            gain_db,
            export_preset,
            config
        ))
        final_bus_label = f"bus_{bid}_out"
        if gain_db != 0:
            filters.append(f"[{bus_mix_label}_raw]volume={gain_db}dB[{final_bus_label}]")
        else:
            final_bus_label = f"{bus_mix_label}_raw" # No gain change
            
        bus_out_nodes.append(f"[{final_bus_label}]")
        output_maps[bid] = f"[{final_bus_label}]"

    if not bus_out_nodes:
        filters.append("anullsrc=r=44100:cl=stereo:d=5[out]")
        return (
            inputs,
            ";".join(filters),
            {"master": "[out]"},
            {
                "master": _build_bus_metadata_entry(
                    "master",
                    ["master"],
                    0.0,
                    export_preset,
                    config
                )
            }
        )

    # Master Concatenation/Mix
    # Sum all buses
    master_in_str = "".join(bus_out_nodes)
    c = len(bus_out_nodes)
    filters.append(f"{master_in_str}amix=inputs={c}:dropout_transition=0:normalize=0[master_raw]")

    master_gain = mix_graph.master_gain_db if mix_graph else 0.0
    headroom_label = "[master_headroom]"
    if config["headroom_db"] != 0 or master_gain != 0:
        combined_gain = master_gain + config["headroom_db"]
        filters.append(f"[master_raw]volume={combined_gain}dB{headroom_label}")
    else:
        headroom_label = "[master_raw]"

    prev_label = headroom_label
    if config["loudnorm_target"] is not None:
        loudnorm_label = "[master_loudnorm]"
        filters.append(f"{prev_label}loudnorm=I={config['loudnorm_target']}:LRA=7:TP=-2{loudnorm_label}")
        prev_label = loudnorm_label

    limiter_thresh = config["limiter_thresh"]
    filters.append(f"{prev_label}alimiter=limit={limiter_thresh}dB:level=false[master_limited]")
    prev_label = "[master_limited]"

    if config["dither"]:
        filters.append(f"{prev_label}aformat=sample_fmts=s16:channel_layouts=stereo:sample_rates=48000[dithered]")
        prev_label = "[dithered]"

    final_label = prev_label
    output_maps["master"] = final_label
    bus_metadata["master"] = _build_bus_metadata_entry(
        "master",
        ["master"],
        master_gain,
        export_preset,
        config
    )
    
    return inputs, ";".join(filters), output_maps, bus_metadata

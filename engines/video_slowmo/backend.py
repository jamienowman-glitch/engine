from typing import Literal

def get_optical_flow_filter(
    target_fps: float,
    mode: Literal["mci", "blend"] = "mci",
    mc_mode: str = "aobmc",
    me_mode: str = "bidir",
) -> str:
    """
    Returns the ffmpeg minterpolate filter string for optical flow, with optional modes.
    """
    return f"minterpolate=fps={target_fps}:mi_mode={mode}:mc_mode={mc_mode}:me_mode={me_mode}"

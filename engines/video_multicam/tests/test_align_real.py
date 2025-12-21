import pytest
import numpy as np
import tempfile
import os
import wave
from unittest.mock import MagicMock, patch
from engines.video_multicam.service import MultiCamService
from engines.video_multicam.models import MultiCamAlignRequest, CreateMultiCamSessionRequest, MultiCamTrackSpec
from engines.media_v2.models import MediaAsset

# Helper to create wav file
def create_sine_wav(filename, duration_sec, freq, shift_sec=0.0):
    sr = 8000
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    # Signal: Sine wave starting at shift_sec
    # if t < shift, 0. else sin(2pi*f*(t-shift))
    
    # We want a feature. A "blip" at a specific time.
    # Let's make a blip at 1.0s in master, and 1.5s in angle
    # Lag = 0.5s.
    # Angle is late. Offset should be -500ms?
    # Or positive? Protocol says: "Positive offset -> angle starts LATER than master".
    # Wait, "angle starts later" means we delay the PLAYBACK of angle?
    # If Angle has feature at 1.5s and Master at 1.0s.
    # We want to align them.
    # We need to shift Angle LEFT by 0.5s. 
    # Shift Left = Negative offset in timeline usually?
    # Or start_time = -0.5s (cut head).
    # If offset=500ms, it means start at 500ms.
    # If we start Angle at 500ms, feature moves to 2.0s. (Late + Delay = Later).
    # Correct alignment: Angle Time - 0.5s = Master Time.
    # We need to play Angle 0.5s SOONER.
    # So Offset must be -500ms.
    
    # Let's generate silence then a beep.
    beep_start = 1.0 + shift_sec
    
    y = np.zeros_like(t)
    # 0.1s beep
    start_idx = int(beep_start * sr)
    end_idx = start_idx + int(0.1 * sr)
    if start_idx < len(y):
        end_idx = min(end_idx, len(y))
        y[start_idx:end_idx] = 0.5 * np.sin(2 * np.pi * freq * t[start_idx:end_idx])
    
    # Int16 conversion
    y_int = (y * 32767).astype(np.int16)
    
    with wave.open(filename, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(y_int.tobytes())

@patch("engines.video_multicam.service.get_media_service")
@patch("engines.video_multicam.service.GcsClient")
@patch("engines.video_multicam.backend.HAS_DSP", True)
@patch("engines.video_multicam.backend.librosa", create=True)
@patch("engines.video_multicam.backend.signal", create=True)
@patch("engines.video_multicam.backend.np", create=True)
def test_align_real_dsp(mock_np, mock_signal, mock_librosa, mock_gcs, mock_get_media):
    # Tests real Librosa logic using synthetic files
    
    # 1. Setup Files
    # Master: Beep at 1.0s
    # Angle: Beep at 1.5s (Late by 0.5s)
    # Expected Offset: -500ms (Shift Left)
    
    tmp_dir = tempfile.gettempdir()
    master_path = os.path.join(tmp_dir, "master_align.wav")
    angle_path = os.path.join(tmp_dir, "angle_align.wav")
    
    create_sine_wav(master_path, 3.0, 440, shift_sec=0.0)
    create_sine_wav(angle_path, 3.0, 440, shift_sec=0.5)
    
    # Configure Mocks to behave like known signal
    # Librosa load returns (data, sr)
    # We want correlate to find a lag.
    # If we return simple arrays where angle is shifted 500ms...
    # SR=8000. 500ms = 4000 samples.
    # Master: [0...1...0] (Peak at 8000)
    # Angle:  [0...0...1] (Peak at 12000)
    
    fake_master = np.zeros(24000)
    fake_master[8000] = 1.0
    
    fake_angle = np.zeros(24000)
    fake_angle[12000] = 1.0
    
    mock_librosa.load.side_effect = [
        (fake_master, 8000), # Master
        (fake_angle, 8000)   # Angle
    ]
    
    # Mock Correlation Logic (Simulate scipy logic)
    # We don't want to impl correlation in mock side effect.
    # But backend uses:
    # correlation = signal.correlate(y_master, y_angle...)
    # lags = signal.correlation_lags(...)
    # lag_idx = np.argmax(correlation)
    # lag_samples = lags[lag_idx]
    
    # We want Lag to be +4000 samples (Angle is late by 4000 samples).
    # Master[0] ~= Angle[4000].
    # So lag = 4000.
    
    mock_signal.correlation_lags.return_value = np.array([4000])
    mock_np.argmax.return_value = 0 # Point to our single lag
    
    try:

        # Mock Media
        mock_media = mock_get_media.return_value
        mock_media.get_asset.side_effect = lambda eid: MediaAsset(
            id=eid, tenant_id="t1", env="dev", kind="video", 
            source_uri=master_path if eid=="m" else angle_path
        )
        
        svc = MultiCamService(media_service=mock_media)
        
        # Create Session
        req_create = CreateMultiCamSessionRequest(
            tenant_id="t1", env="dev", name="Align Test",
            tracks=[
                MultiCamTrackSpec(asset_id="m", role="primary"),
                MultiCamTrackSpec(asset_id="a", role="alt")
            ]
        )
        session = svc.create_session(req_create)
        
        # Align
        res = svc.align_session(MultiCamAlignRequest(session_id=session.id, tenant_id="t1", env="dev"))
        
        # Verify
        # Angle is 500ms late.
        # Should be roughly -500ms
        off = res.offsets_ms["a"]
        print(f"Calculated Offset: {off}")
        
        # Allow small tolerance
        assert -550 <= off <= -450 
        
    finally:
        if os.path.exists(master_path): os.unlink(master_path)
        if os.path.exists(angle_path): os.unlink(angle_path)

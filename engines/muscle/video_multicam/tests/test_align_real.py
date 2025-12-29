
import pytest
import numpy as np
import tempfile
import os
try:
    from scipy.io import wavfile
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

from engines.video_multicam.backend import LibrosaAlignBackend

@pytest.fixture
def temp_audio_files():
    if not HAS_SCIPY:
        pytest.skip("Scipy not installed")
        
    sr = 8000
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    
    # Master: 440Hz Sine
    y_master = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    
    # Angle: Delayed by 0.5s (4000 samples)
    delay_samples = 4000 # 0.5s
    y_angle = np.concatenate([np.zeros(delay_samples), y_master[:-delay_samples]]).astype(np.float32)
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fm:
        wavfile.write(fm.name, sr, y_master)
        master_path = fm.name
        
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fa:
        wavfile.write(fa.name, sr, y_angle)
        angle_path = fa.name
        
    yield master_path, angle_path, 500.0
    
    if os.path.exists(master_path):
        os.unlink(master_path)
    if os.path.exists(angle_path):
        os.unlink(angle_path)

def test_librosa_backend_synthetic(temp_audio_files):
    # Check if librosa installed
    try:
        import librosa
    except ImportError:
        pytest.skip("Librosa not installed")

    backend = LibrosaAlignBackend(sr=8000)
    m_path, a_path, expected_delay_ms = temp_audio_files
    
    offset, conf = backend.calculate_offset(m_path, a_path)
    
    print(f"Calculated: {offset}, Conf: {conf}")
    
    # Angle is delayed -> expect negative offset around -500ms
    assert np.isclose(offset, -expected_delay_ms, atol=20.0)
    assert conf > 0.8

def test_librosa_backend_identical(temp_audio_files):
    try:
        import librosa
    except ImportError:
        pytest.skip("Librosa not installed")
        
    backend = LibrosaAlignBackend(sr=8000)
    m_path, _, _ = temp_audio_files
    
    offset, conf = backend.calculate_offset(m_path, m_path)
    assert np.isclose(offset, 0.0, atol=1.0)
    assert conf > 0.95

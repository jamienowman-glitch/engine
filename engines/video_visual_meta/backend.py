from __future__ import annotations

from pathlib import Path
from typing import List, Optional

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

from engines.video_visual_meta.models import VisualMetaSummary, VisualMetaFrame, SubjectDetection


class MissingDependencyError(Exception):
    """Raised when OpenCV is unavailable."""


class OpenCvVisualMetaBackend:
    backend_version = "visual_meta_opencv_v1"
    model_used = "visual_meta_opencv_v1"

    def analyze(
        self,
        video_path: Path,
        sample_interval_ms: int,
        include_labels: Optional[list[str]],
        detect_shot_boundaries: bool,
    ) -> VisualMetaSummary:
        if not HAS_OPENCV:
            raise MissingDependencyError("OpenCV not installed")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError("unable to open source for visual meta")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 360
        frame_interval = max(1, int(max(1, (sample_interval_ms / 1000.0) * fps)))

        frames: List[VisualMetaFrame] = []
        prev_gray = None
        prev_hist = None
        frame_idx = 0
        last_timestamp_ms = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % frame_interval != 0:
                frame_idx += 1
                continue

            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC) or frame_idx * (1000.0 / fps))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            shot_boundary = False
            if detect_shot_boundaries:
                hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
                cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
                if prev_hist is not None:
                    score = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                    shot_boundary = score < 0.7
                prev_hist = hist

            center_x, center_y = 0.5, 0.5
            thresh = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY)[1]
            moments = cv2.moments(thresh)
            if moments["m00"] > 0:
                center_x = min(max(moments["m10"] / moments["m00"] / width, 0.05), 0.95)
                center_y = min(max(moments["m01"] / moments["m00"] / height, 0.05), 0.95)

            motion_magnitude = 0.0
            if prev_gray is not None:
                diff = cv2.absdiff(gray, prev_gray)
                motion_magnitude = float(np.mean(diff)) / 255.0
            prev_gray = gray

            subjects = []
            if not include_labels or "motion" in include_labels:
                subjects.append(
                    SubjectDetection(
                        label="motion",
                        confidence=motion_magnitude,
                        bbox_x=0.0,
                        bbox_y=0.0,
                        bbox_width=1.0,
                        bbox_height=1.0,
                    )
                )

            frames.append(
                VisualMetaFrame(
                    timestamp_ms=timestamp_ms,
                    subjects=subjects,
                    primary_subject_center_x=center_x,
                    primary_subject_center_y=center_y,
                    shot_boundary=shot_boundary,
                )
            )
            frame_idx += 1
            last_timestamp_ms = timestamp_ms

        cap.release()

        if not frames:
            frames.append(
                VisualMetaFrame(
                    timestamp_ms=0,
                    subjects=[],
                    primary_subject_center_x=0.5,
                    primary_subject_center_y=0.5,
                    shot_boundary=detect_shot_boundaries,
                )
            )
            last_timestamp_ms = 0

        duration_ms = max(last_timestamp_ms, frame_idx * sample_interval_ms)
        return VisualMetaSummary(
            asset_id="",
            frames=frames,
            duration_ms=duration_ms,
            frame_sample_interval_ms=sample_interval_ms,
        )

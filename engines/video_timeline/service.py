from __future__ import annotations

from typing import Dict, List, Optional, Any

from engines.config import runtime_config
from engines.video_timeline.models import Clip, FilterStack, Sequence, Track, Transition, VideoProject, ParameterAutomation, Keyframe

try:
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None


class TimelineRepository:
    def create_project(self, project: VideoProject) -> VideoProject:
        raise NotImplementedError

    def get_project(self, project_id: str) -> Optional[VideoProject]:
        raise NotImplementedError

    def list_projects(self, tenant_id: str) -> List[VideoProject]:
        raise NotImplementedError

    def update_project(self, project: VideoProject) -> VideoProject:
        raise NotImplementedError

    def create_sequence(self, sequence: Sequence) -> Sequence:
        raise NotImplementedError

    def get_sequence(self, seq_id: str) -> Optional[Sequence]:
        raise NotImplementedError

    def list_sequences_for_project(self, project_id: str) -> List[Sequence]:
        raise NotImplementedError

    def update_sequence(self, sequence: Sequence) -> Sequence:
        raise NotImplementedError

    def create_track(self, track: Track) -> Track:
        raise NotImplementedError

    def get_track(self, track_id: str) -> Optional[Track]:
        raise NotImplementedError

    def list_tracks_for_sequence(self, sequence_id: str) -> List[Track]:
        raise NotImplementedError

    def update_track(self, track: Track) -> Track:
        raise NotImplementedError

    def create_clip(self, clip: Clip) -> Clip:
        raise NotImplementedError

    def get_clip(self, clip_id: str) -> Optional[Clip]:
        raise NotImplementedError

    def list_clips_for_track(self, track_id: str) -> List[Clip]:
        raise NotImplementedError

    def update_clip(self, clip: Clip) -> Clip:
        raise NotImplementedError

    def delete_clip(self, clip_id: str) -> None:
        raise NotImplementedError

    def create_transition(self, transition: Transition) -> Transition:
        raise NotImplementedError

    def list_transitions_for_sequence(self, sequence_id: str) -> List[Transition]:
        raise NotImplementedError

    def get_transition(self, transition_id: str) -> Optional[Transition]:
        raise NotImplementedError

    def update_transition(self, transition: Transition) -> Transition:
        raise NotImplementedError

    def delete_transition(self, transition_id: str) -> None:
        raise NotImplementedError

    def create_filter_stack(self, stack: FilterStack) -> FilterStack:
        raise NotImplementedError

    def get_filter_stack(self, stack_id: str) -> Optional[FilterStack]:
        raise NotImplementedError

    def get_filter_stack_for_target(self, target_type: str, target_id: str) -> Optional[FilterStack]:
        raise NotImplementedError

    def update_filter_stack(self, stack: FilterStack) -> FilterStack:
        raise NotImplementedError

    def delete_filter_stack(self, stack_id: str) -> None:
        raise NotImplementedError

    # Automation
    def create_automation(self, automation: ParameterAutomation) -> ParameterAutomation:
        raise NotImplementedError

    def get_automation(self, automation_id: str) -> Optional[ParameterAutomation]:
        raise NotImplementedError

    def list_automation(self, target_type: str, target_id: str) -> List[ParameterAutomation]:
        raise NotImplementedError

    def update_automation(self, automation: ParameterAutomation) -> ParameterAutomation:
        raise NotImplementedError

    def delete_automation(self, automation_id: str) -> None:
        raise NotImplementedError


class InMemoryTimelineRepository(TimelineRepository):
    def __init__(self) -> None:
        self.projects: Dict[str, VideoProject] = {}
        self.sequences: Dict[str, Sequence] = {}
        self.tracks: Dict[str, Track] = {}
        self.clips: Dict[str, Clip] = {}
        self.transitions: Dict[str, Transition] = {}
        self.filter_stacks: Dict[str, FilterStack] = {}
        self.automation: Dict[str, ParameterAutomation] = {}

    def create_project(self, project: VideoProject) -> VideoProject:
        self.projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Optional[VideoProject]:
        return self.projects.get(project_id)

    def list_projects(self, tenant_id: str) -> List[VideoProject]:
        return sorted([p for p in self.projects.values() if p.tenant_id == tenant_id], key=lambda p: p.created_at, reverse=True)

    def update_project(self, project: VideoProject) -> VideoProject:
        self.projects[project.id] = project
        return project

    def create_sequence(self, sequence: Sequence) -> Sequence:
        self.sequences[sequence.id] = sequence
        proj = self.projects.get(sequence.project_id)
        if proj and sequence.id not in proj.sequence_ids:
            proj.sequence_ids.append(sequence.id)
            proj.updated_at = sequence.updated_at
        return sequence

    def get_sequence(self, seq_id: str) -> Optional[Sequence]:
        return self.sequences.get(seq_id)

    def list_sequences_for_project(self, project_id: str) -> List[Sequence]:
        return sorted([s for s in self.sequences.values() if s.project_id == project_id], key=lambda s: s.created_at)

    def update_sequence(self, sequence: Sequence) -> Sequence:
        self.sequences[sequence.id] = sequence
        return sequence

    def create_track(self, track: Track) -> Track:
        self.tracks[track.id] = track
        seq = self.sequences.get(track.sequence_id)
        if seq and track.id not in seq.track_ids:
            seq.track_ids.append(track.id)
            seq.updated_at = track.updated_at
        return track

    def get_track(self, track_id: str) -> Optional[Track]:
        return self.tracks.get(track_id)

    def list_tracks_for_sequence(self, sequence_id: str) -> List[Track]:
        return sorted([t for t in self.tracks.values() if t.sequence_id == sequence_id], key=lambda t: t.order)

    def update_track(self, track: Track) -> Track:
        self.tracks[track.id] = track
        return track

    def create_clip(self, clip: Clip) -> Clip:
        self.clips[clip.id] = clip
        return clip

    def get_clip(self, clip_id: str) -> Optional[Clip]:
        return self.clips.get(clip_id)

    def list_clips_for_track(self, track_id: str) -> List[Clip]:
        return sorted([c for c in self.clips.values() if c.track_id == track_id], key=lambda c: c.start_ms_on_timeline)

    def update_clip(self, clip: Clip) -> Clip:
        self.clips[clip.id] = clip
        return clip

    def delete_clip(self, clip_id: str) -> None:
        self.clips.pop(clip_id, None)

    def create_transition(self, transition: Transition) -> Transition:
        self.transitions[transition.id] = transition
        return transition

    def list_transitions_for_sequence(self, sequence_id: str) -> List[Transition]:
        return sorted([t for t in self.transitions.values() if t.sequence_id == sequence_id], key=lambda t: t.created_at)

    def get_transition(self, transition_id: str) -> Optional[Transition]:
        return self.transitions.get(transition_id)

    def update_transition(self, transition: Transition) -> Transition:
        self.transitions[transition.id] = transition
        return transition

    def delete_transition(self, transition_id: str) -> None:
        self.transitions.pop(transition_id, None)

    def create_filter_stack(self, stack: FilterStack) -> FilterStack:
        self.filter_stacks[stack.id] = stack
        return stack

    def get_filter_stack(self, stack_id: str) -> Optional[FilterStack]:
        return self.filter_stacks.get(stack_id)

    def get_filter_stack_for_target(self, target_type: str, target_id: str) -> Optional[FilterStack]:
        return next((s for s in self.filter_stacks.values() if s.target_type == target_type and s.target_id == target_id), None)

    def update_filter_stack(self, stack: FilterStack) -> FilterStack:
        self.filter_stacks[stack.id] = stack
        return stack

    def delete_filter_stack(self, stack_id: str) -> None:
        self.filter_stacks.pop(stack_id, None)

    def create_automation(self, automation: ParameterAutomation) -> ParameterAutomation:
        self.automation[automation.id] = automation
        return automation

    def get_automation(self, automation_id: str) -> Optional[ParameterAutomation]:
        return self.automation.get(automation_id)

    def list_automation(self, target_type: str, target_id: str) -> List[ParameterAutomation]:
        return [a for a in self.automation.values() if a.target_type == target_type and a.target_id == target_id]

    def update_automation(self, automation: ParameterAutomation) -> ParameterAutomation:
        self.automation[automation.id] = automation
        return automation

    def delete_automation(self, automation_id: str) -> None:
        self.automation.pop(automation_id, None)


class FirestoreTimelineRepository(TimelineRepository):
    def __init__(self, client: Optional[object] = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore not installed")
        project = runtime_config.get_firestore_project()
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]

    def _col(self, tenant_id: str, name: str):
        return self._client.collection(f"{name}_{tenant_id}")

    def create_project(self, project: VideoProject) -> VideoProject:
        self._col(project.tenant_id, "video_projects").document(project.id).set(project.model_dump())
        return project

    def get_project(self, project_id: str) -> Optional[VideoProject]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return None
        snap = self._col(tenant, "video_projects").document(project_id).get()
        return VideoProject(**snap.to_dict()) if snap and snap.exists else None

    def list_projects(self, tenant_id: str) -> List[VideoProject]:
        docs = self._col(tenant_id, "video_projects").where("tenant_id", "==", tenant_id).stream()
        return sorted([VideoProject(**d.to_dict()) for d in docs], key=lambda p: p.created_at, reverse=True)

    def update_project(self, project: VideoProject) -> VideoProject:
        self._col(project.tenant_id, "video_projects").document(project.id).set(project.model_dump())
        return project

    def create_sequence(self, sequence: Sequence) -> Sequence:
        self._col(sequence.tenant_id, "video_sequences").document(sequence.id).set(sequence.model_dump())
        return sequence

    def get_sequence(self, seq_id: str) -> Optional[Sequence]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return None
        snap = self._col(tenant, "video_sequences").document(seq_id).get()
        return Sequence(**snap.to_dict()) if snap and snap.exists else None

    def list_sequences_for_project(self, project_id: str) -> List[Sequence]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return []
        docs = self._col(tenant, "video_sequences").where("project_id", "==", project_id).stream()
        return sorted([Sequence(**d.to_dict()) for d in docs], key=lambda s: s.created_at)

    def update_sequence(self, sequence: Sequence) -> Sequence:
        self._col(sequence.tenant_id, "video_sequences").document(sequence.id).set(sequence.model_dump())
        return sequence

    def create_track(self, track: Track) -> Track:
        self._col(track.tenant_id, "video_tracks").document(track.id).set(track.model_dump())
        return track

    def get_track(self, track_id: str) -> Optional[Track]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return None
        snap = self._col(tenant, "video_tracks").document(track_id).get()
        return Track(**snap.to_dict()) if snap and snap.exists else None

    def list_tracks_for_sequence(self, sequence_id: str) -> List[Track]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return []
        docs = self._col(tenant, "video_tracks").where("sequence_id", "==", sequence_id).stream()
        return sorted([Track(**d.to_dict()) for d in docs], key=lambda t: t.order)

    def update_track(self, track: Track) -> Track:
        self._col(track.tenant_id, "video_tracks").document(track.id).set(track.model_dump())
        return track

    def create_clip(self, clip: Clip) -> Clip:
        self._col(clip.tenant_id, "video_clips").document(clip.id).set(clip.model_dump())
        return clip

    def get_clip(self, clip_id: str) -> Optional[Clip]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return None
        snap = self._col(tenant, "video_clips").document(clip_id).get()
        return Clip(**snap.to_dict()) if snap and snap.exists else None

    def list_clips_for_track(self, track_id: str) -> List[Clip]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return []
        docs = self._col(tenant, "video_clips").where("track_id", "==", track_id).stream()
        return sorted([Clip(**d.to_dict()) for d in docs], key=lambda c: c.start_ms_on_timeline)

    def update_clip(self, clip: Clip) -> Clip:
        self._col(clip.tenant_id, "video_clips").document(clip.id).set(clip.model_dump())
        return clip

    def delete_clip(self, clip_id: str) -> None:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return
        self._col(tenant, "video_clips").document(clip_id).delete()

    def create_transition(self, transition: Transition) -> Transition:
        self._col(transition.tenant_id, "video_transitions").document(transition.id).set(transition.model_dump())
        return transition

    def list_transitions_for_sequence(self, sequence_id: str) -> List[Transition]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return []
        docs = self._col(tenant, "video_transitions").where("sequence_id", "==", sequence_id).stream()
        return sorted([Transition(**d.to_dict()) for d in docs], key=lambda t: t.created_at)

    def get_transition(self, transition_id: str) -> Optional[Transition]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return None
        snap = self._col(tenant, "video_transitions").document(transition_id).get()
        return Transition(**snap.to_dict()) if snap and snap.exists else None

    def update_transition(self, transition: Transition) -> Transition:
        self._col(transition.tenant_id, "video_transitions").document(transition.id).set(transition.model_dump())
        return transition

    def delete_transition(self, transition_id: str) -> None:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return
        self._col(tenant, "video_transitions").document(transition_id).delete()

    def create_filter_stack(self, stack: FilterStack) -> FilterStack:
        self._col(stack.tenant_id, "video_filter_stacks").document(stack.id).set(stack.model_dump())
        return stack

    def get_filter_stack(self, stack_id: str) -> Optional[FilterStack]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return None
        snap = self._col(tenant, "video_filter_stacks").document(stack_id).get()
        return FilterStack(**snap.to_dict()) if snap and snap.exists else None

    def get_filter_stack_for_target(self, target_type: str, target_id: str) -> Optional[FilterStack]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return None
        docs = self._col(tenant, "video_filter_stacks").where("target_type", "==", target_type).where("target_id", "==", target_id).stream()
        for d in docs:
            return FilterStack(**d.to_dict())
        return None

    def update_filter_stack(self, stack: FilterStack) -> FilterStack:
        self._col(stack.tenant_id, "video_filter_stacks").document(stack.id).set(stack.model_dump())
        return stack

    def delete_filter_stack(self, stack_id: str) -> None:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return
        self._col(tenant, "video_filter_stacks").document(stack_id).delete()

    # Automation
    def create_automation(self, automation: ParameterAutomation) -> ParameterAutomation:
        self._col(automation.tenant_id, "video_automation").document(automation.id).set(automation.model_dump())
        return automation

    def get_automation(self, automation_id: str) -> Optional[ParameterAutomation]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return None
        snap = self._col(tenant, "video_automation").document(automation_id).get()
        return ParameterAutomation(**snap.to_dict()) if snap and snap.exists else None

    def list_automation(self, target_type: str, target_id: str) -> List[ParameterAutomation]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return []
        docs = (
            self._col(tenant, "video_automation")
            .where("target_type", "==", target_type)
            .where("target_id", "==", target_id)
            .stream()
        )
        return [ParameterAutomation(**d.to_dict()) for d in docs]

    def update_automation(self, automation: ParameterAutomation) -> ParameterAutomation:
        self._col(automation.tenant_id, "video_automation").document(automation.id).set(automation.model_dump())
        return automation

    def delete_automation(self, automation_id: str) -> None:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return
        self._col(tenant, "video_automation").document(automation_id).delete()


class TimelineService:
    def __init__(self, repo: Optional[TimelineRepository] = None) -> None:
        # GAP-G1: No fallback to InMemory. Repo must be durable or None (will error on use).
        # Phase 0 closeout enforces fail-fast via routing registry startup validation.
        self.repo = repo or self._default_repo()

    def _default_repo(self) -> TimelineRepository:
        # Must use Firestore; no fallback to InMemory
        return FirestoreTimelineRepository()

    # Project
    def create_project(self, project: VideoProject) -> VideoProject:
        return self.repo.create_project(project)

    def get_project(self, project_id: str) -> Optional[VideoProject]:
        return self.repo.get_project(project_id)

    def list_projects(self, tenant_id: str) -> List[VideoProject]:
        return self.repo.list_projects(tenant_id)

    def update_project(self, project: VideoProject) -> VideoProject:
        return self.repo.update_project(project)

    # Sequence
    def create_sequence(self, sequence: Sequence) -> Sequence:
        return self.repo.create_sequence(sequence)

    def get_sequence(self, seq_id: str) -> Optional[Sequence]:
        return self.repo.get_sequence(seq_id)

    def list_sequences_for_project(self, project_id: str) -> List[Sequence]:
        return self.repo.list_sequences_for_project(project_id)

    def update_sequence(self, sequence: Sequence) -> Sequence:
        return self.repo.update_sequence(sequence)

    # Track
    def create_track(self, track: Track) -> Track:
        return self.repo.create_track(track)

    def get_track(self, track_id: str) -> Optional[Track]:
        return self.repo.get_track(track_id)

    def list_tracks_for_sequence(self, sequence_id: str) -> List[Track]:
        return self.repo.list_tracks_for_sequence(sequence_id)

    def update_track(self, track: Track) -> Track:
        return self.repo.update_track(track)

    # Clip
    def create_clip(self, clip: Clip) -> Clip:
        return self.repo.create_clip(clip)

    def get_clip(self, clip_id: str) -> Optional[Clip]:
        return self.repo.get_clip(clip_id)

    def list_clips_for_track(self, track_id: str) -> List[Clip]:
        return self.repo.list_clips_for_track(track_id)

    def update_clip(self, clip: Clip) -> Clip:
        return self.repo.update_clip(clip)

    def delete_clip(self, clip_id: str) -> None:
        self.repo.delete_clip(clip_id)

    # Edit Ops
    def trim_clip(self, clip_id: str, new_in_ms: float, new_out_ms: float, ripple: bool = False) -> Clip:
        clip = self.get_clip(clip_id)
        if not clip:
            raise ValueError(f"Clip {clip_id} not found")
            
        if new_out_ms <= new_in_ms:
            raise ValueError("new_out_ms must be > new_in_ms")
            
        old_duration = clip.out_ms - clip.in_ms
        new_duration = new_out_ms - new_in_ms
        delta = new_duration - old_duration
        
        clip.in_ms = new_in_ms
        clip.out_ms = new_out_ms
        # Only start_ms stays the same for a tail trim. 
        # For head trim, start_ms stays same? Or shifts? 
        # Standard: trim usually just affects content window. 
        # If ripple=True, we shift subsequent clips by delta.
        
        self.update_clip(clip)
        
        if ripple and delta != 0:
            self._shift_track_after(clip.track_id, clip.start_ms_on_timeline + old_duration, delta)
            
        return clip

    def split_clip(self, clip_id: str, split_time_on_timeline_ms: float) -> Clip:
        clip = self.get_clip(clip_id)
        if not clip:
            raise ValueError(f"Clip {clip_id} not found")
            
        if not (clip.start_ms_on_timeline < split_time_on_timeline_ms < clip.start_ms_on_timeline + (clip.out_ms - clip.in_ms)):
             raise ValueError("Split point outside clip bounds")
             
        # Calculate offset into asset
        offset_ms = split_time_on_timeline_ms - clip.start_ms_on_timeline
        split_point_in_asset = clip.in_ms + offset_ms
        
        # Original clip ends at split
        old_out = clip.out_ms
        clip.out_ms = split_point_in_asset
        self.update_clip(clip)
        
        # New clip starts at split
        new_clip = Clip(
            tenant_id=clip.tenant_id,
            env=clip.env,
            user_id=clip.user_id,
            track_id=clip.track_id,
            asset_id=clip.asset_id,
            artifact_id=clip.artifact_id,
            mask_artifact_id=clip.mask_artifact_id,
            in_ms=split_point_in_asset,
            out_ms=old_out,
            start_ms_on_timeline=split_time_on_timeline_ms,
            speed=clip.speed,
            volume_db=clip.volume_db,
            opacity=clip.opacity,
            blend_mode=clip.blend_mode,
            scale_mode=clip.scale_mode,
            position=clip.position,
            crop=clip.crop,
            stabilise=clip.stabilise,
            optical_flow=clip.optical_flow,
            alignment_applied=clip.alignment_applied,
            meta=clip.meta.copy() if clip.meta else {}
        )
        return self.create_clip(new_clip)

    def move_clip(self, clip_id: str, new_start_ms: float, track_id: Optional[str] = None, ripple: bool = False) -> Clip:
        clip = self.get_clip(clip_id)
        if not clip:
            raise ValueError(f"Clip {clip_id} not found")
            
        target_track = track_id if track_id else clip.track_id
        duration = clip.out_ms - clip.in_ms
        
        if ripple:
             # Very basic ripple insert: Shift everything at insertion point to the right by duration
             self._shift_track_after(target_track, new_start_ms, duration)
             
        clip.start_ms_on_timeline = new_start_ms
        clip.track_id = target_track
        
        return self.update_clip(clip)

    def _shift_track_after(self, track_id: str, time_threshold_ms: float, delta_ms: float):
        clips = self.list_clips_for_track(track_id)
        for c in clips:
            if c.start_ms_on_timeline >= time_threshold_ms:
                c.start_ms_on_timeline += delta_ms
                self.update_clip(c)

    # Transition
    def create_transition(self, transition: Transition) -> Transition:
        if transition.duration_ms <= 0:
            raise ValueError("Transition duration must be greater than 0")
        # Ensure clips exist? (Optional but good for T01.3)
        return self.repo.create_transition(transition)

    def list_transitions_for_sequence(self, sequence_id: str) -> List[Transition]:
        return self.repo.list_transitions_for_sequence(sequence_id)

    def get_transition(self, transition_id: str) -> Optional[Transition]:
        return self.repo.get_transition(transition_id)

    def update_transition(self, transition: Transition) -> Transition:
        return self.repo.update_transition(transition)

    def delete_transition(self, transition_id: str) -> None:
        self.repo.delete_transition(transition_id)

    # Filter stacks
    KNOWN_FILTERS = {
        "color_grade", "teeth_whiten", "skin_smooth", "face_blur", "eye_enhance", "lut"
    }

    def create_filter_stack(self, stack: FilterStack) -> FilterStack:
        for f in stack.filters:
            if f.type not in self.KNOWN_FILTERS:
                raise ValueError(f"Unknown filter type: {f.type}")
        return self.repo.create_filter_stack(stack)

    def get_filter_stack_for_target(self, target_type: str, target_id: str) -> Optional[FilterStack]:
        return self.repo.get_filter_stack_for_target(target_type, target_id)

    # Multicam Integration (T01.4)
    def promote_multicam_to_sequence(self, project_id: str, name: str, multicam_result: Dict[str, Any]) -> Sequence:
        """
        multicam_result expected structure (from V04):
        {
            "cuts": [
                {"asset_id": "a1", "start_ms": 0, "end_ms": 1000, "meta": {...}},
                ...
            ],
            "meta": {"alignment_version": "v1", ...},
            "tenant_id": "...", 
            "env": "..."
        }
        """
        tenant_id = multicam_result.get("tenant_id")
        env = multicam_result.get("env")
        if not tenant_id or not env:
            raise ValueError("Multicam result missing tenant_id/env")
            
        seq = self.create_sequence(Sequence(
            tenant_id=tenant_id, env=env, project_id=project_id, name=name
        ))
        
        # Create Main Video Track
        track = self.create_track(Track(
            tenant_id=tenant_id, env=env, sequence_id=seq.id, kind="video", video_role="main"
        ))
        
        timeline_cursor = 0.0
        for cut in multicam_result.get("cuts", []):
            duration = cut["end_ms"] - cut["start_ms"]
            meta = cut.get("meta", {})
            self.create_clip(Clip(
                tenant_id=tenant_id,
                env=env,
                track_id=track.id,
                asset_id=cut["asset_id"],
                in_ms=cut["start_ms"],
                out_ms=cut["end_ms"],
                start_ms_on_timeline=timeline_cursor,
                alignment_applied=True, # Assuming multicam output implies alignment
                meta=meta
            ))
            timeline_cursor += duration
            
        return seq

    # Assist Integration (T01.5)
    def ingest_assist_highlights(self, sequence_id: str, highlights_result: Dict[str, Any]) -> Track:
        """
        highlights_result:
        {
            "segments": [
                {"asset_id": "a1", "in_ms": 100, "out_ms": 500, "meta": {"score": 0.9}},
                ...
            ],
            "tenant_id": "...", "env": "..."
        }
        """
        tenant_id = highlights_result.get("tenant_id")
        env = highlights_result.get("env")
        if not tenant_id or not env:
            raise ValueError("Assist result missing tenant_id/env")
            
        track = self.create_track(Track(
            tenant_id=tenant_id, env=env, sequence_id=sequence_id, kind="video", video_role="b-roll", meta={"source": "assist"}
        ))
        
        # Simple concatenation on new track? Or smart placement? 
        # T01.5 DoD says "Highlight suggestions become tracks/clips". 
        # We'll just stack them for now.
        
        cursor = 0.0
        for seg in highlights_result.get("segments", []):
            duration = seg["out_ms"] - seg["in_ms"]
            self.create_clip(Clip(
                tenant_id=tenant_id,
                env=env,
                track_id=track.id,
                asset_id=seg["asset_id"],
                in_ms=seg["in_ms"],
                out_ms=seg["out_ms"],
                start_ms_on_timeline=cursor,
                meta=seg.get("meta", {})
            ))
            cursor += duration  # Assuming they are meant to be a reel
            
        return track

    # Focus Integration (T01.5)
    def apply_focus_automation(self, clip_id: str, focus_result: Dict[str, Any]) -> List[ParameterAutomation]:
        """
        focus_result:
        {
            "keyframes": [
                {"time_ms": 0, "crop_x": 0.5, "crop_y": 0.3, "scale": 1.2},
                ...
            ],
            "tenant_id": "...", "env": "..."
        }
        """
        clip = self.get_clip(clip_id)
        if not clip:
            raise ValueError(f"Clip {clip_id} not found")
            
        created_auto = []
        # Group keyframes by property
        props: Dict[str, List[Keyframe]] = {
            "crop_x": [], "crop_y": [], "scale": []
        }
        
        for kf in focus_result.get("keyframes", []):
            t = int(kf.get("time_ms", 0))
            if "crop_x" in kf:
                props["crop_x"].append(Keyframe(time_ms=t, value=kf["crop_x"]))
            if "crop_y" in kf:
                props["crop_y"].append(Keyframe(time_ms=t, value=kf["crop_y"]))
            if "scale" in kf:
                props["scale"].append(Keyframe(time_ms=t, value=kf["scale"]))
                
        for prop_name, kfs in props.items():
            if not kfs:
                continue
            auto = ParameterAutomation(
                tenant_id=clip.tenant_id,
                env=clip.env,
                target_type="clip",
                target_id=clip.id,
                property=prop_name, # type: ignore
                keyframes=sorted(kfs, key=lambda k: k.time_ms)
            )
            created_auto.append(self.create_automation(auto))
            
        return created_auto

    def get_filter_stack(self, stack_id: str) -> Optional[FilterStack]:
        return self.repo.get_filter_stack(stack_id)

    def update_filter_stack(self, stack: FilterStack) -> FilterStack:
        return self.repo.update_filter_stack(stack)

    def delete_filter_stack(self, stack_id: str) -> None:
        self.repo.delete_filter_stack(stack_id)

    # Automation
    def create_automation(self, automation: ParameterAutomation) -> ParameterAutomation:
        return self.repo.create_automation(automation)

    def get_automation(self, automation_id: str) -> Optional[ParameterAutomation]:
        return self.repo.get_automation(automation_id)

    def list_automation(self, target_type: str, target_id: str) -> List[ParameterAutomation]:
        return self.repo.list_automation(target_type, target_id)

    def update_automation(self, automation: ParameterAutomation) -> ParameterAutomation:
        return self.repo.update_automation(automation)

    def delete_automation(self, automation_id: str) -> None:
        self.repo.delete_automation(automation_id)


_default_service: Optional[TimelineService] = None


def get_timeline_service() -> TimelineService:
    global _default_service
    if _default_service is None:
        _default_service = TimelineService()
    return _default_service


def set_timeline_service(service: TimelineService) -> None:
    global _default_service
    _default_service = service

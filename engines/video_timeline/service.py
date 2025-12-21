from __future__ import annotations

from typing import Dict, List, Optional

from engines.config import runtime_config
from engines.video_timeline.models import Clip, FilterStack, Sequence, Track, Transition, VideoProject, ParameterAutomation

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
        self.repo = repo or self._default_repo()

    def _default_repo(self) -> TimelineRepository:
        try:
            return FirestoreTimelineRepository()
        except Exception:
            return InMemoryTimelineRepository()

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

    # Transition
    def create_transition(self, transition: Transition) -> Transition:
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
    def create_filter_stack(self, stack: FilterStack) -> FilterStack:
        return self.repo.create_filter_stack(stack)

    def get_filter_stack_for_target(self, target_type: str, target_id: str) -> Optional[FilterStack]:
        return self.repo.get_filter_stack_for_target(target_type, target_id)

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

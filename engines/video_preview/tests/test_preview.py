from unittest.mock import MagicMock, patch

from engines.video_render.models import PlanStep, RenderPlan, RenderResult
from engines.video_preview.models import PreviewRequest
from engines.video_preview.service import PreviewService
from engines.video_timeline.models import Clip, Sequence


@patch("engines.video_preview.service.get_timeline_service")
@patch("engines.video_preview.service.get_render_service")
def test_preview_generation(mock_render_getter, mock_timeline_getter):
    mock_ts = mock_timeline_getter.return_value
    mock_rs = mock_render_getter.return_value
    track = MagicMock()
    track.id = "t1"
    track.kind = "video"
    mock_ts.list_tracks_for_sequence.return_value = [track]
    mock_ts.list_clips_for_track.return_value = [Clip(id="c1", track_id="t1", tenant_id="t1", env="dev", asset_id="a1", in_ms=0, out_ms=1000, start_ms_on_timeline=0)]

    seq = Sequence(id="s1", project_id="p1", tenant_id="t1", env="dev", name="Seq")
    mock_ts.get_sequence.return_value = seq
    mock_rs.render.return_value = RenderResult(
        asset_id="a_out",
        artifact_id="art_out",
        uri="/tmp/preview.mp4",
        render_profile="preview_720p_fast",
        plan_preview=RenderPlan(
            inputs=[],
            input_meta=[],
            steps=[PlanStep(description="preview", ffmpeg_args=["ffmpeg"])],
            output_path="/tmp/preview.mp4",
            profile="preview_720p_fast",
            filters=[],
            audio_filters=[],
            meta={},
        ),
    )

    svc = PreviewService(render_service=mock_rs, timeline_service=mock_ts)
    req = PreviewRequest(sequence_id="s1", strategy="DRAFT")

    res = svc.get_preview_stream(req)

    assert res is not None
    assert res.render_plan["profile"] == "draft_480p_fast"
    assert res.render_plan["meta"]["preview_profile"] == "preview_720p_fast"
    assert mock_rs.render.call_args[0][0].render_profile == "preview_720p_fast"
    assert res.estimated_latency_ms == 200
    mock_rs.ensure_proxies_for_project.assert_called_with("p1")
    assert mock_rs.render.call_count == 1


@patch("engines.video_preview.service.get_timeline_service")
@patch("engines.video_preview.service.get_render_service")
def test_preview_missing_clips_warns(mock_render_getter, mock_timeline_getter):
    mock_ts = mock_timeline_getter.return_value
    mock_rs = mock_render_getter.return_value
    track = MagicMock()
    track.id = "t1"
    track.kind = "video"
    mock_ts.list_tracks_for_sequence.return_value = [track]
    mock_ts.list_clips_for_track.return_value = []

    seq = Sequence(id="s1", project_id="p1", tenant_id="t1", env="dev", name="Seq")
    mock_ts.get_sequence.return_value = seq
    plan = RenderPlan(
        inputs=[],
        input_meta=[],
        steps=[PlanStep(description="preview", ffmpeg_args=["ffmpeg"])],
        output_path="/tmp/preview.mp4",
        profile="preview_720p_fast",
        filters=[],
        audio_filters=[],
        meta={},
    )
    mock_rs.render.return_value = RenderResult(
        asset_id="a_out",
        artifact_id="art_out",
        uri="/tmp/preview.mp4",
        render_profile="preview_720p_fast",
        plan_preview=plan,
    )

    svc = PreviewService(render_service=mock_rs, timeline_service=mock_ts)
    req = PreviewRequest(sequence_id="s1", strategy="DRAFT")

    res = svc.get_preview_stream(req)

    assert res.render_plan["meta"].get("preview_warnings")
    assert "no_clips_for_preview" in res.render_plan["meta"]["preview_warnings"]
    assert res.render_plan["meta"]["preview_profile"] == "preview_720p_fast"
    assert res.render_plan["profile"] == "draft_480p_fast"

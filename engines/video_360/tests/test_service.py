import pytest
from unittest.mock import MagicMock
from engines.video_360.models import VirtualCameraKeyframe
from engines.video_360.service import Video360Service

def test_compile_expression_constant():
    service = Video360Service(media_service=MagicMock())
    kfs = [VirtualCameraKeyframe(time_ms=0, yaw=45)]
    expr = service._compile_expression(kfs, "yaw")
    assert expr == "45.0"

def test_compile_expression_lerp():
    service = Video360Service(media_service=MagicMock())
    kfs = [
        VirtualCameraKeyframe(time_ms=0, yaw=0),
        VirtualCameraKeyframe(time_ms=1000, yaw=90)
    ]
    expr = service._compile_expression(kfs, "yaw")
    # if(lt(t,1.0),lerp(0.0,90.0,(t-0.0)/1.0),90.0)
    assert "lerp(0.0,90.0" in expr
    assert "if(lt(t,1.0)" in expr

def test_build_v360_filter():
    service = Video360Service(media_service=MagicMock())
    kfs = [
        VirtualCameraKeyframe(time_ms=0, yaw=0, pitch=10),
        VirtualCameraKeyframe(time_ms=1000, yaw=90, pitch=20)
    ]
    filter_str = service.build_v360_filter(kfs)
    assert "v360=input=e:output=flat" in filter_str
    assert "yaw=" in filter_str
    assert "pitch=" in filter_str
    assert "roll='0.0'" in filter_str # Default
    assert "h_fov='90.0'" in filter_str # Default

def test_compile_expression_multi_segment():
    service = Video360Service(media_service=MagicMock())
    kfs = [
        VirtualCameraKeyframe(time_ms=0, yaw=0),
        VirtualCameraKeyframe(time_ms=1000, yaw=90),
        VirtualCameraKeyframe(time_ms=2000, yaw=180)
    ]
    expr = service._compile_expression(kfs, "yaw")
    # Should be nested
    # if(lt(t,1.0), ..., if(lt(t,2.0), ..., 180.0))
    # Logic in service builds from back: 
    # expr = 180.0
    # expr = if(lt(t, 2.0), segment2, 180.0)
    # expr = if(lt(t, 1.0), segment1, expr)
    assert expr.count("if(lt(t,") == 2

def test_build_v360_filter_with_dimensions():
    service = Video360Service(media_service=MagicMock())
    kfs = [VirtualCameraKeyframe(time_ms=0, yaw=0)]
    # social_1_1 is 1080x1080
    filter_str = service.build_v360_filter(kfs, width=1080, height=1080)
    assert ":w=1080:h=1080" in filter_str

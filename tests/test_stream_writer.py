from evm_overlay.stream_writer import build_ffmpeg_rtsp_command


def test_build_ffmpeg_rtsp_command_pipes_bgr_frames_to_rtsp():
    cmd = build_ffmpeg_rtsp_command(
        output_url="rtsp://go2rtc:8554/baby-bed-heart",
        width=1280,
        height=720,
        fps=15,
    )

    assert cmd[:4] == ["ffmpeg", "-hide_banner", "-loglevel", "warning"]
    assert "rawvideo" in cmd
    assert "bgr24" in cmd
    assert "1280x720" in cmd
    assert "libx264" in cmd
    assert cmd[-2:] == ["-f", "rtsp"] or cmd[-3:] == ["-f", "rtsp", "rtsp://go2rtc:8554/baby-bed-heart"]
    assert cmd[-1] == "rtsp://go2rtc:8554/baby-bed-heart"

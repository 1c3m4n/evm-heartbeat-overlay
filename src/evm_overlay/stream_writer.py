from __future__ import annotations

import subprocess
from dataclasses import dataclass

import numpy as np


def build_ffmpeg_rtsp_command(*, output_url: str, width: int, height: int, fps: int) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-re",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-tune",
        "zerolatency",
        "-pix_fmt",
        "yuv420p",
        "-f",
        "rtsp",
        output_url,
    ]


@dataclass
class FfmpegRtspWriter:
    output_url: str
    width: int
    height: int
    fps: int

    def __post_init__(self) -> None:
        self.command = build_ffmpeg_rtsp_command(
            output_url=self.output_url,
            width=self.width,
            height=self.height,
            fps=self.fps,
        )
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    def write(self, frame: np.ndarray) -> None:
        if frame.shape[:2] != (self.height, self.width):
            raise ValueError(f"frame shape {frame.shape} does not match writer size {(self.height, self.width)}")
        if self.process.poll() is not None:
            stderr = b""
            if self.process.stderr is not None:
                stderr = self.process.stderr.read()[-4000:]
            raise RuntimeError(f"ffmpeg exited with code {self.process.returncode}: {stderr.decode(errors='ignore')}")
        if self.process.stdin is None:
            raise RuntimeError("ffmpeg stdin is closed")
        self.process.stdin.write(frame.tobytes())

    def release(self) -> None:
        if self.process.stdin is not None:
            self.process.stdin.close()
        self.process.wait(timeout=10)

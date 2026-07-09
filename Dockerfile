ARG BASE_IMAGE=rocm/dev-ubuntu-22.04
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OPENCV_VIDEOIO_PRIORITY_MSMF=0

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv ffmpeg libgl1 libglib2.0-0 \
    ocl-icd-libopencl1 clinfo \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY src /app/src
RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel \
  && python3 -m pip install --no-cache-dir .

COPY config.example.yaml /config/config.yaml
VOLUME ["/config"]

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD python3 -c "import cv2; print('opencl_available=', cv2.ocl.haveOpenCL(), 'opencl_enabled=', cv2.ocl.useOpenCL())" || exit 1

ENTRYPOINT ["python3", "-m", "evm_overlay.service"]
CMD ["--config", "/config/config.yaml"]

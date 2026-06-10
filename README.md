# Tello VGGT Omega 3D Reconstruction

A complete 3D reconstruction pipeline based on Facebook's VGGT-Omega foundation model.

The project supports three different workflows:

1. Live acquisition and reconstruction from a DJI Tello EDU drone.
2. Reconstruction from an existing video file.
3. Rebuilding a reconstruction from previously saved VGGT chunks.

The pipeline is designed for long sequences and constrained GPU memory environments by processing data in overlapping chunks and saving intermediate results to disk.

---

# Overview

Modern visual geometry foundation models can recover:

* Camera poses
* Camera intrinsics
* Dense depth maps
* Confidence maps
* World-space point clouds

directly from image sequences.

VGGT-Omega performs this reconstruction from monocular image streams without requiring:

* Camera calibration
* SLAM pipelines
* Structure-from-Motion preprocessing

This project provides a complete orchestration layer around VGGT-Omega for acquisition, chunk management, fusion, persistence, and GLB export.

---

# Features

* DJI Tello EDU support
* Video file reconstruction
* Chunk-based processing
* Intermediate chunk persistence
* Recovery after interruption
* Overlap-aware chunk fusion
* Automatic mission management
* GLB export
* Blender-compatible output
* Jetson AGX Orin support
* CUDA workstation support

---

# Architecture

The project is organized around four core components.

## Video Acquisition

Responsible for:

* Tello video streaming
* Frame capture
* Chunk generation
* Overlap management

Example:

Chunk 0

Frame 0 → 99

Chunk 1

Frame 95 → 194

Chunk 2

Frame 190 → 289

The overlap allows chunks to be fused afterward.

---

## VGGT-Omega Inference

Responsible for:

* Loading VGGT-Omega
* Running inference
* Producing reconstruction data

Outputs:

* Camera extrinsics
* Camera intrinsics
* Depth maps
* Confidence maps

---

## Chunk Fusion

Responsible for:

* Detecting overlapping predictions
* Removing duplicates
* Merging trajectories
* Producing a global reconstruction

The fusion process uses overlap information between consecutive chunks.

---

## GLB Export

Responsible for:

* Point cloud generation
* Camera visualization
* Scene export

Outputs:

* GLB files
* Blender-compatible scenes
* MeshLab-compatible scenes

---

# Project Structure

```text
project/
│
├── checkpoints/
│   └── model.pt
│
├── missions/
│
├── src/
│   └── tello_vggt/
│
├── run_tello_reconstruction.py
├── run_video_reconstruction.py
├── rebuild_mission.py
│
└── pyproject.toml
```

---

# Hardware Requirements

## Recommended

* NVIDIA RTX 4060 Ti 16GB
* 32 GB RAM
* Ubuntu 24.04
* Python 3.12

## Minimum

* NVIDIA RTX 3080 10GB
* 16 GB RAM

## Jetson

Supported:

* Jetson AGX Orin 64GB

Inference will be slower but remains fully functional.

---

# Creating the Python Environment

Create a virtual environment:

```bash
python3.12 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Upgrade pip:

```bash
pip install --upgrade pip setuptools wheel
```

---

# Installing PyTorch

Example for CUDA-enabled desktop GPUs:

```bash
pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu126
```

Verify CUDA availability:

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

Expected output:

```text
True
```

---

# Installing the Project

```bash
pip install -e .[vggt,dev]
```

---

# Installing VGGT-Omega

Clone the official repository:

```bash
git clone https://github.com/facebookresearch/vggt-omega.git external/vggt-omega
```

Example structure:

```text
project/
│
├── external/
│   └── vggt-omega/
│
├── src/
│
└── run_tello_reconstruction.py
```

Add the repository to the Python path:

```python
import sys
from pathlib import Path

sys.path.append(
    str(
        Path(__file__).parent
        / "external"
        / "vggt-omega"
    )
)
```

---

# Downloading the Model

Download the VGGT-Omega checkpoint.

Example:

```text
checkpoints/
└── model.pt
```

Update your scripts accordingly:

```python
CHECKPOINT = "checkpoints/model.pt"
```

---

# Usage

## 1. Live Reconstruction from DJI Tello

This workflow:

* Connects to a DJI Tello EDU
* Records all frames
* Runs VGGT inference chunk-by-chunk
* Saves chunks immediately
* Fuses all chunks
* Exports a GLB reconstruction

Launch:

```bash
python run_tello_reconstruction.py
```

Mission structure:

```text
missions/
└── mission_20260610_120000/
    ├── mission.json
    ├── frames/
    ├── chunks/
    └── reconstruction.glb
```

Recommended flight behavior:

* Move slowly
* Avoid motion blur
* Avoid rapid yaw rotations
* Keep objects visible across multiple viewpoints
* Maintain visual overlap

Stop acquisition with:

```text
CTRL+C
```

The final reconstruction is generated automatically.

---

## 2. Reconstruction from a Video File

Use this workflow when a video already exists.

Supported formats include:

* mp4
* mov
* avi
* mkv

Launch:

```bash
python run_video_reconstruction.py
```

Pipeline:

1. Extract frames
2. Run VGGT inference
3. Save chunk files
4. Fuse chunks
5. Export GLB

Generated structure:

```text
mission/
├── frames/
├── chunks/
├── fused_result.npz
└── mission.glb
```

---

## 3. Rebuild an Existing Mission

This workflow allows reconstruction to be regenerated from saved chunk files without rerunning VGGT inference.

Useful when:

* GLB export parameters change
* Fusion logic is improved
* A previous export failed
* Additional filtering is required

Launch:

```bash
python rebuild_mission.py
```

Pipeline:

1. Load chunk files
2. Fuse chunks
3. Reload frames
4. Export a new GLB

No VGGT inference is executed.

---

# Mission Format

A mission follows the structure:

```text
mission/
│
├── mission.json
│
├── frames/
│   ├── frame_0000000.jpg
│   ├── frame_0000001.jpg
│   └── ...
│
├── chunks/
│   ├── chunk_00000.npz
│   ├── chunk_00001.npz
│   └── ...
│
├── fused_result.npz
│
└── reconstruction.glb
```

Chunk files contain:

* Camera extrinsics
* Camera intrinsics
* Depth maps
* Confidence maps

They can be reloaded independently at any time.

---

# Recovery and Fault Tolerance

Each VGGT chunk is written to disk immediately after inference.

Example:

```text
Chunk 0 -> saved
Chunk 1 -> saved
Chunk 2 -> saved

System crash
```

Previously generated chunks remain available.

The mission can be rebuilt without rerunning inference on those chunks.

Benefits:

* Crash resistance
* Reduced VRAM usage
* Reduced RAM usage
* Long flight support
* Easy experimentation

---

# Viewing Results

Generated GLB files can be opened directly in:

* Blender
* MeshLab
* Windows 3D Viewer
* BabylonJS
* ThreeJS

Example:

```bash
blender reconstruction.glb
```

---

# Performance Expectations

Approximate performance on an RTX 4060 Ti 16GB:

| Chunk Size | Resolution | Time    |
| ---------- | ---------- | ------- |
| 50 Frames  | 512        | 5–10 s  |
| 100 Frames | 512        | 10–20 s |
| 200 Frames | 512        | 20–40 s |

Actual timings depend on:

* CUDA version
* PyTorch version
* xFormers availability
* GPU clocks

---

# Jetson AGX Orin Recommendations

Recommended settings:

```python
CHUNK_SIZE = 50
IMAGE_RESOLUTION = 512
MODE = "balanced"
```

These settings reduce memory pressure while preserving reconstruction quality.

---

# Future Improvements

Potential future additions:

* CLI interface
* YAML configuration files
* TensorRT acceleration
* Real-time reconstruction preview
* Open3D integration
* Bundle adjustment
* Point cloud filtering
* Multi-mission fusion
* Autonomous waypoint missions
* Large-scale outdoor mapping

---

# License

This repository contains original orchestration and reconstruction code.

VGGT-Omega remains subject to the license terms of the original Facebook Research project.

Please consult the official VGGT-Omega repository for licensing details.

# Tello VGGT-Omega 3D Reconstruction

A modern, production-ready 3D reconstruction pipeline for DJI Tello and video footage built around Facebook's VGGT-Omega foundation model.

This repository now provides a unified CLI, configurable YAML settings, mission tracking, structured logging, Gaussian Splatting support, and semantic segmentation with Deep Anything V3.

---

## ✨ Key Features

- **Modern CLI**: `tello-vggt` with commands for recording, video reconstruction, rebuilding, Gaussian Splatting, and semantic segmentation.
- **Configurable**: YAML-based configuration with Pydantic validation.
- **Mission management**: Automatic mission directories, status tracking, and metadata persistence.
- **Chunked processing**: Overlap-aware chunk generation for memory-efficient inference.
- **GLB export**: Blender- and MeshLab-compatible output.
- **Gaussian Splatting**: Render point clouds into splatted geometry.
- **Semantic segmentation**: Deep Anything V3 integration for class-aware reconstruction.
- **Structured logging**: Colored terminal output, file logging, and per-mission logs.
- **Test coverage**: Pytest tests for config and mission workflows.

---

## 🚀 Quick Start

### 1. Install the package

```bash
cd /home/jetson/Desktop/tello_vggt
pip install -e .
```

To install optional extras:

```bash
pip install -e ".[all]"
```

### 2. Create configuration

```bash
tello-vggt init-config --output config.yaml
```

Edit `config.yaml` to match your hardware, dataset, and mission preferences.

### 3. Run video reconstruction

```bash
tello-vggt video input.mp4 --config config.yaml
```

### 4. View results

The mission output is stored in a mission directory under `missions/`.

```bash
ls missions/mission_001/output/
```

---

## 🧭 CLI Commands

```bash
tello-vggt --help
```

### Main commands

- `tello-vggt record [OPTIONS]` — Capture frames from a DJI Tello drone.
- `tello-vggt video [VIDEO] [OPTIONS]` — Reconstruct a scene from a video file.
- `tello-vggt rebuild [MISSION] [OPTIONS]` — Rebuild a mission from saved chunks.
- `tello-vggt gaussian-splatting [MISSION] [OPTIONS]` — Run Gaussian Splatting on a mission.
- `tello-vggt semantic-segmentation [MISSION] [OPTIONS]` — Apply Deep Anything V3 segmentation.
- `tello-vggt list-missions` — List available missions.
- `tello-vggt show-config` — Display the loaded configuration.
- `tello-vggt init-config` — Generate a config template.

---

## 🧪 Recommended Workflows

### Video reconstruction

```bash
tello-vggt video input.mp4 --config config.yaml
```

This workflow extracts frames, runs VGGT inference per chunk, fuses results, and exports a GLB file.

### Gaussian Splatting

```bash
tello-vggt gaussian-splatting missions/mission_001
```

Generates Gaussian-based rendering output from the reconstructed mission.

### Depth Anything 3

```bash
tello-vggt depth-anything-3 ~/Videos/input.mp4 \
  --config config.yaml \
  --model-id your-depth-anything-3-model
```

For a local Depth Anything 3 clone, expose a small factory and point the CLI to it:

```bash
PYTHONPATH=external/depth-anything-3:$PYTHONPATH \
tello-vggt depth-anything-3 ~/Videos/input.mp4 \
  --config config.yaml \
  --model-import depth_anything_3_adapter:create_model \
  --checkpoint checkpoints/depth-anything-3.pt
```

The command exports normalized depth PNGs, a compressed depth NPZ, a colored PLY point
cloud, and a Gaussian initialization NPZ.

### Semantic segmentation

```bash
tello-vggt semantic-segmentation missions/mission_001 --checkpoint deep_anything_v3.pt
```

Produces class-aware point clouds and segmentation masks.

### Rebuild from existing chunks

```bash
tello-vggt rebuild missions/mission_001
```

Use this when chunks are already available but the final GLB export needs regeneration.

---

## 🗂️ Mission Output Structure

A mission directory typically contains:

```text
missions/mission_001/
├── frames/                    # Extracted frame images
├── chunks/                    # Per-chunk VGGT inference results
├── output/                    # Exported reconstruction
│   └── reconstruction.glb
├── gaussian_splatting/        # Optional advanced rendering output
├── semantic_segmentation/     # Optional semantic output
├── logs/                      # Mission logs
└── mission.json               # Mission metadata
```

---

## ⚙️ Configuration

The project uses `config.example.yaml` as a template.

Example configuration fields:

```yaml
vggt:
  checkpoint_path: "checkpoints/VGGT-Omega.pt"
  image_resolution: 512
  mode: balanced
  device: cuda
  half_precision: false

inference:
  chunk_size: 100
  overlap: 5
  batch_size: 16

acquisition:
  fps: 30
  fourcc: "mp4v"

export:
  confidence_threshold: 50.0
  show_cameras: true

gaussian_splatting:
  enabled: true
  sh_degree: 3
  iterations: 7000

missions_dir: "missions"
logs_dir: "logs"
log_level: "INFO"
```

Use `tello-vggt init-config --output config.yaml` to generate a starter file, then edit it for your environment.

---

## 🧰 Installation Requirements

- Python 3.10+
- `pip`
- A CUDA-capable GPU is strongly recommended for VGGT inference.
- Linux is the preferred platform; Jetson AGX Orin is supported.

### Python dependencies

Install the base dependencies with:

```bash
pip install -e .
```

Optional extras:

- `.[gaussian-splatting]` — Gaussian Splatting support
- `.[deep-anything-v3]` — Deep Anything V3 semantic segmentation
- `.[all]` — All optional dependencies

---

## 🔧 Development & Testing

Run tests with:

```bash
pytest tests/ -v
```

For coverage:

```bash
pytest tests/ --cov=tello_vggt --cov-report=html
```

---

## 📌 Notes

- Legacy scripts such as `run_tello_reconstruction.py`, `run_video_reconstruction.py`, and `rebuild_mission.py` remain in the repository for compatibility, but the preferred interface is the new `tello-vggt` CLI.
- Use `tello-vggt --help` or `tello-vggt <command> --help` to see available options.
- If you need to change logging behavior, update `log_level` and `log_to_file` in your config.

---

## 📘 Configuration Template

A detailed configuration example is available in `config.example.yaml`.

---

## 🎯 Summary

This repository now offers a polished, modern command-line interface and a structured pipeline for building 3D reconstructions from drone and video data. It is designed for repeatable missions, robust logging, and advanced post-processing with Gaussian Splatting and semantic segmentation.

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

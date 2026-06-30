# 🚁 Tello VGGT-Omega 3D Reconstruction - Modern CLI Edition

A complete, production-ready 3D reconstruction pipeline for DJI Tello using Facebook's VGGT-Omega foundation model, now with **modern Python tooling**, **CLI interface**, **Gaussian Splatting**, and **semantic segmentation**.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()

---

## ✨ What's New

### 🎯 Modern CLI Interface
```bash
# Single, intuitive command line
tello-vggt video input.mp4
tello-vggt record --duration 300
tello-vggt rebuild missions/mission_001
tello-vggt gaussian-splatting missions/mission_001
```

### ⚙️ Configuration Management
```bash
# YAML-based configuration with validation
tello-vggt init-config
tello-vggt show-config --output current.yaml
```

### 📊 Structured Logging
```
2026-06-30 14:23:45 [INFO] Processing video: input.mp4
2026-06-30 14:23:46 [INFO] 🎬 Extracting frames...
2026-06-30 14:24:12 [INFO] ✅ Extracted 300 frames
2026-06-30 14:24:13 [INFO] 🔗 Fusing chunks...
```

### 🎨 Gaussian Splatting
```bash
# Generate 3D Gaussian Splats for real-time rendering
tello-vggt gaussian-splatting missions/my_mission
```

### 🎭 Semantic Segmentation
```bash
# Extract semantic classes with Deep Anything V3
tello-vggt semantic-segmentation missions/my_mission \
  --checkpoint deep_anything_v3.pt
```

### 📋 Mission Management
```bash
# Track and manage all reconstructions
tello-vggt list-missions
```

---

## 🚀 Quick Start

### Installation
```bash
# Clone and install
cd tello_vggt
pip install -e ".[all]"

# Initialize configuration
tello-vggt init-config --output config.yaml
```

### Process Video
```bash
tello-vggt video input.mp4 --config config.yaml
```

### Output
```
missions/
└── mission_001/
    ├── frames/           (Extracted frames)
    ├── chunks/           (VGGT inference)
    ├── output/
    │   └── reconstruction.glb     ← Open in Blender!
    ├── gaussian_splatting/        (Optional)
    └── semantic_segmentation/     (Optional)
```

---

## 🎛️ Commands

### Core Workflows
```bash
tello-vggt record [OPTIONS]           # Record from Tello drone
tello-vggt video [VIDEO] [OPTIONS]    # Reconstruct from video file
tello-vggt rebuild [MISSION] [OPTIONS]# Rebuild from chunks
```

### Advanced Features
```bash
tello-vggt gaussian-splatting [MISSION] [OPTIONS]      # GS rendering
tello-vggt semantic-segmentation [MISSION] [OPTIONS]   # Segmentation
```

### Utilities
```bash
tello-vggt list-missions              # List all missions
tello-vggt show-config                # View current config
tello-vggt init-config [OPTIONS]      # Create config template
```

### Get Help
```bash
tello-vggt --help                     # Global help
tello-vggt video --help               # Command-specific help
```

---

## 📖 Documentation

- 📘 [Quick Start Guide](QUICK_START.md) - Get running in 5 minutes
- 🏗️ [Architecture Guide](ARCHITECTURE_REFACTORED.md) - Detailed structure
- 📋 [Config Reference](config.example.yaml) - Configuration options
- ✅ [Refactoring Summary](REFACTORING_COMPLETE.md) - What's new
- 🔍 [Analysis](ANALYSIS_AND_RECOMMENDATIONS.md) - Design decisions

---

## 📦 Features

### Video Acquisition
- ✅ DJI Tello drone support
- ✅ Video file processing
- ✅ Configurable frame extraction

### 3D Reconstruction
- ✅ VGGT-Omega inference
- ✅ Chunk-based processing (GPU memory efficient)
- ✅ Overlap-aware fusion
- ✅ GLB/GLTF export

### Advanced Rendering
- ✅ **Gaussian Splatting** - Real-time 3D rendering
- ✅ **Semantic Segmentation** - Deep Anything V3 integration
- ✅ **Point Cloud Export** - PLY/NPZ formats
- ✅ **Per-class segmentation** - Semantic object isolation

### Project Management
- ✅ Mission lifecycle tracking
- ✅ Status persistence
- ✅ Per-mission logging
- ✅ Automatic cleanup policies

### Configuration
- ✅ YAML-based settings
- ✅ Environment variable support
- ✅ Type validation (Pydantic)
- ✅ Multiple profiles

### Development
- ✅ Type hints throughout
- ✅ Comprehensive logging
- ✅ Error handling & recovery
- ✅ Pytest test suite

---

## 🛠️ Technical Stack

### Core Dependencies
- **pydantic** ≥2.0 - Configuration validation
- **typer** ≥0.12 - CLI framework
- **pyyaml** ≥6.0 - YAML support
- **tqdm** ≥4.67 - Progress bars
- **torch** ≥2.0 - Deep learning
- **opencv-python** ≥4.11 - Computer vision

### Optional Dependencies
```bash
# Full VGGT support
pip install -e ".[vggt]"

# Gaussian Splatting
pip install -e ".[gaussian-splatting]"

# Deep Anything V3
pip install -e ".[deep-anything-v3]"

# Everything
pip install -e ".[all]"
```

---

## 📋 System Requirements

- **Python:** 3.10+
- **GPU:** CUDA-capable NVIDIA GPU (recommended)
- **RAM:** 16GB+ (32GB recommended)
- **Disk:** 50GB+ (for models and outputs)
- **OS:** Linux recommended (Jetson AGX Orin tested)

---

## 🎯 Use Cases

### 1. Drone Mapping
```bash
tello-vggt record --duration 600  # 10 min flight
tello-vggt rebuild missions/flight_001
```

### 2. Architecture Documentation
```bash
# Record building interior
tello-vggt record --output missions/building
tello-vggt gaussian-splatting missions/building  # For VR walkthrough
```

### 3. Construction Site Monitoring
```bash
tello-vggt video site_progress.mp4
tello-vggt semantic-segmentation missions/site  # Object detection
```

### 4. Research & Development
```bash
tello-vggt video scene.mp4 --skip-export  # Just inference
# Then post-process with custom Python code
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=tello_vggt --cov-report=html

# Specific test
pytest tests/test_config.py -v
```

---

## 📊 Example Workflow

```bash
# 1. Initialize
tello-vggt init-config --output my_config.yaml
# → Creates YAML template with all options

# 2. Configure (edit my_config.yaml)
nano my_config.yaml
# → Set image resolution, chunk size, output path

# 3. Process video
tello-vggt video footage.mp4 --config my_config.yaml
# → Extracts frames → Runs VGGT → Fuses chunks → Exports GLB

# 4. Generate Gaussian Splats
tello-vggt gaussian-splatting missions/mission_001
# → Converts to real-time rendereable format

# 5. Extract semantics
tello-vggt semantic-segmentation missions/mission_001 \
  --checkpoint deep_anything_v3.pt
# → Generates class-specific point clouds

# 6. View results
ls missions/mission_001/output/
# → reconstruction.glb ✅
# → gaussian_splatting/gaussians.ply
# → semantic_segmentation/class_*.ply
```

---

## 🔧 Configuration Example

```yaml
# config.yaml
vggt:
  checkpoint_path: "checkpoints/VGGT-Omega.pt"
  image_resolution: 512
  device: cuda
  mode: balanced

inference:
  chunk_size: 100
  overlap: 5
  batch_size: 16

gaussian_splatting:
  enabled: true
  sh_degree: 3
  iterations: 7000

missions_dir: "missions"
log_level: "INFO"
```

---

## 🐛 Troubleshooting

### CUDA Memory Error
```yaml
# Reduce resolution in config.yaml
vggt:
  image_resolution: 256
```

### Module Not Found
```bash
pip install -e ".[all]"
```

### Mission Stuck in "Recording"
```bash
# Edit mission metadata
nano missions/mission_001/mission.json
# Change "status": "recording" → "status": "recorded"
tello-vggt rebuild missions/mission_001
```

For more help, see [QUICK_START.md](QUICK_START.md)

---

## 📚 Learning Resources

- **VGGT-Omega Paper:** Visual Geometry Groups
- **Gaussian Splatting:** 3D Gaussian Splatting for Real-Time Radiance Field Rendering
- **Deep Anything V3:** Semantic segmentation foundation model
- **PyTorch:** Deep learning framework

---

## 🤝 Contributing

We welcome contributions! Areas of interest:

- [ ] REST API layer
- [ ] Web dashboard
- [ ] Docker containerization
- [ ] Performance optimizations
- [ ] Model quantization
- [ ] Additional export formats
- [ ] Mobile app support

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **Facebook Research** - VGGT-Omega model
- **DJI** - Tello drone hardware
- **PyTorch Team** - Deep learning framework
- **Open Source Community** - All dependencies

---

## 📞 Support

- 📖 Read the [documentation](QUICK_START.md)
- 🔍 Check [troubleshooting guide](QUICK_START.md#troubleshooting)
- 🐛 Review [logs](missions/mission_001/logs/)
- 💬 Enable verbose mode: `--verbose`

---

## 🎉 Status

**✅ Production Ready**

- Tested on Jetson AGX Orin
- Works with CUDA 11.8+
- Python 3.10+ compatible
- Full backward compatibility with original scripts

---

## 🚀 Get Started Now

```bash
# Installation
pip install -e .

# Quick demo
tello-vggt init-config
tello-vggt video example.mp4

# View results
open missions/mission_001/output/reconstruction.glb
```

**Happy reconstructing!** 🎨


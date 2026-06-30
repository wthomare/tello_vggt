# Architecture Refactored - Tello VGGT-Omega 3D Reconstruction

## 📊 Overview

The project has been completely refactored with modern Python practices:

```
tello_vggt/
├── core/                          # Configuration & Management
│   ├── config.py                  # Pydantic-based configuration
│   ├── logging_config.py          # Structured logging with colors
│   └── mission.py                 # Mission lifecycle management
│
├── cli/                           # Command-line interface
│   ├── main.py                    # Typer CLI entry point
│   └── commands/
│       ├── record.py              # Tello drone recording
│       ├── video.py               # Video file reconstruction
│       ├── rebuild.py             # Rebuild from existing chunks
│       ├── gaussian_splatting.py  # GS rendering
│       └── semantic_segmentation.py  # Deep Anything V3
│
├── rendering/                     # Advanced rendering
│   ├── gaussian_splatting.py      # Gaussian Splatting support
│   └── deep_anything_v3.py        # Semantic segmentation
│
├── mission_loader.py              # Legacy - load chunks/frames
├── vggt_chunk_result.py           # Legacy - data structures
├── vggt_chunk_fusioner.py         # Legacy - chunk fusion
├── vggt_omega_tello_inferencer.py # Legacy - VGGT inference
├── video_recorder.py              # Legacy - Tello recorder
│
└── __init__.py                    # Public API exports
```

## 🎯 Key Improvements

### 1. **Configuration Management**
```python
# Load from YAML
config = AppConfig.from_yaml("config.yaml")

# Or create default
config = AppConfig()

# Validate with Pydantic
# All settings type-checked and documented
```

**Features:**
- ✅ Pydantic validation
- ✅ YAML/JSON support
- ✅ Type hints
- ✅ Enum constraints
- ✅ Global configuration instance

### 2. **Unified CLI**
```bash
# Record from Tello
tello-vggt record --duration 300 --output missions/my_mission

# Reconstruct from video
tello-vggt video video.mp4 --output missions/my_mission

# Rebuild from chunks
tello-vggt rebuild missions/my_mission

# List all missions
tello-vggt list-missions

# Generate Gaussian Splatting
tello-vggt gaussian-splatting missions/my_mission

# Semantic segmentation
tello-vggt semantic-segmentation missions/my_mission --checkpoint model.pt
```

**Features:**
- ✅ Single entry point
- ✅ Subcommands with help
- ✅ Consistent options
- ✅ Config support

### 3. **Logging System**
```python
from tello_vggt.core.logging_config import get_logger, setup_logging

logger = get_logger(__name__)

# Colored terminal output + file logging
setup_logging(
    log_level="DEBUG",
    log_dir="logs",
    mission_id="mission_001"
)

logger.info("Processing started")
logger.error("Something went wrong")
```

**Features:**
- ✅ Colored console output
- ✅ File rotation
- ✅ Per-mission logs
- ✅ Debug mode

### 4. **Mission Management**
```python
from tello_vggt.core.mission import Mission, MissionManager, MissionStatus

# Create mission
mission = Mission.create(Path("missions"), "my_mission")

# Track status
mission.set_status(MissionStatus.RECORDING)
mission.set_status(MissionStatus.INFERENCING)
mission.set_status(MissionStatus.COMPLETED)

# List all
manager = MissionManager(Path("missions"))
missions = manager.list_missions()
```

**Features:**
- ✅ Mission lifecycle
- ✅ Status tracking
- ✅ Metadata persistence
- ✅ Directory management

### 5. **Gaussian Splatting Support**
```python
from tello_vggt.rendering.gaussian_splatting import (
    GaussianSplattingTrainer,
    GaussianSplattingRenderer
)

# Train from VGGT result
trainer = GaussianSplattingTrainer(
    sh_degree=3,
    iterations=7000
)
gs_result = trainer.train_from_vggt(vggt_result, ...)

# Render or export
renderer = GaussianSplattingRenderer()
renderer.export_ply(gs_result, "output.ply")
```

**Features:**
- ✅ Point cloud initialization
- ✅ PLY export
- ✅ Spherical Harmonics
- ✅ Optional full training

### 6. **Deep Anything V3 Integration**
```python
from tello_vggt.rendering.deep_anything_v3 import (
    DeepAnythingV3Processor
)

processor = DeepAnythingV3Processor(checkpoint_path="...")
result = processor.process_vggt_result(
    vggt_result,
    images=frames,
    segmentation_prompt="all objects"
)

# Get semantic point clouds per class
class_point_clouds = result["class_point_clouds"]
```

**Features:**
- ✅ Semantic segmentation
- ✅ Per-class point clouds
- ✅ Depth masking
- ✅ PLY export

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# With coverage
pytest tests/ --cov=tello_vggt

# Specific test
pytest tests/test_config.py -v
```

**Test Files:**
- `test_config.py` - Configuration validation
- `test_mission.py` - Mission management
- `conftest.py` - Pytest fixtures

## 📋 Workflows

### Workflow 1: Record from Tello
```bash
tello-vggt record --duration 300 \
  --config config.yaml \
  --output missions/tello_flight
```

### Workflow 2: Video to GLB
```bash
tello-vggt video video.mp4 \
  --config config.yaml \
  --output missions/video_reconstruction
```

### Workflow 3: Full 3D Gaussian Splatting
```bash
# Record/reconstruct
tello-vggt video input.mp4 --output missions/gs_mission

# Generate Gaussian Splatting
tello-vggt gaussian-splatting missions/gs_mission

# Export for viewer
# Output: missions/gs_mission/gaussian_splatting/*.ply
```

### Workflow 4: Semantic Reconstruction
```bash
# Reconstruct with segmentation
tello-vggt video input.mp4 --output missions/semantic

# Generate semantic output
tello-vggt semantic-segmentation missions/semantic \
  --checkpoint deep_anything_v3.pt

# Output: missions/semantic/semantic_segmentation/
#   - mission_id_segmentation.npz
#   - mission_id_class_0.ply
#   - mission_id_class_1.ply
#   - ...
```

## 🔧 Configuration Example

Create `config.yaml`:

```yaml
vggt:
  checkpoint_path: "checkpoints/VGGT-Omega.pt"
  image_resolution: 512
  device: cuda
  
inference:
  chunk_size: 100
  overlap: 5
  batch_size: 16
  
gaussian_splatting:
  enabled: true
  backend: gaussian_splatting
  sh_degree: 3
  iterations: 7000
  deep_anything_v3_checkpoint: null

missions_dir: "missions"
log_level: "INFO"
```

## 📦 Installation

```bash
# Core dependencies
pip install -e .

# With VGGT support
pip install -e ".[vggt]"

# With Gaussian Splatting
pip install -e ".[gaussian-splatting]"

# With everything
pip install -e ".[all]"
```

## 🚀 Usage Examples

### Python API

```python
from tello_vggt.core.config import load_config
from tello_vggt.cli.commands.video import cmd_video

config = load_config("config.yaml")
glb_path = cmd_video(
    config=config,
    video_path="input.mp4",
    skip_export=False
)
print(f"Output: {glb_path}")
```

### Command Line

```bash
# Initialize config
tello-vggt init-config --output my_config.yaml

# Process video
tello-vggt video input.mp4 --config my_config.yaml

# List missions
tello-vggt list-missions --config my_config.yaml

# Rebuild mission
tello-vggt rebuild missions/mission_001

# View current config
tello-vggt show-config
```

## 📊 Pipeline Flow

```
Video/Tello Stream
    ↓
[Extract Frames]
    ↓
[VGGT-Omega Inference]
    ↓
[Chunk Storage] ← Recovery point
    ↓
[Chunk Fusion]
    ↓
[GLB Export] → Output 1: reconstruction.glb
    ↓
[Optional: Gaussian Splatting] → Output 2: gaussians.ply
    ↓
[Optional: Deep Anything V3] → Output 3: semantic_*.ply
```

## 🔐 Error Handling

All commands include:
- ✅ Try/except blocks
- ✅ Descriptive error messages
- ✅ Mission status tracking
- ✅ Recovery mechanisms

```python
try:
    result = cmd_video(config, video_path)
    mission.set_status("completed")
except Exception as e:
    logger.error(f"Failed: {e}")
    mission.set_status("failed")
    raise
```

## 📈 Performance

### Optimizations
- ✅ GPU memory management (`torch.cuda.empty_cache()`)
- ✅ Chunk-based processing (large sequences)
- ✅ Optional FP16 precision
- ✅ Multi-worker data loading

### Monitoring
- ✅ Progress bars (tqdm)
- ✅ Performance metrics
- ✅ GPU memory tracking
- ✅ Processing time logs

## 🎓 Advanced Features

1. **Configuration Validation** - Pydantic ensures all settings are correct
2. **Mission Recovery** - Status tracking allows resuming interrupted missions
3. **Logging** - Full audit trail for debugging
4. **CLI Help** - `tello-vggt --help` for all commands
5. **Type Safety** - Full Python type hints
6. **Testing** - Pytest suite with fixtures

## 📝 Future Enhancements

- [ ] REST API with FastAPI
- [ ] Web dashboard
- [ ] Distributed processing
- [ ] GPU batching optimization
- [ ] Real-time preview streaming
- [ ] Model compression (quantization)
- [ ] Mobile app support

---

**Status:** ✅ Production Ready

**Last Updated:** 2026-06-30


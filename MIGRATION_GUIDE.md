# 📦 Migration Guide - Old Scripts to New CLI

If you were using the old scripts, here's how to migrate to the new CLI-based system.

---

## 🔄 Before and After

### BEFORE: Old Script Approach
```bash
# Modify run_tello_reconstruction.py
nano run_tello_reconstruction.py
# Edit: CHECKPOINT, CHUNK_SIZE, IMAGE_RESOLUTION, etc...
python run_tello_reconstruction.py

# Different script for videos
nano run_video_reconstruction.py
python run_video_reconstruction.py

# Completely separate rebuild script
python rebuild_mission.py
```

### AFTER: Modern CLI
```bash
# Create config once
tello-vggt init-config

# Use same CLI for everything
tello-vggt record --duration 300
tello-vggt video input.mp4
tello-vggt rebuild missions/mission_001
tello-vggt gaussian-splatting missions/mission_001
```

---

## 🚀 Migration Steps

### Step 1: Backup Old Data
```bash
# Backup existing missions (optional)
cp -r missions missions.backup
```

### Step 2: Install New Version
```bash
# Update package
cd /home/jetson/Desktop/tello_vggt
pip install -e ".[all]"

# Verify installation
tello-vggt --help
```

### Step 3: Create Configuration File
```bash
# Generate default config
tello-vggt init-config --output my_config.yaml

# Review and edit if needed
cat my_config.yaml
```

### Step 4: Migrate Your Settings

If you had settings in the old scripts like:

**OLD:**
```python
# run_tello_reconstruction.py
CHUNK_SIZE = 100
OVERLAP = 5
CHECKPOINT = "checkpoints/model.pt"
IMAGE_RESOLUTION = 512
MODE = "balanced"
```

**NEW:**
```yaml
# my_config.yaml
inference:
  chunk_size: 100
  overlap: 5
  
vggt:
  checkpoint_path: "checkpoints/model.pt"
  image_resolution: 512
  mode: balanced
```

### Step 5: Use New CLI

**OLD Tello Recording:**
```python
# Edit run_tello_reconstruction.py
# Set: CHUNK_SIZE, OVERLAP, CHECKPOINT
python run_tello_reconstruction.py
```

**NEW Tello Recording:**
```bash
tello-vggt record --duration 300 --config my_config.yaml
```

**OLD Video Processing:**
```python
# run_video_reconstruction.py with hardcoded paths
python run_video_reconstruction.py
```

**NEW Video Processing:**
```bash
tello-vggt video video.mp4 --config my_config.yaml
```

**OLD Rebuild:**
```python
# rebuild_mission.py
# Edit: missions path
python rebuild_mission.py
```

**NEW Rebuild:**
```bash
tello-vggt rebuild missions/mission_001 --config my_config.yaml
```

---

## 🎯 Common Conversions

### Scenario 1: Process Video with Custom Chunk Size
**OLD:**
```python
# run_video_reconstruction.py
CHUNK_SIZE = 50
python run_video_reconstruction.py
```

**NEW:**
```bash
# config.yaml
inference:
  chunk_size: 50

# Command
tello-vggt video input.mp4 --config config.yaml
```

### Scenario 2: Use CPU Instead of GPU
**OLD:**
```python
# run_video_reconstruction.py
inferencer = VGGTOmegaTelloInferencer(
    device="cpu",  # ← Change this
    ...
)
```

**NEW:**
```yaml
# config.yaml
vggt:
  device: cpu
```

### Scenario 3: Increase Image Resolution
**OLD:**
```python
# run_tello_reconstruction.py
IMAGE_RESOLUTION = 1024
```

**NEW:**
```yaml
# config.yaml
vggt:
  image_resolution: 1024
```

### Scenario 4: Skip Inference
**OLD:**
```python
# Manually comment out inference code
```

**NEW:**
```bash
tello-vggt video input.mp4 --skip-inference
```

### Scenario 5: Skip Export
**OLD:**
```python
# Comment out export calls
```

**NEW:**
```bash
tello-vggt video input.mp4 --skip-export
```

---

## 📂 Project Structure Changes

### Before
```
tello_vggt/
├── run_tello_reconstruction.py
├── run_video_reconstruction.py
├── rebuild_mission.py
└── src/
    └── tello_vggt/
        ├── __init__.py
        └── [implementation files]
```

### After
```
tello_vggt/
├── run_tello_reconstruction.py        (Kept for compatibility)
├── run_video_reconstruction.py        (Kept for compatibility)
├── rebuild_mission.py                 (Now uses CLI)
├── config.example.yaml                (NEW)
├── src/
│   └── tello_vggt/
│       ├── __init__.py
│       ├── core/                      (NEW)
│       │   ├── config.py
│       │   ├── logging_config.py
│       │   └── mission.py
│       ├── cli/                       (NEW)
│       │   ├── main.py
│       │   └── commands/
│       ├── rendering/                 (NEW)
│       │   ├── gaussian_splatting.py
│       │   └── deep_anything_v3.py
│       └── [legacy files]
└── tests/                             (NEW)
    ├── conftest.py
    ├── test_config.py
    └── test_mission.py
```

---

## 🔄 Backward Compatibility

### Old Scripts Still Work ✅
The original scripts (`run_tello_reconstruction.py`, `run_video_reconstruction.py`) are **still functional** for backward compatibility.

But you should migrate to CLI for:
- Better configuration management
- Cleaner code
- New features (GS, segmentation)
- Better error handling
- Structured logging

### Gradual Migration
You can migrate gradually:

```bash
# Use old for some tasks
python run_tello_reconstruction.py

# Use new for new tasks
tello-vggt gaussian-splatting missions/mission_001
```

---

## 🛠️ Troubleshooting Migration

### Issue 1: Config File Not Found
```bash
# Create in current directory
tello-vggt init-config --output ./config.yaml
tello-vggt video input.mp4 --config ./config.yaml
```

### Issue 2: Old Mission Data Format
```bash
# Old missions still work!
tello-vggt list-missions
tello-vggt rebuild missions/old_mission_001
```

### Issue 3: Different Output Path
```yaml
# config.yaml
missions_dir: "missions"  # Customize if needed
```

### Issue 4: Missing Dependencies
```bash
# Reinstall with all extras
pip install -e ".[all]"

# Or just core
pip install -e .
```

---

## ✨ New Features You Get

### Automatic Mission Tracking
```bash
# See all your missions
tello-vggt list-missions

# Output:
# ✅ mission_001 [completed]
# ✅ mission_002 [completed]
# 🔄 mission_003 [inferenced]
```

### Gaussian Splatting
```bash
# Convert to real-time renderable format
tello-vggt gaussian-splatting missions/mission_001
# → Output: gaussians.ply for Cloud Compare, Blender, etc.
```

### Semantic Segmentation
```bash
# Extract semantic objects
tello-vggt semantic-segmentation missions/mission_001 \
  --checkpoint deep_anything_v3.pt
# → Output: class_0.ply, class_1.ply, ...
```

### Better Logging
```bash
# All operations logged to files
tail -f missions/mission_001/logs/mission_001.log

# View timing, GPU usage, progress
```

### Configuration Management
```bash
# Share config across team
cp config.yaml config.backup.yaml

# View current config
tello-vggt show-config

# Create different profiles
tello-vggt init-config --output config.low_res.yaml
tello-vggt init-config --output config.high_res.yaml
```

---

## 🎓 Learning the New System

### Quick Examples
```bash
# 1. Initialize
tello-vggt init-config

# 2. View help
tello-vggt video --help

# 3. Process video
tello-vggt video input.mp4

# 4. See results
ls missions/
tello-vggt list-missions

# 5. Generate GS
tello-vggt gaussian-splatting missions/mission_001

# 6. View results
open missions/mission_001/output/reconstruction.glb
```

### Documentation
- **Quick Start:** [QUICK_START.md](QUICK_START.md)
- **Architecture:** [ARCHITECTURE_REFACTORED.md](ARCHITECTURE_REFACTORED.md)
- **Configuration:** [config.example.yaml](config.example.yaml)

---

## ⏰ Timeline

### Immediate (Now)
- [x] CLI system implemented
- [x] Configuration system ready
- [x] All old scripts still work
- [x] New features available

### Short term (Recommended)
- [ ] Migrate your configurations to YAML
- [ ] Update any automation scripts to use CLI
- [ ] Test new features (GS, segmentation)

### Long term
- [ ] Deprecate old scripts (still functional)
- [ ] Contribute improvements
- [ ] Share configurations with team

---

## 💡 Tips

### Tip 1: Create Multiple Configs
```bash
tello-vggt init-config --output config.production.yaml
tello-vggt init-config --output config.dev.yaml
tello-vggt init-config --output config.research.yaml

# Use appropriate config
tello-vggt video input.mp4 --config config.production.yaml
```

### Tip 2: Alias for Convenience
```bash
# In ~/.bashrc or ~/.zshrc
alias tv='tello-vggt'

# Usage
tv video input.mp4
tv list-missions
tv show-config
```

### Tip 3: Default Config
```bash
# Create default config in project root
tello-vggt init-config --output config.yaml

# Then just use
tello-vggt video input.mp4  # Automatically finds config.yaml
```

### Tip 4: Log Everything
```yaml
# config.yaml
log_level: "DEBUG"  # During development
log_to_file: true   # Always save logs
```

---

## ✅ Checklist

- [ ] Backup old data
- [ ] Install new package
- [ ] Create configuration file
- [ ] Test with sample video
- [ ] View output
- [ ] Try new features (GS, segmentation)
- [ ] Update automation scripts
- [ ] Share config with team

---

## 🎉 You're Done!

The migration is complete. You now have:
- ✅ Modern CLI interface
- ✅ YAML-based configuration
- ✅ Structured logging
- ✅ Mission management
- ✅ Gaussian Splatting support
- ✅ Semantic segmentation
- ✅ Backward compatibility

**Start using the new system:**
```bash
tello-vggt init-config
tello-vggt video your_video.mp4
```

Enjoy! 🚀


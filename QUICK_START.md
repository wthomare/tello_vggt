# 🚀 Quick Start Guide - Refactored Tello VGGT-Omega

## 📋 Résumé des Changements

Vous pouvez maintenant utiliser le projet avec une **CLI unifiée et moderne**!

### ✨ Avant vs Après

**AVANT:**
```bash
# 3 scripts différents à modifier
python run_tello_reconstruction.py  # Modifier CHUNK_SIZE, checkpoint, etc...
python run_video_reconstruction.py   # Modifier paths hard-codées
python rebuild_mission.py            # Pas de CLI, code brut
```

**APRÈS:**
```bash
# CLI moderne avec Typer + Config
tello-vggt record --duration 300 --config config.yaml
tello-vggt video video.mp4 --config config.yaml
tello-vggt rebuild missions/mission_001
tello-vggt gaussian-splatting missions/mission_001
```

---

## 🎯 Installation (5 min)

### 1. **Installer le package**
```bash
cd /home/jetson/Desktop/tello_vggt

# Installation development
pip install -e .

# Ou avec tous les extras
pip install -e ".[all]"
```

### 2. **Créer un fichier de config**
```bash
tello-vggt init-config --output config.yaml

# Éditer config.yaml si nécessaire
nano config.yaml
```

### 3. **Vérifier l'installation**
```bash
tello-vggt --help
tello-vggt show-config
```

---

## 🎬 Utilisation Rapide

### Workflow 1: Reconstruction depuis Vidéo
```bash
# Traiter une vidéo
tello-vggt video mon_video.mp4 \
  --config config.yaml \
  --output missions/mon_mission

# Output:
# missions/mon_mission/
#   ├── frames/           (images extraites)
#   ├── chunks/           (résultats VGGT)
#   └── output/
#       └── reconstruction.glb  ✅ Votre fichier 3D!
```

### Workflow 2: Reconstruction + Gaussian Splatting
```bash
# Traiter vidéo
tello-vggt video mon_video.mp4 --output missions/mission_gs

# Générer Gaussian Splatting
tello-vggt gaussian-splatting missions/mission_gs

# Output supplémentaire:
# missions/mission_gs/gaussian_splatting/
#   ├── mission_gs_gaussians.npz   (modèle)
#   └── mission_gs_gaussians.ply   ✅ Point cloud viewer!
```

### Workflow 3: Segmentation Sémantique
```bash
# Traiter vidéo
tello-vggt video mon_video.mp4 --output missions/mission_seg

# Générer segmentation avec Deep Anything V3
tello-vggt semantic-segmentation missions/mission_seg \
  --checkpoint deep_anything_v3.pt

# Output:
# missions/mission_seg/semantic_segmentation/
#   ├── segmentation.npz         (masques)
#   ├── class_0.ply              ✅ Object 1
#   ├── class_1.ply              ✅ Object 2
#   └── ...
```

### Workflow 4: Enregistrement Tello
```bash
# Enregistrer depuis drone (300s)
tello-vggt record --duration 300 --output missions/tello_flight

# Puis traiter automatiquement
tello-vggt rebuild missions/tello_flight
```

---

## 🔧 Configuration

### Option 1: Via YAML (Recommandé)
```bash
# Créer config.yaml
tello-vggt init-config --output config.yaml

# Éditer le fichier
# Puis utiliser:
tello-vggt video input.mp4 --config config.yaml
```

### Option 2: Via ligne de commande
```bash
tello-vggt video input.mp4 \
  --log-level DEBUG \
  --verbose
```

### Option 3: Config par défaut
```bash
# Utilise les valeurs par défaut
tello-vggt video input.mp4
```

---

## 📊 Viewing Results

### Fichiers générés

```
missions/
└── mission_001/
    ├── frames/                    # Images extraites
    │   ├── frame_000000.jpg
    │   ├── frame_000001.jpg
    │   └── ...
    ├── chunks/                    # Résultats VGGT intermédiaires
    │   ├── chunk_00000.npz
    │   ├── chunk_00001.npz
    │   └── ...
    ├── output/
    │   ├── reconstruction.glb      # ✅ Importer dans Blender
    │   └── mission_001_reconstruction.glb
    ├── gaussian_splatting/        # (Si --gaussian-splatting)
    │   ├── gaussians.ply
    │   └── gaussians.npz
    ├── semantic_segmentation/     # (Si --semantic-segmentation)
    │   ├── class_0.ply
    │   ├── class_1.ply
    │   └── segmentation.npz
    ├── logs/
    │   ├── app.log
    │   └── mission_001.log        # Logs détaillés
    └── mission.json               # Métadonnées
```

### Viewer Recommendations

**GLB (Standard):**
- Blender (Import → Shading nodes)
- Three.js viewer (web)
- Model Viewer (Google)

**PLY (Point Cloud):**
- CloudCompare
- Meshlab
- MeshLab
- Blender (Add Point Cloud plugin)

**Segmentation:**
- CloudCompare (color by class)
- Custom Python viewer (numpy + matplotlib)

---

## 🛠️ Common Tasks

### List all missions
```bash
tello-vggt list-missions --config config.yaml

# Output:
# ✅ mission_001 [completed] | Frames: 300 | Chunks: 3
# 🔄 mission_002 [inferenced] | Frames: 250 | Chunks: 2
# ❌ mission_003 [failed] | Frames: 100 | Chunks: 0
```

### Rebuild existing mission
```bash
# Si vous avez les chunks mais pas le GLB
tello-vggt rebuild missions/mission_001

# Force re-export même si GLB existe
tello-vggt rebuild missions/mission_001 --re-export
```

### Change log level
```bash
tello-vggt video input.mp4 --log-level DEBUG  # Verbose
tello-vggt video input.mp4 --log-level ERROR  # Silent
```

### View config
```bash
# Afficher config courante
tello-vggt show-config

# Sauvegarder config
tello-vggt show-config --output current_config.yaml
```

---

## 🚨 Troubleshooting

### ImportError: No module named 'pydantic'
```bash
pip install pydantic>=2.0 typer click
```

### CUDA out of memory
```yaml
# config.yaml
vggt:
  image_resolution: 256  # Réduire résolution
  device: cpu            # Ou utiliser CPU
  half_precision: true   # Ou utiliser FP16
```

### "Module not found: vggt"
```bash
pip install -e ".[vggt]"  # Installer dépendances optionnelles
```

### Mission stuck in "recording" status
```bash
# Éditer mission.json
nano missions/mission_001/mission.json

# Changer status à "recorded"
# Puis relancer rebuild
```

---

## 📚 Documentation

```bash
# Voir tous les fichiers docs
ls -la *.md

# Architecture complète
cat ARCHITECTURE_REFACTORED.md

# Analyse & recommandations
cat ANALYSIS_AND_RECOMMENDATIONS.md

# Corrections appliquées
cat CORRECTIONS_SUMMARY.md
```

---

## 🔬 Advanced Usage

### Python API
```python
from tello_vggt.core.config import load_config
from tello_vggt.cli.commands.video import cmd_video
from tello_vggt.core.logging_config import setup_logging

# Setup
setup_logging("DEBUG", "logs")
config = load_config("config.yaml")

# Process
glb_path = cmd_video(
    config=config,
    video_path="input.mp4",
    output_dir=Path("missions/custom")
)

print(f"✅ Generated: {glb_path}")
```

### Custom Gaussian Splatting
```python
from tello_vggt.rendering.gaussian_splatting import GaussianSplattingTrainer
from tello_vggt.mission_loader import MissionLoader

# Load mission data
chunks = MissionLoader.load_chunks("missions/mission_001/chunks")

# Train GS
trainer = GaussianSplattingTrainer(sh_degree=3, iterations=7000)
gs_result = trainer.train_from_vggt(
    chunks[0],
    camera_poses=...,
    camera_intrinsics=...,
    images=...
)

# Export
gs_result.save("gaussians.npz")
```

---

## ✅ Checklist de Démarrage

- [ ] Installation: `pip install -e .`
- [ ] Config: `tello-vggt init-config`
- [ ] Test: `tello-vggt show-config`
- [ ] Premier test: `tello-vggt video test_video.mp4`
- [ ] Vérifier output dans `missions/`
- [ ] Ouvrir GLB dans Blender

---

## 📞 Support

Si vous avez des problèmes:

1. **Vérifier les logs:**
   ```bash
   tail -f logs/app.log
   tail -f missions/mission_001/logs/mission_001.log
   ```

2. **Activer debug:**
   ```bash
   tello-vggt video input.mp4 --verbose
   ```

3. **Vérifier config:**
   ```bash
   tello-vggt show-config | head -20
   ```

4. **Lire la doc:**
   ```bash
   cat ARCHITECTURE_REFACTORED.md
   ```

---

**🎉 Vous êtes prêt à utiliser la nouvelle version!**

Lancez votre première reconstruction:
```bash
tello-vggt video mon_video.mp4 --config config.yaml
```

Ensuite, explorez Gaussian Splatting:
```bash
tello-vggt gaussian-splatting missions/mission_001
```

Amusez-vous! 🚀


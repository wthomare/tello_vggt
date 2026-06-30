"""
Script pour reconstruire les GLB depuis des chunks VGGT déjà calculés.

Utilisation:
    python rebuild_mission.py <mission_dir>
"""

import sys
from pathlib import Path

from tello_vggt.mission_loader import MissionLoader, load_frames
from tello_vggt.vggt_chunk_fusioner import VGGTChunkFusioner
from tello_vggt.vggt_chunk_result import VGGTGlbExporter


def rebuild_mission(mission_dir: str | Path) -> Path:
    """
    Reconstruis un GLB à partir d'une mission existante.
    
    Args:
        mission_dir: Chemin vers le répertoire mission (contient "chunks/" et "frames/")
    
    Returns:
        Chemin du fichier GLB généré
    """
    mission_dir = Path(mission_dir)
    
    if not mission_dir.exists():
        raise FileNotFoundError(f"Mission directory not found: {mission_dir}")
    
    chunks_dir = mission_dir / "chunks"
    frames_dir = mission_dir / "frames"
    
    if not chunks_dir.exists():
        raise FileNotFoundError(f"Chunks directory not found: {chunks_dir}")
    if not frames_dir.exists():
        raise FileNotFoundError(f"Frames directory not found: {frames_dir}")
    
    print(f"📂 Loading mission from: {mission_dir}")
    
    # Charger les chunks
    print(f"📦 Loading chunks from: {chunks_dir}")
    chunks = MissionLoader.load_chunks(chunks_dir)
    if not chunks:
        raise RuntimeError(f"No chunks found in {chunks_dir}")
    print(f"✅ Loaded {len(chunks)} chunks")
    
    # Fusionner les chunks
    print("🔗 Fusing chunks...")
    fusioner = VGGTChunkFusioner(
        min_overlap=1,
        max_overlap=20,
        use_allclose=True,
    )
    fusioner.extend(chunks)
    fused_result = fusioner.fuse()
    print(f"✅ Fused result shape: {fused_result.depth.shape[0]} frames")
    
    # Charger les frames
    print(f"🎬 Loading frames from: {frames_dir}")
    frames = load_frames(frames_dir)
    print(f"✅ Loaded {len(frames)} frames")
    
    # Vérifier la cohérence
    if fused_result.depth.shape[0] != len(frames):
        print(f"⚠️  Warning: Frame count mismatch! Predictions: {fused_result.depth.shape[0]}, Frames: {len(frames)}")
        print(f"   Using only the first {min(fused_result.depth.shape[0], len(frames))} frames")
        frames = frames[:fused_result.depth.shape[0]]
    
    # Exporter GLB
    print("🎨 Exporting GLB...")
    exporter = VGGTGlbExporter(input_is_bgr=True)
    
    output_path = mission_dir / "reconstruction.glb"
    glb_path = exporter.export_glb(
        result=fused_result,
        out_path=output_path,
        frames=frames,
        conf_thres=50.0,
        show_cam=True,
    )
    
    print(f"✅ GLB exported to: {glb_path}")
    return glb_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python rebuild_mission.py <mission_dir>")
        print("Example: python rebuild_mission.py missions/mission_20240630_120000")
        sys.exit(1)
    
    mission_dir = sys.argv[1]
    
    try:
        glb_path = rebuild_mission(mission_dir)
        print(f"\n✨ Success! Generated: {glb_path}")
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)

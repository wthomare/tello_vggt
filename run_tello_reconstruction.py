from __future__ import annotations

import gc
import json
from collections import deque
from datetime import datetime
from pathlib import Path

import cv2
import torch
from djitellopy import Tello

from tello_vggt.vggt_chunk_fusioner import VGGTChunkFusioner
from tello_vggt.vggt_chunk_result import (
    VGGTChunkResult,
    VGGTGlbExporter,
)
from tello_vggt.vggt_omega_tello_inferencer import (
    VGGTOmegaTelloInferencer,
)

from tello_vggt.mission_loader import (MissionLoader,
                                       load_frames)

# ============================================================================
# Configuration
# ============================================================================

CHUNK_SIZE = 100
OVERLAP = 5

CHECKPOINT = "checkpoints/model.pt"

IMAGE_RESOLUTION = 512
MODE = "balanced"

CONF_THRESHOLD = 50.0


# ============================================================================
# Main
# ============================================================================


def main():

    # ------------------------------------------------------------------
    # Mission creation
    # ------------------------------------------------------------------

    mission_name = datetime.now().strftime(
        "mission_%Y%m%d_%H%M%S"
    )

    mission_dir = Path("missions") / mission_name

    chunks_dir = mission_dir / "chunks"
    frames_dir = mission_dir / "frames"

    chunks_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    mission_metadata = {
        "mission_name": mission_name,
        "chunk_size": CHUNK_SIZE,
        "overlap": OVERLAP,
        "image_resolution": IMAGE_RESOLUTION,
        "checkpoint": CHECKPOINT,
        "start_time": datetime.now().isoformat(),
    }

    with open(
        mission_dir / "mission.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            mission_metadata,
            f,
            indent=4,
        )

    # ------------------------------------------------------------------
    # VGGT
    # ------------------------------------------------------------------

    inferencer = VGGTOmegaTelloInferencer(
        checkpoint_path=CHECKPOINT,
        device="cuda",
        image_resolution=IMAGE_RESOLUTION,
        mode=MODE,
        input_is_bgr=True,
    )

    # ------------------------------------------------------------------
    # Tello
    # ------------------------------------------------------------------

    tello = Tello()

    tello.connect()

    print()
    print("Battery:", tello.get_battery(), "%")
    print()

    tello.streamon()

    frame_reader = tello.get_frame_read()

    # Décommenter si tu veux décoller automatiquement
    # tello.takeoff()

    chunk_frames = []

    overlap_frames = deque(
        maxlen=OVERLAP
    )

    chunk_count = 0
    global_frame_idx = 0

    print()
    print("Recording...")
    print("Press CTRL+C to stop.")
    print()

    # ------------------------------------------------------------------
    # Flight loop
    # ------------------------------------------------------------------

    try:

        while True:

            frame = frame_reader.frame

            if frame is None:
                continue

            # Sauvegarde frame
            frame_path = (
                frames_dir
                / f"frame_{global_frame_idx:07d}.jpg"
            )

            cv2.imwrite(
                str(frame_path),
                frame,
            )

            global_frame_idx += 1

            chunk_frames.append(frame)

            if len(chunk_frames) < CHUNK_SIZE:
                continue

            print()
            print(
                f"[Chunk {chunk_count}] "
                f"Running VGGT inference..."
            )

            result = inferencer.infer_frames(
                chunk_frames
            )

            chunk_path = (
                chunks_dir
                / f"chunk_{chunk_count:05d}.npz"
            )

            result.save(chunk_path)

            print(
                f"[Chunk {chunk_count}] "
                f"saved -> {chunk_path.name}"
            )

            # ----------------------------------------------------------
            # Free RAM / VRAM
            # ----------------------------------------------------------

            del result

            gc.collect()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # ----------------------------------------------------------

            overlap_frames.clear()

            overlap_frames.extend(
                chunk_frames[-OVERLAP:]
            )

            chunk_frames = list(
                overlap_frames
            )

            chunk_count += 1

    except KeyboardInterrupt:

        print()
        print("Flight terminated by user.")

    finally:

        try:
            tello.streamoff()
        except Exception:
            pass

        try:
            tello.end()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Last partial chunk
    # ------------------------------------------------------------------

    if len(chunk_frames) > OVERLAP:

        print()
        print("Processing last partial chunk...")

        result = inferencer.infer_frames(
            chunk_frames
        )

        chunk_path = (
            chunks_dir
            / f"chunk_{chunk_count:05d}.npz"
        )

        result.save(chunk_path)

        del result

        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        chunk_count += 1

    # ------------------------------------------------------------------
    # Update metadata
    # ------------------------------------------------------------------

    mission_metadata["num_chunks"] = chunk_count
    mission_metadata["num_frames"] = global_frame_idx
    mission_metadata["end_time"] = datetime.now().isoformat()

    with open(
        mission_dir / "mission.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            mission_metadata,
            f,
            indent=4,
        )

    # ------------------------------------------------------------------
    # Reload chunks
    # ------------------------------------------------------------------

    print()
    print("Loading chunks from disk...")

    chunks = MissionLoader.load_chunks(
        chunks_dir
    )

    print(
        f"{len(chunks)} chunks loaded."
    )

    # ------------------------------------------------------------------
    # Fusion
    # ------------------------------------------------------------------

    print()
    print("Fusing chunks...")

    fusioner = VGGTChunkFusioner(
        min_overlap=OVERLAP,
        max_overlap=OVERLAP,
        use_allclose=False,
    )

    fusioner.extend(chunks)

    merged_result = fusioner.fuse()

    print(
        "Total frames after fusion:",
        merged_result.extrinsics.shape[0],
    )

    # ------------------------------------------------------------------
    # Reload frames
    # ------------------------------------------------------------------

    print()
    print("Loading frames...")

    frames = load_frames(
        frames_dir
    )

    print(
        f"{len(frames)} frames loaded."
    )

    # ------------------------------------------------------------------
    # GLB export
    # ------------------------------------------------------------------

    print()
    print("Exporting GLB...")

    exporter = VGGTGlbExporter(
        input_is_bgr=True
    )

    output_glb = (
        mission_dir
        / "reconstruction.glb"
    )

    exporter.export_glb(
        result=merged_result,
        frames=frames,
        out_path=output_glb,
        conf_thres=CONF_THRESHOLD,
        show_cam=True,
    )

    print()
    print("Mission completed.")
    print("Mission:", mission_dir)
    print("GLB:", output_glb)
    print()


if __name__ == "__main__":
    main()
from pathlib import Path

import cv2
import torch

from tello_vggt.vggt_omega_tello_inferencer import (
    VGGTOmegaTelloInferencer
)
from tello_vggt.mission_loader import (
    MissionLoader,
    load_frames
)
from tello_vggt.vggt_chunk_fusioner import (
    VGGTChunkFusioner
)
from tello_vggt.vggt_chunk_result import (
    VGGTGlbExporter
)


def video_frame_generator(video_path):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise RuntimeError(
            f"Unable to open {video_path}"
        )

    while True:
        ok, frame = cap.read()

        if not ok:
            break

        yield frame

    cap.release()

def run_inference(
    video_path,
    checkpoint_path,
    chunks_dir,
    chunk_size=100,
    overlap=5,
):
    chunks_dir = Path(chunks_dir)
    chunks_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    inferencer = (
        VGGTOmegaTelloInferencer(
            checkpoint_path=checkpoint_path,
            device="cuda",
            image_resolution=512,
            mode="balanced",
        )
    )

    for chunk_id, result in enumerate(
        inferencer.infer_stream(
            video_frame_generator(video_path),
            chunk_size=chunk_size,
            overlap=overlap,
        )
    ):
        chunk_file = (
            chunks_dir /
            f"chunk_{chunk_id:05d}.npz"
        )

        result.save(chunk_file)

        print(
            f"saved {chunk_file}"
        )

        del result
        torch.cuda.empty_cache()

def load_and_fuse(chunks_dir):
    chunks = MissionLoader.load_chunks(
        chunks_dir
    )
    if not chunks:
        raise RuntimeError(
            "No chunk found."
        )

    fusioner = VGGTChunkFusioner(
                                min_overlap=5,
                                max_overlap=5,
                                use_allclose=True,
                            )

    fusioner.extend(chunks)

    return fusioner.fuse()


def extract_frames(
    video_path,
    frames_dir
):
    frames_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    cap = cv2.VideoCapture(
        str(video_path)
    )

    idx = 0

    while True:
        ok, frame = cap.read()

        if not ok:
            break

        cv2.imwrite(
            str(
                frames_dir /
                f"frame_{idx:06d}.jpg"
            ),
            frame
        )

        idx += 1

    cap.release()


def main():

    extract_frames(
        "mission.mp4",
        Path("mission/frames")
    )

    run_inference(
        video_path="mission.mp4",
        checkpoint_path="VGGT-Omega.pt",
        chunks_dir="mission/chunks",
        chunk_size=100,
        overlap=5,
    )

    fused_result = load_and_fuse(
        "mission/chunks"
    )

    fused_result.save(
        "mission/fused_result.npz"
    )

    frames = load_frames(
        "mission/frames"
    )

    if fused_result.depth.shape[0] != len(frames):
        raise RuntimeError(
            f"Frame mismatch: "
            f"{fused_result.depth.shape[0]} predictions "
            f"vs {len(frames)} images"
        )

    exporter = VGGTGlbExporter()

    exporter.export_glb(
        fused_result,
        "mission.glb",
        frames=frames,
    )


if __name__ == "__main__":
    main()

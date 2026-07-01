from pathlib import Path

import cv2
from tello_vggt.vggt_chunk_result import VGGTChunkResult


class MissionLoader:

    @staticmethod
    def load_chunks(chunks_dir: str | Path):

        chunks_dir = Path(chunks_dir)

        files = sorted(
            chunks_dir.glob("chunk_*.npz")
        )

        return [
            VGGTChunkResult.load(f)
            for f in files
        ]
    


def load_frames(frames_dir: str | Path):

    frames_dir = Path(frames_dir)

    frame_files = sorted(
        [
            *frames_dir.glob("frame_*.jpg"),
            *frames_dir.glob("frame_*.jpeg"),
            *frames_dir.glob("frame_*.png"),
        ]
    )

    frames = []

    for frame_file in frame_files:

        frame = cv2.imread(str(frame_file))

        if frame is None:
            raise RuntimeError(
                f"Unable to load frame {frame_file}"
            )

        frames.append(frame)

    return frames

"""Tello VGGT-Omega 3D Reconstruction Pipeline."""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = [
    "MissionLoader",
    "load_frames",
    "VGGTChunkResult",
    "VGGTGlbExporter",
    "VGGTChunkFusioner",
    "fuse_vggt_chunks",
    "VGGTOmegaTelloInferencer",
    "TelloSegmentRecorder",
]


def __getattr__(name: str):
    """Lazy-load optional pipeline objects so config/CLI imports stay lightweight."""
    if name in {"MissionLoader", "load_frames"}:
        from tello_vggt.mission_loader import MissionLoader, load_frames

        return {"MissionLoader": MissionLoader, "load_frames": load_frames}[name]

    if name in {"VGGTChunkResult", "VGGTGlbExporter"}:
        from tello_vggt.vggt_chunk_result import VGGTChunkResult, VGGTGlbExporter

        return {"VGGTChunkResult": VGGTChunkResult, "VGGTGlbExporter": VGGTGlbExporter}[name]

    if name in {"VGGTChunkFusioner", "fuse_vggt_chunks"}:
        from tello_vggt.vggt_chunk_fusioner import VGGTChunkFusioner, fuse_vggt_chunks

        return {
            "VGGTChunkFusioner": VGGTChunkFusioner,
            "fuse_vggt_chunks": fuse_vggt_chunks,
        }[name]

    if name == "VGGTOmegaTelloInferencer":
        from tello_vggt.vggt_omega_tello_inferencer import VGGTOmegaTelloInferencer

        return VGGTOmegaTelloInferencer

    if name == "TelloSegmentRecorder":
        from tello_vggt.video_recorder import TelloSegmentRecorder

        return TelloSegmentRecorder

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

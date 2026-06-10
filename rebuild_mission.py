from tello_vggt.mission_loader import MissionLoader
from tello_vggt.vggt_chunk_fusioner import VGGTChunkFusioner
from tello_vggt.vggt_chunk_result import VGGTGlbExporter

chunks = MissionLoader.load_chunks(
    "missions/mission_001/chunks"
)

fusioner = VGGTChunkFusioner()

fusioner.extend(chunks)

result = fusioner.fuse()

exporter = VGGTGlbExporter(
    input_is_bgr=True,
)

exporter.export_glb(
    result=result,
    frames=...
)
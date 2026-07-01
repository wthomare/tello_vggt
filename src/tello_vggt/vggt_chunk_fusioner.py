from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Callable
import numpy as np

from tello_vggt.vggt_chunk_result import VGGTChunkResult


@dataclass
class VGGTChunkFusioner:
    """
    Fusionne une suite de VGGTChunkResult en détectant le recouvrement
    entre la fin du chunk précédent et le début du chunk suivant.

    Par défaut, la détection de recouvrement se fait en comparant les tenseurs
    extrinsics/intrinsics/depth/depth_conf sur une fenêtre glissante.
    """
    min_overlap: int = 1
    max_overlap: int = 20
    use_allclose: bool = False
    rtol: float = 1e-5
    atol: float = 1e-8
    compare_raw_keys: Tuple[str, ...] = ()
    prefer_largest_overlap: bool = True

    _chunks: List[VGGTChunkResult] = field(default_factory=list, init=False)

    def add(self, chunk: VGGTChunkResult) -> None:
        self._chunks.append(chunk)

    def extend(self, chunks: Sequence[VGGTChunkResult]) -> None:
        for chunk in chunks:
            self.add(chunk)

    def fuse(self) -> VGGTChunkResult:
        if not self._chunks:
            raise ValueError("Aucun chunk à fusionner.")
        if len(self._chunks) == 1:
            return self._chunks[0]

        fused = self._chunks[0]
        for nxt in self._chunks[1:]:
            overlap = self._find_overlap(fused, nxt)
            fused = self._concat(fused, nxt, overlap)

        return fused

    def _find_overlap(self, left: VGGTChunkResult, right: VGGTChunkResult) -> int:
        """
        Cherche le plus grand overlap k tel que:
        left[-k:] == right[:k]
        """
        left_len = self._frame_count(left)
        right_len = self._frame_count(right)
        max_k = min(self.max_overlap, left_len, right_len)

        candidates = range(max_k, self.min_overlap - 1, -1) if self.prefer_largest_overlap \
            else range(self.min_overlap, max_k + 1)

        for k in candidates:
            if self._chunks_match(left, right, k):
                return k

        return 0

    def _chunks_match(self, left: VGGTChunkResult, right: VGGTChunkResult, k: int) -> bool:
        # Compare les tenseurs principaux frame par frame
        if not self._match_array_tail_head(left.extrinsics, right.extrinsics, k):
            return False
        if not self._match_array_tail_head(left.intrinsics, right.intrinsics, k):
            return False
        if not self._match_array_tail_head(left.depth, right.depth, k):
            return False
        if not self._match_array_tail_head(left.depth_conf, right.depth_conf, k):
            return False

        # Compare éventuellement certaines entrées de raw si elles existent
        for key in self.compare_raw_keys:
            if key not in left.raw or key not in right.raw:
                return False
            if not self._match_any_tail_head(left.raw[key], right.raw[key], k):
                return False

        return True

    def _match_array_tail_head(self, left: np.ndarray, right: np.ndarray, k: int) -> bool:
        try:
            a = left[-k:]
            b = right[:k]
        except Exception:
            return False

        if a.shape != b.shape:
            return False

        if self.use_allclose:
            return np.allclose(a, b, rtol=self.rtol, atol=self.atol, equal_nan=True)
        return np.array_equal(a, b)

    def _match_any_tail_head(self, left_obj: Any, right_obj: Any, k: int) -> bool:
        """
        Comparaison générique pour raw.
        - si c'est un np.ndarray, on compare comme les tenseurs
        - si c'est une liste/tuple, on compare les k derniers / k premiers éléments
        - sinon, on tente une égalité stricte sur les slices si possible
        """
        if isinstance(left_obj, np.ndarray) and isinstance(right_obj, np.ndarray):
            return self._match_array_tail_head(left_obj, right_obj, k)

        if isinstance(left_obj, (list, tuple)) and isinstance(right_obj, (list, tuple)):
            if len(left_obj) < k or len(right_obj) < k:
                return False
            return left_obj[-k:] == right_obj[:k]

        return left_obj == right_obj

    def _concat(
        self,
        left: VGGTChunkResult,
        right: VGGTChunkResult,
        overlap: int,
    ) -> VGGTChunkResult:
        """
        Concatène en supprimant les frames dupliquées au début de right.
        """
        if overlap < 0:
            raise ValueError("overlap ne peut pas être négatif.")

        extrinsics = self._concat_axis0(left.extrinsics, right.extrinsics, overlap)
        intrinsics = self._concat_axis0(left.intrinsics, right.intrinsics, overlap)
        depth = self._concat_axis0(left.depth, right.depth, overlap)
        depth_conf = self._concat_axis0(left.depth_conf, right.depth_conf, overlap)

        raw = self._merge_raw(left.raw, right.raw, overlap)

        return VGGTChunkResult(
            extrinsics=extrinsics,
            intrinsics=intrinsics,
            depth=depth,
            depth_conf=depth_conf,
            raw=raw,
        )

    def _concat_axis0(self, left: np.ndarray, right: np.ndarray, overlap: int) -> np.ndarray:
        if overlap == 0:
            return np.concatenate([left, right], axis=0)
        return np.concatenate([left, right[overlap:]], axis=0)

    def _merge_raw(
        self,
        left_raw: Dict[str, Any],
        right_raw: Dict[str, Any],
        overlap: int,
    ) -> Dict[str, Any]:
        """
        Fusion simple de raw:
        - les clés communes contenant des séquences ou arrays sont concaténées en supprimant
          l'overlap côté droit
        - sinon, on garde la valeur du gauche si elle existe, sinon celle du droit
        """
        out: Dict[str, Any] = dict(left_raw)

        for key, rval in right_raw.items():
            if key not in out:
                out[key] = rval
                continue

            lval = out[key]
            out[key] = self._merge_values(lval, rval, overlap)

        return out

    def _merge_values(self, lval: Any, rval: Any, overlap: int) -> Any:
        if isinstance(lval, np.ndarray) and isinstance(rval, np.ndarray):
            if (
                lval.ndim >= 1
                and rval.ndim >= 1
                and lval.shape[0] >= overlap
                and rval.shape[0] >= overlap
            ):
                try:
                    return np.concatenate([lval, rval[overlap:]], axis=0)
                except Exception:
                    return lval
            return lval

        if isinstance(lval, list) and isinstance(rval, list):
            if overlap <= len(rval):
                return lval + rval[overlap:]
            return lval

        if isinstance(lval, tuple) and isinstance(rval, tuple):
            if overlap <= len(rval):
                return tuple(list(lval) + list(rval[overlap:]))
            return lval

        return lval

    def _frame_count(self, chunk: VGGTChunkResult) -> int:
        """
        Déduit le nombre de frames à partir du premier axe.
        On suppose que toutes les sorties ont la même longueur temporelle.
        """
        return int(chunk.extrinsics.shape[0])


def fuse_vggt_chunks(chunks: Sequence[VGGTChunkResult], **kwargs: Any) -> VGGTChunkResult:
    fusioner = VGGTChunkFusioner(**kwargs)
    fusioner.extend(chunks)
    return fusioner.fuse()

"""
fusioner = VGGTChunkFusioner(
    min_overlap=1,
    max_overlap=10,
    use_allclose=False,   #  True si on veux tolérer des petites différences numériques
)

fusioner.add(chunk_1)
fusioner.add(chunk_2)
fusioner.add(chunk_3)

merged = fusioner.fuse()
"""

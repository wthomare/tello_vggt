from __future__ import annotations

import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque, List, Optional, Tuple

import cv2
from djitellopy import Tello


class TelloSegmentRecorder:
    def __init__(
        self,
        output_dir: str = "tello_recordings",
        segment_size: int = 100,
        overlap: int = 5,
        fps: int = 30,
        frame_size: Optional[Tuple[int, int]] = None,  # (width, height)
        fourcc: str = "mp4v",
    ):
        if overlap >= segment_size:
            raise ValueError("overlap doit être strictement inférieur à segment_size")

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.segment_size = segment_size
        self.overlap = overlap
        self.fps = fps
        self.frame_size = frame_size
        self.fourcc = cv2.VideoWriter_fourcc(*fourcc)

        self.tello = Tello()
        self.frame_reader = None

        self._connected = False
        self._streaming = False
        self._running = False

    def connect(self) -> None:
        self.tello.connect()
        self.tello.streamon()
        self.frame_reader = self.tello.get_frame_read()
        self._connected = True
        self._streaming = True

    def disconnect(self) -> None:
        try:
            if self._streaming:
                self.tello.streamoff()
        finally:
            self._streaming = False
            self._connected = False

    def _get_frame(self):
        if not self.frame_reader:
            raise RuntimeError("Flux vidéo non initialisé. Appelle connect() d'abord.")
        frame = self.frame_reader.frame
        if frame is None:
            return None
        return frame

    def _prepare_frame(self, frame):
        if self.frame_size is None:
            return frame
        width, height = self.frame_size
        return cv2.resize(frame, (width, height))

    def _new_writer(self, filepath: Path):
        if self.frame_size is None:
            raise ValueError(
                "frame_size doit être défini pour créer un VideoWriter de manière fiable."
            )
        width, height = self.frame_size
        return cv2.VideoWriter(str(filepath), self.fourcc, self.fps, (width, height))

    def _segment_filename(self, index: int) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"tello_segment_{index:04d}_{ts}.mp4"

    def record(self, total_segments: Optional[int] = None) -> List[Path]:
        """
        Enregistre des segments de segment_size frames.
        Chaque segment partage les 'overlap' dernières frames du segment précédent.

        total_segments:
            - None : tourne indéfiniment jusqu'à interruption clavier (Ctrl+C)
            - entier : nombre de segments à enregistrer
        """
        if not self._connected:
            self.connect()

        self._running = True
        saved_files: List[Path] = []

        # Stocke les dernières frames du segment précédent
        previous_overlap: Deque = deque(maxlen=self.overlap)

        segment_index = 0

        try:
            while self._running:
                segment_path = self._segment_filename(segment_index)
                writer = None

                frames_for_this_segment: List = list(previous_overlap)

                # On attend d'avoir assez de frames nouvelles pour compléter le segment
                while len(frames_for_this_segment) < self.segment_size:
                    frame = self._get_frame()
                    if frame is None:
                        continue

                    frame = self._prepare_frame(frame)
                    frames_for_this_segment.append(frame)

                if self.frame_size is None:
                    h, w = frames_for_this_segment[0].shape[:2]
                    self.frame_size = (w, h)

                writer = self._new_writer(segment_path)

                for frame in frames_for_this_segment:
                    writer.write(frame)

                writer.release()
                saved_files.append(segment_path)

                # Prépare le recouvrement pour le segment suivant
                previous_overlap = deque(
                    frames_for_this_segment[-self.overlap :], maxlen=self.overlap
                )

                segment_index += 1

                if total_segments is not None and segment_index >= total_segments:
                    break

        except KeyboardInterrupt:
            print("Arrêt demandé par l'utilisateur.")
        finally:
            self._running = False
            self.disconnect()

        return saved_files

    def stop(self) -> None:
        self._running = False


if __name__ == "__main__":
    recorder = TelloSegmentRecorder(
        output_dir="recordings",
        segment_size=100,
        overlap=5,
        fps=30,
        frame_size=(960, 720),  # adapte si besoin
    )

    files = recorder.record(total_segments=3)
    print("Fichiers enregistrés :")
    for f in files:
        print(f)
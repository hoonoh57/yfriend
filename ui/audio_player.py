"""오디오 재생 엔진 — 나레이션+BGM 동시 재생, 볼륨 믹싱"""
from pathlib import Path
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl, QObject, Signal


class AudioTrackPlayer:
    """단일 오디오 트랙 플레이어"""
    def __init__(self):
        self._player = QMediaPlayer()
        self._output = QAudioOutput()
        self._player.setAudioOutput(self._output)
        self._output.setVolume(1.0)
        self._file: str = ""
        self._start_sec: float = 0.0  # 타임라인 상 시작 시각

    def load(self, file_path: str, start_sec: float = 0.0, volume: float = 1.0):
        self._file = file_path
        self._start_sec = start_sec
        self._output.setVolume(volume)
        p = Path(file_path)
        if p.exists():
            self._player.setSource(QUrl.fromLocalFile(str(p)))

    def set_volume(self, vol: float):
        self._output.setVolume(max(0.0, min(vol, 2.0)))

    @property
    def player(self):
        return self._player

    @property
    def start_sec(self):
        return self._start_sec

    @property
    def file_path(self):
        return self._file


class AudioMixer(QObject):
    """멀티 트랙 오디오 믹서 — 타임라인 시간에 맞춰 재생"""
    playback_time = Signal(float)  # 현재 재생 시간 (초)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracks: list[AudioTrackPlayer] = []
        self._playing = False
        self._current_time = 0.0

    def clear(self):
        for t in self._tracks:
            t.player.stop()
        self._tracks.clear()

    def add_track(self, file_path: str, start_sec: float, volume: float = 1.0):
        t = AudioTrackPlayer()
        t.load(file_path, start_sec, volume)
        self._tracks.append(t)
        return t

    def play_from(self, time_sec: float):
        """지정 시간부터 모든 트랙 동시 재생"""
        self._current_time = time_sec
        self._playing = True
        for t in self._tracks:
            if not t.file_path or not Path(t.file_path).exists():
                continue
            clip_offset = time_sec - t.start_sec
            if clip_offset < 0:
                t.player.stop()
            else:
                t.player.setPosition(int(clip_offset * 1000))
                t.player.play()

    def pause(self):
        self._playing = False
        for t in self._tracks:
            t.player.pause()

    def stop(self):
        self._playing = False
        for t in self._tracks:
            t.player.stop()

    def seek(self, time_sec: float):
        """시크 — 각 트랙의 오프셋 계산하여 이동"""
        self._current_time = time_sec
        for t in self._tracks:
            clip_offset = time_sec - t.start_sec
            if not t.file_path or not Path(t.file_path).exists():
                continue
            if clip_offset < 0:
                t.player.stop()
            else:
                t.player.setPosition(int(clip_offset * 1000))
                if self._playing:
                    t.player.play()

    def set_track_volume(self, index: int, volume: float):
        if 0 <= index < len(self._tracks):
            self._tracks[index].set_volume(volume)

    @property
    def is_playing(self):
        return self._playing

    @property
    def track_count(self):
        return len(self._tracks)

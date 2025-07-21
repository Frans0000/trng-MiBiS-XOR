import numpy as np
import pyaudio
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AudioCapture:
    def __init__(self, sample_rate=44100, chunk_size=1024, channels=1, format_type=pyaudio.paInt16):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.format_type = format_type
        self.pyaudio_instance = None
        self.stream = None

    def __enter__(self):
        self.pyaudio_instance = pyaudio.PyAudio()
        self.open_stream()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open_stream(self):
        if self.pyaudio_instance is None:
            self.pyaudio_instance = pyaudio.PyAudio()

        self.stream = self.pyaudio_instance.open(
            format=self.format_type,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        logger.info(f"Opened audio stream: {self.sample_rate}Hz, {self.channels} channel(s)")

    def capture_audio(self, duration_seconds):
        if self.stream is None or not self.stream.is_active():
            self.open_stream()

        frames = []
        chunks_to_read = int(self.sample_rate * duration_seconds / self.chunk_size)

        logger.info(f"Capturing audio for {duration_seconds} seconds...")
        start_time = time.time()

        for _ in range(chunks_to_read):
            try:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(data)
            except Exception as e:
                logger.error(f"Error capturing audio: {e}")

        elapsed_time = time.time() - start_time
        logger.info(f"Captured audio, actual time: {elapsed_time:.2f}s")

        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
        return audio_data

    def close(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        if self.pyaudio_instance is not None:
            self.pyaudio_instance.terminate()
            self.pyaudio_instance = None

        logger.info("Closed audio stream and released resources")
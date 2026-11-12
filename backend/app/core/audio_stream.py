"""
Audio streaming utilities: chunk framing, resampling, endpointing and barge-in detection.
"""

class AudioStreamHandler:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BitExtractor:
    def __init__(self, bit_extraction_method="lsb", bits_per_sample=4):
        self.method = bit_extraction_method
        self.bits_per_sample = bits_per_sample
        logger.info(
            f"Initializing bit extractor, method: {bit_extraction_method}, bits per sample: {bits_per_sample}")

    def extract_bits(self, audio_samples):
        if self.method == "lsb":
            bits = self._extract_lsb(audio_samples)
        elif self.method == "threshold":
            bits = self._extract_threshold(audio_samples)
        elif self.method == "optimized":
            bits = self.extract_optimized_bits(audio_samples, self.bits_per_sample)
        else:
            raise ValueError(f"Unknown bit extraction method: {self.method}")

        logger.info(f"Extracted {len(bits)} bits from {len(audio_samples)} audio samples")
        return bits

    def _extract_lsb(self, audio_samples):
        # Get LSB (bit 0) from each sample
        return np.bitwise_and(audio_samples, 1).astype(np.uint8)

    def _extract_threshold(self, audio_samples):
        # Extract bits based on sample value relative to zero
        return (audio_samples > 0).astype(np.uint8)

    def extract_optimized_bits(self, audio_samples, bits_per_sample=4):
        # Limit bits_per_sample to a sensible value
        bits_per_sample = max(1, min(4, bits_per_sample))

        # Use vectorized numpy operations for speed
        result = np.zeros(len(audio_samples) * bits_per_sample, dtype=np.uint8)

        # Choose strategy based on number of bits
        if bits_per_sample == 1:
            # Standard LSB extraction
            result = np.bitwise_and(audio_samples, 1).astype(np.uint8)
        else:
            # Extract multiple bits using both LSB and some higher order bits
            # For each bit we want to extract
            for i in range(bits_per_sample):
                if i < 2:  # For two least significant bits
                    bit_pos = i
                else:  # For remaining bits choose those with more noise
                    bit_pos = i + 2  # E.g. bits 4, 5 instead of 2, 3

                bit_mask = 1 << bit_pos
                bit_values = ((audio_samples & bit_mask) > 0).astype(np.uint8)
                result[i::bits_per_sample] = bit_values

        return result
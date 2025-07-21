import numpy as np
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FileOperations:
    @staticmethod
    def save_bits_to_file(bits, filename):
        # Make sure we have a numpy array
        if not isinstance(bits, np.ndarray):
            bits = np.array(bits, dtype=np.uint8)

        # Pad to full bytes
        padding_bits = (8 - len(bits) % 8) % 8
        if padding_bits > 0:
            bits = np.append(bits, np.zeros(padding_bits, dtype=np.uint8))

        # Convert bits to bytes
        byte_count = len(bits) // 8
        bytes_data = bytearray()

        for i in range(byte_count):
            byte_val = 0
            for j in range(8):
                byte_val |= (bits[i * 8 + j] << (7 - j))
            bytes_data.append(byte_val)

        # Save bytes to file
        with open(filename, 'wb') as f:
            f.write(bytes_data)

        logger.info(f"Saved {len(bits)} bits ({byte_count} bytes) to file {filename}")
        return len(bits)

    @staticmethod
    def load_bits_from_file(filename, max_bits=None):
        if not os.path.exists(filename):
            logger.error(f"File {filename} does not exist")
            return np.array([], dtype=np.uint8)

        with open(filename, 'rb') as f:
            data = f.read()

        # Convert bytes to bits
        bits = []
        for byte in data:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)

        # Limit number of bits if max_bits specified
        if max_bits is not None and max_bits < len(bits):
            bits = bits[:max_bits]

        logger.info(f"Loaded {len(bits)} bits from file {filename}")
        return np.array(bits, dtype=np.uint8)
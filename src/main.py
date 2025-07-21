import argparse
import logging
import numpy as np
import time
import os
from audio_capture import AudioCapture
from bit_extraction import BitExtractor
from mibis_xor import MiBiSXOR
from file_operations import FileOperations

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trng.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TrngGenerator:
    def __init__(self, output_file_base, target_bits=13000000, batch_size=1048576, use_dual_mixers=True,
                 bit_extraction_method="lsb", bits_per_sample=1):
        if output_file_base.endswith('.bin'):
            output_file_base = output_file_base[:-4]

        self.output_file_base = output_file_base
        self.raw_audio_file = f"{output_file_base}_raw.bin"
        self.mibis_xor_file = f"{output_file_base}_mibis.bin"
        self.sha3_file = f"{output_file_base}_sha3.bin"

        self.target_bits = target_bits
        self.batch_size = batch_size
        self.use_dual_mixers = use_dual_mixers

        self.audio_capture = AudioCapture(sample_rate=44100, chunk_size=1024)
        self.bit_extractor = BitExtractor(bit_extraction_method=bit_extraction_method,
                                          bits_per_sample=bits_per_sample)
        self.mibis_xor = MiBiSXOR(use_dual_mixers=use_dual_mixers)

        self.total_bits_generated = 0
        self.start_time = None

        logger.info(f"Initializing TRNG generator with output files: "
                    f"{self.raw_audio_file}, {self.mibis_xor_file}, {self.sha3_file}")

    def generate(self):
        logger.info(f"Starting generation of {self.target_bits} random bits")
        self.start_time = time.time()

        for file_path in [self.raw_audio_file, self.mibis_xor_file, self.sha3_file]:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Removed existing file: {file_path}")

        all_raw_bits = np.array([], dtype=np.uint8)
        all_processed_bits = np.array([], dtype=np.uint8)

        with self.audio_capture:
            while self.total_bits_generated < self.target_bits:
                bits_needed = min(self.batch_size, self.target_bits - self.total_bits_generated)

                capture_duration = bits_needed / 44100 * 1.5  # 1.5x more for safety
                audio_data = self.audio_capture.capture_audio(capture_duration)

                new_raw_bits = self.bit_extractor.extract_bits(audio_data)
                all_raw_bits = np.append(all_raw_bits, new_raw_bits)

                new_processed_bits = self.mibis_xor.process_bits(new_raw_bits, max_bits=bits_needed * 2)
                new_processed_bits = new_processed_bits[:bits_needed]
                all_processed_bits = np.append(all_processed_bits, new_processed_bits)

                self.total_bits_generated += len(new_processed_bits)
                
                # Simple progress print
                progress_percent = self.total_bits_generated / self.target_bits * 100
                print(f"Progress: {progress_percent:.1f}% ({self.total_bits_generated}/{self.target_bits} bits)")

        # Save all bits to files
        logger.info(f"Saving {len(all_raw_bits)} raw bits to {self.raw_audio_file}")
        FileOperations.save_bits_to_file(all_raw_bits, self.raw_audio_file)

        logger.info(f"Saving {len(all_processed_bits)} processed bits to {self.mibis_xor_file}")
        FileOperations.save_bits_to_file(all_processed_bits, self.mibis_xor_file)

        # Generate and save SHA3-256 bits
        import hashlib
        sha3_bits = self._generate_and_save_sha3(self.mibis_xor_file, self.sha3_file, self.target_bits)

        total_time = time.time() - self.start_time
        speed = self.total_bits_generated / total_time if total_time > 0 else 0
        
        logger.info(f"Generation completed. Generated {self.total_bits_generated} bits in {total_time:.2f}s ({speed:.2f} bits/s)")
        logger.info(f"1. Raw audio bits: {self.raw_audio_file} ({len(all_raw_bits)} bits)")
        logger.info(f"2. MiBiS&XOR bits: {self.mibis_xor_file} ({len(all_processed_bits)} bits)")
        logger.info(f"3. SHA3-256 bits: {self.sha3_file} ({len(sha3_bits)} bits)")

        return all_raw_bits, all_processed_bits, sha3_bits

    def _generate_and_save_sha3(self, input_file, output_file, target_bits):
        logger.info(f"Generating SHA3 bit stream ({target_bits} bits) from {input_file}")

        with open(input_file, 'rb') as f:
            data = f.read()

        num_hashes_needed = (target_bits + 255) // 256
        all_sha3_bits = []
        
        chunk_size = len(data) // min(num_hashes_needed, 1000)
        chunk_size = max(chunk_size, 64)  # Minimum chunk size is 64 bytes

        # Generate hashes for file fragments
        for i in range(min(num_hashes_needed, len(data) // chunk_size)):
            chunk = data[i * chunk_size:(i + 1) * chunk_size]
            salted_chunk = chunk + i.to_bytes(4, byteorder='big')

            sha3_hash = hashlib.sha3_256(salted_chunk).digest()

            for byte in sha3_hash:
                for j in range(7, -1, -1):
                    all_sha3_bits.append((byte >> j) & 1)

        # If more hashes needed, generate them based on entire file + counter
        remaining_hashes = num_hashes_needed - min(num_hashes_needed, len(data) // chunk_size)
        if remaining_hashes > 0:
            logger.info(f"Generating additional {remaining_hashes} SHA3-256 hashes")

            for i in range(remaining_hashes):
                offset = len(data) // chunk_size + i
                salted_data = data + offset.to_bytes(4, byteorder='big')

                sha3_hash = hashlib.sha3_256(salted_data).digest()

                for byte in sha3_hash:
                    for j in range(7, -1, -1):
                        all_sha3_bits.append((byte >> j) & 1)

        sha3_bits_array = np.array(all_sha3_bits, dtype=np.uint8)
        sha3_bits_array = sha3_bits_array[:target_bits]

        FileOperations.save_bits_to_file(sha3_bits_array, output_file)
        logger.info(f"Saved {len(sha3_bits_array)} SHA3 bits to {output_file}")

        return sha3_bits_array

def parse_arguments():
    parser = argparse.ArgumentParser(description="True Random Number Generator using MiBiS&XOR method.")

    parser.add_argument("-o", "--output", default="random_bits", help="Base name for output files (without extension)")
    parser.add_argument("-n", "--bits", type=int, default=13000000, help="Number of bits to generate")
    parser.add_argument("-b", "--batch", type=int, default=1048576, help="Size of single batch of bits")
    parser.add_argument("-s", "--single-mixer", action="store_true", help="Use single mixer instead of two")
    parser.add_argument("-e", "--extraction", default="optimized", choices=["lsb", "optimized", "threshold"],
                        help="Bit extraction method")
    parser.add_argument("-bs", "--bits-per-sample", type=int, default=4,
                        help="Number of bits to extract from each sample (for 'optimized' method)")

    return parser.parse_args()

def main():
    args = parse_arguments()

    try:
        generator = TrngGenerator(
            output_file_base=args.output,
            target_bits=args.bits,
            batch_size=args.batch,
            use_dual_mixers=not args.single_mixer,
            bit_extraction_method=args.extraction,
            bits_per_sample=args.bits_per_sample
        )

        raw_bits, mibis_bits, sha3_bits = generator.generate()

        logger.info(f"Generator completed successfully.")
        logger.info(f"1. Raw audio bits saved to {generator.raw_audio_file}")
        logger.info(f"2. MiBiS&XOR processed bits saved to {generator.mibis_xor_file}")
        logger.info(f"3. SHA3-256 bits saved to {generator.sha3_file}")

    except KeyboardInterrupt:
        logger.info("Generator interrupted by user")
    except Exception as e:
        logger.error(f"Error during generation: {e}", exc_info=True)

if __name__ == "__main__":
    main()
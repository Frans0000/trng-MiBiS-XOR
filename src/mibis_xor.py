import numpy as np
import math
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MiBiSXOR:
    def __init__(self, use_dual_mixers=True):
        self.use_dual_mixers = use_dual_mixers
        logger.info(f"Initializing MiBiSXOR, mode: {'dual mixers' if use_dual_mixers else 'single mixer'}")
    
    def process_bits(self, input_bits, max_bits=None):
        if max_bits is not None and max_bits < len(input_bits):
            input_bits = input_bits[:max_bits]
        
        if self.use_dual_mixers:
            return self._process_with_dual_mixers(input_bits)
        else:
            return self._process_with_single_mixer(input_bits)
    
    def _process_with_single_mixer(self, input_bits):
        logger.info("Processing with single mixer")
        start_time = time.time()
        
        # Calculate number of mixing steps
        num_bits = len(input_bits)
        steps = self._calculate_mixing_steps(num_bits)
        
        # Perform bit mixing
        mixed_bits = self._mix_bits(input_bits, steps)
        
        # XOR adjacent bits
        output_bits = self._xor_adjacent_bits(mixed_bits)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Processed {len(input_bits)} bits to {len(output_bits)} random bits in {elapsed_time:.3f}s")
        
        return np.array(output_bits, dtype=np.uint8)
    
    def _process_with_dual_mixers(self, input_bits):
        logger.info("Processing with dual mixers")
        start_time = time.time()
        
        # Split bits in two parts for two mixers
        midpoint = len(input_bits) // 2
        bits1 = input_bits[:midpoint]
        bits2 = input_bits[midpoint:]
        
        # Calculate mixing steps for each part
        steps1 = self._calculate_mixing_steps(len(bits1))
        steps2 = self._calculate_mixing_steps(len(bits2))
        
        # Perform mixing in parallel
        mixed1 = self._mix_bits(bits1, steps1)
        mixed2 = self._mix_bits(bits2, steps2)
        
        # XOR adjacent bits for both parts
        output1 = self._xor_adjacent_bits(mixed1)
        output2 = self._xor_adjacent_bits(mixed2)
        
        # Combine results
        output_bits = output1 + output2
        
        elapsed_time = time.time() - start_time
        logger.info(f"Processed {len(input_bits)} bits to {len(output_bits)} random bits in {elapsed_time:.3f}s")
        
        return np.array(output_bits, dtype=np.uint8)
    
    def _calculate_mixing_steps(self, num_bits):
        """
        Calculate optimal number of mixing steps for given number of bits.
        
        According to the formula from the article: n = log2(yn - 1) + 1, where yn is the number of bits
        """
        if num_bits <= 1:
            return 1
        return math.floor(math.log2(num_bits - 1) + 1)

    def _mix_bits(self, input_bits, steps):
        """
        Mix bits according to the MiBiS algorithm from the article.
        """
        # Calculate buffer size
        buffer_size = 2 ** (steps - 1) + 1

        # Initialize buffer
        mixed_buffer = [0] * buffer_size

        # Special cases for small number of steps
        if steps == 1:
            if len(input_bits) > 0:
                mixed_buffer[0] = input_bits[0]
            if len(input_bits) > 1:
                mixed_buffer[1] = input_bits[1]
            return mixed_buffer

        # First insert two bits at beginning and end of buffer
        if len(input_bits) > 0:
            mixed_buffer[0] = input_bits[0]
        if len(input_bits) > 1:
            mixed_buffer[-1] = input_bits[1]

        # Index of next bit to insert
        input_idx = 2

        # Array of positions that are already occupied by bits
        # Initially only position 0 and last position
        occupied_positions = [0, buffer_size - 1]

        # For each next step
        for step in range(2, steps + 1):
            # New array of positions that will be occupied in this step
            new_positions = []

            # For each pair of adjacent occupied positions
            for i in range(len(occupied_positions) - 1):
                left_pos = occupied_positions[i]
                right_pos = occupied_positions[i + 1]

                # Find middle position between them
                middle_pos = (left_pos + right_pos) // 2

                # If we still have bits to insert and position is not occupied
                if input_idx < len(input_bits) and mixed_buffer[middle_pos] == 0:
                    mixed_buffer[middle_pos] = input_bits[input_idx]
                    input_idx += 1
                    new_positions.append(middle_pos)

            # Add new occupied positions to list and sort
            occupied_positions.extend(new_positions)
            occupied_positions.sort()

            # If we inserted all bits, stop
            if input_idx >= len(input_bits):
                break

        return mixed_buffer
    
    def _xor_adjacent_bits(self, mixed_bits):
        """
        XOR adjacent bits.
        """
        result = []
        
        # XOR adjacent bits
        for i in range(0, len(mixed_bits) - 1, 2):
            result.append(mixed_bits[i] ^ mixed_bits[i+1])
        
        return result
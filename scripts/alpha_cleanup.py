"""Optional cleanup of low-confidence reflections near a video's floor.

Use the original segmentation confidence, before opaque-interior repair. That
repair intentionally fills light-coloured fur, but can also promote reflections
under paws to opaque foreground. Keep this correction restricted to the reviewed
floor band; applying it to an entire image would erode real translucent fur.
"""
import numpy as np


def suppress_ground_reflections(alpha, original_matte, band, confidence=(195, 245)):
    start, end = band
    low, high = confidence
    if alpha.shape != original_matte.shape or alpha.ndim != 2:
        raise ValueError("Alpha and original matte must have matching 2D shapes")
    if not 0 <= start < end < alpha.shape[0]:
        raise ValueError("Ground band must be within the source image height")
    if not 0 <= low < high <= 255:
        raise ValueError("Confidence must increase within 0..255")
    strength = np.clip((original_matte.astype(np.float32) - low) / (high - low), 0, 1)
    strength = strength * strength * (3 - 2 * strength)
    # Fade the correction in vertically so a moving tail or body does not
    # encounter a hard horizontal crop. High-confidence foreground is untouched.
    blend = np.clip((np.arange(alpha.shape[0])[:, None] - start) / (end - start), 0, 1)
    cap = np.rint(255 * (1 - blend + blend * strength))
    return np.minimum(alpha, cap).astype(np.uint8)

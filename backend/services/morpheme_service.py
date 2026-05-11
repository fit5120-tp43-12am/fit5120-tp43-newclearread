"""
Morpheme Segmenter Service - initialization and wrapper for FastAPI integration.

This module provides a singleton MorphemeSegmenter instance that can be imported
and used by FastAPI routes or other backend services.
"""

from pathlib import Path
from .morpheme_analyzer import MorphemeSegmenter

# Initialize the segmenter once at module load time
# The MorphemeSegmenter class handles loading the ONNX model and vocabulary
_segmenter: MorphemeSegmenter | None = None


def get_segmenter(
    onnx_path: str | Path | None = None,
    vocab_path: str | Path | None = None,
    threshold: float = 0.5,
) -> MorphemeSegmenter:
    """
    Get or initialize the global MorphemeSegmenter instance.
    
    Args:
        onnx_path: Path to ONNX model (uses default if None)
        vocab_path: Path to vocabulary JSON (uses default if None)
        threshold: Boundary probability threshold (default 0.5)
    
    Returns:
        MorphemeSegmenter instance (singleton-like behavior on first call)
    """
    global _segmenter
    
    if _segmenter is None:
        if onnx_path is None and vocab_path is None:
            # Use defaults from MorphemeSegmenter
            _segmenter = MorphemeSegmenter(threshold=threshold)
        else:
            _segmenter = MorphemeSegmenter(
                onnx_path=onnx_path,
                vocab_path=vocab_path,
                threshold=threshold,
            )
    
    return _segmenter


def analyze_word(word: str) -> dict:
    """
    Analyze a word and return morpheme segmentation result.
    
    Args:
        word: The word to analyze
    
    Returns:
        Dictionary with morpheme analysis result
    """
    segmenter = get_segmenter()
    return segmenter.analyze(word)

"""
N-gram extraction from tokenized post content.
Produces unigrams and bigrams that serve as candidate topic signals.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable


def extract_ngrams(tokens: list[str], max_n: int = 2) -> list[str]:
    """Extract unigrams and bigrams from a token list."""
    ngrams = list(tokens)  # unigrams
    if max_n >= 2 and len(tokens) >= 2:
        ngrams += [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]
    return ngrams


def aggregate_ngrams(
    ngram_lists: Iterable[list[str]],
) -> Counter:
    """Count total occurrences across all posts."""
    counter: Counter = Counter()
    for ngrams in ngram_lists:
        counter.update(ngrams)
    return counter

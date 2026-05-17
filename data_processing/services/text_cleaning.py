"""
Text cleaning utilities for preprocessing post content before n-gram extraction.
"""

import re

# Common stopwords that add no signal for trend detection
STOPWORDS = frozenset([
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "just", "because", "but", "and", "or", "if", "while", "about", "up",
    "that", "this", "these", "those", "it", "its", "he", "she", "they",
    "them", "his", "her", "their", "we", "our", "you", "your", "i", "me",
    "my", "who", "which", "what", "also", "still", "already", "yet",
    "said", "according", "new", "one", "two", "first", "last", "many",
    "much", "even", "now", "well", "way", "day", "part", "made", "time",
    "like", "back", "going", "get", "got", "come", "came", "make",
    "take", "took", "give", "gave", "say", "tell", "told",
])

# Patterns indicating Home Front Command alert posts (location lists, not content)
ALERT_PATTERNS = [
    re.compile(r"alert from the home front command", re.IGNORECASE),
    re.compile(r"message from the home front command", re.IGNORECASE),
    re.compile(r"red color alert", re.IGNORECASE),
    re.compile(r"rocket and missile fire", re.IGNORECASE),
]

# Regex to strip URLs and URL-like fragments
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+|t\.me/\S+")

# Regex to strip non-alphanumeric (keep spaces)
NON_ALPHA_PATTERN = re.compile(r"[^a-z0-9\s]")

# Minimum token length worth keeping
MIN_TOKEN_LENGTH = 3


def is_alert_post(text: str) -> bool:
    """Detect Home Front Command alert posts — these are location lists, not topical content."""
    return any(p.search(text) for p in ALERT_PATTERNS)


def clean_text(text: str) -> str:
    """Lowercase, strip URLs, remove punctuation, collapse whitespace."""
    text = text.lower()
    text = URL_PATTERN.sub("", text)
    text = NON_ALPHA_PATTERN.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Tokens that look like hashes, IDs, or encoded strings (>12 chars, no vowels, or hex-like)
JUNK_TOKEN_PATTERN = re.compile(r"^[a-z0-9]{15,}$|^[bcdfghjklmnpqrstvwxz0-9]{8,}$")

# Boilerplate n-grams from UI/navigation text embedded in shared posts
BOILERPLATE_NGRAMS = frozenset([
    "reading computer", "reading mobile", "easy reading", "computer easy",
    "mobile device", "continue reading", "click here", "read more",
    "share whatsapp", "share facebook", "share twitter", "share telegram",
    "updates share", "hamoked whatsapp", "device easy", "n12chat",
    "instagram tiktok", "device computer", "easy device",
])

# Single tokens that are UI boilerplate, not real topic signal.
# Social-platform names included here because they overwhelmingly appear in
# footer / "follow us on X" text rather than as topical content.
BOILERPLATE_TOKENS = frozenset([
    "computer", "mobile", "device", "reading", "easy", "n12chat",
    "click", "subscribe", "join", "share", "updates", "follow",
    "channel", "group", "link", "telegram",
    "tiktok", "instagram", "facebook", "youtube", "twitter", "whatsapp",
])


def is_junk_token(token: str) -> bool:
    """Reject tokens that look like URL fragments, hashes, or encoded IDs."""
    return bool(JUNK_TOKEN_PATTERN.match(token))


def tokenize(text: str) -> list[str]:
    """Split cleaned text into tokens, removing stopwords, short tokens, and junk."""
    return [
        token for token in text.split()
        if token not in STOPWORDS
        and token not in BOILERPLATE_TOKENS
        and len(token) >= MIN_TOKEN_LENGTH
        and not is_junk_token(token)
    ]


def is_boilerplate_ngram(ngram: str) -> bool:
    """Check if an n-gram is known UI/navigation boilerplate."""
    return ngram in BOILERPLATE_NGRAMS

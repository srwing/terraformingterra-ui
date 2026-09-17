import re
import numpy as np

from collections import Counter

from sentence_transformers import (
    SentenceTransformer
)

STOPWORDS = set([
    "the","and","with","from","that",
    "this","have","were","would","there",
    "their","about","which","because",
    "into","while","where","when"
])

print("Loading embedding model...")

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

print("Embedding model loaded.")

def summarize(text, max_sentences=2):
    sentences = re.split(
        r'(?<=[.!?]) +',
        text
    )
    return " ".join(
        sentences[:max_sentences]
    )

def extract_insight(text):
    sentences = re.split(
        r'(?<=[.!?]) +',
        text
    )

    if not sentences:
        return ""

    best = max(
        sentences,
        key=len
    )
    return best


def extract_tags(text, top_n=8):
    words = re.findall(
        r'\b[a-zA-Z]{4,}\b',
        text.lower()
    )

    words = [
        w for w in words
        if w not in STOPWORDS
    ]

    counts = Counter(words)

    return [
        w for w, _ in counts.most_common(top_n)
    ]

def generate_embedding(text):
    emb = model.encode(text)
    return np.array(emb).tobytes()

def process_post(post):
    text = post["content"]
    summary = summarize(text)
    insight = extract_insight(text)
    tags = extract_tags(text)
    embedding = generate_embedding(
        summary + " " + insight
    )
    return {
        **post,
        "summary": summary,
        "insight": insight,
        "tags": ",".join(tags),
        "embedding": embedding
    }

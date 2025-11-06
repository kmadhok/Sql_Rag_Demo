"""
Join Inference Module

Analyzes two pandas DataFrames to propose joinable column pairs using:
- Name similarity (fuzzy matching)
- Type compatibility
- Value overlap (Jaccard similarity)
- Cardinality analysis (uniqueness)
- Optional semantic similarity (embeddings)
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Optional, Tuple, List, TYPE_CHECKING
from rapidfuzz import fuzz
import warnings

# Optional embedding support
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    SentenceTransformer = None  # type: ignore


def _get_type_group(dtype: np.dtype) -> str:
    """Map pandas dtype to compatibility group."""
    if pd.api.types.is_integer_dtype(dtype):
        return "numeric"
    elif pd.api.types.is_float_dtype(dtype):
        return "numeric"
    elif pd.api.types.is_string_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
        return "string"
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"
    elif pd.api.types.is_bool_dtype(dtype):
        return "bool"
    else:
        return "other"


def _check_type_compatibility(dtype1: np.dtype, dtype2: np.dtype) -> bool:
    """Check if two dtypes are compatible for joining."""
    group1 = _get_type_group(dtype1)
    group2 = _get_type_group(dtype2)
    return group1 == group2 and group1 != "other"


def _compute_name_similarity(col1: str, col2: str, left_name: str, right_name: str) -> Tuple[float, str]:
    """
    Compute name similarity with FK/PK pattern detection.

    Returns:
        (similarity_score, notes)
    """
    # Base similarity using RapidFuzz
    base_sim = fuzz.ratio(col1.lower(), col2.lower()) / 100.0

    notes = []
    boost = 0.0

    # FK pattern detection: left_col ends with _id or _key
    col1_lower = col1.lower()
    col2_lower = col2.lower()

    # Check if left looks like FK and right looks like PK
    if col1_lower.endswith('_id') or col1_lower.endswith('_key'):
        notes.append("left_is_fk_pattern")

        # Check if right is exactly 'id'
        if col2_lower == 'id':
            boost += 0.15
            notes.append("right_is_pk_id")
        # Check if col1 contains table name: {table}_id ↔ id
        elif col1_lower == f"{right_name.lower()}_id":
            boost += 0.2
            notes.append(f"fk_pattern_{right_name}_id")

    # Check reverse: right looks like FK and left looks like PK
    if col2_lower.endswith('_id') or col2_lower.endswith('_key'):
        if col1_lower == 'id':
            boost += 0.15
            notes.append("left_is_pk_id")
        elif col2_lower == f"{left_name.lower()}_id":
            boost += 0.2
            notes.append(f"fk_pattern_{left_name}_id")

    # Check for exact match
    if col1_lower == col2_lower:
        boost += 0.1
        notes.append("exact_name_match")

    final_sim = min(1.0, base_sim + boost)
    notes_str = ",".join(notes) if notes else ""

    return final_sim, notes_str


def _compute_value_jaccard(series1: pd.Series, series2: pd.Series) -> float:
    """
    Compute Jaccard similarity of distinct values between two series.
    Handles string comparison by converting to string type.
    """
    # Drop nulls
    s1_clean = series1.dropna()
    s2_clean = series2.dropna()

    if len(s1_clean) == 0 or len(s2_clean) == 0:
        return 0.0

    # Convert to string for comparison to handle mixed types
    try:
        set1 = set(s1_clean.astype(str).unique())
        set2 = set(s2_clean.astype(str).unique())
    except Exception:
        # If conversion fails, return 0
        return 0.0

    if len(set1) == 0 or len(set2) == 0:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    return intersection / union if union > 0 else 0.0


def _compute_uniqueness(series: pd.Series) -> float:
    """
    Compute uniqueness score: distinct_count / non_null_count.
    Returns value between 0 and 1.
    """
    non_null = series.dropna()
    if len(non_null) == 0:
        return 0.0

    distinct_count = non_null.nunique()
    return distinct_count / len(non_null)


def _compute_embedding_similarity(
    col1: str,
    col2: str,
    values1: pd.Series,
    values2: pd.Series,
    model: Optional[SentenceTransformer] = None
) -> float:
    """
    Compute semantic similarity using embeddings.
    Combines column names + sampled values.
    """
    if model is None:
        return 0.0

    try:
        # Sample up to 50 values from each column
        sample1 = values1.dropna().head(50).astype(str).tolist()
        sample2 = values2.dropna().head(50).astype(str).tolist()

        # Create text representations
        text1 = f"{col1} " + " ".join(sample1[:10])  # Column name + first 10 values
        text2 = f"{col2} " + " ".join(sample2[:10])

        # Compute embeddings
        embeddings = model.encode([text1, text2])

        # Cosine similarity
        from numpy.linalg import norm
        cos_sim = np.dot(embeddings[0], embeddings[1]) / (norm(embeddings[0]) * norm(embeddings[1]))

        return float(cos_sim)
    except Exception as e:
        warnings.warn(f"Embedding computation failed: {e}")
        return 0.0


def find_join_candidates(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    left_name: str = "left",
    right_name: str = "right",
    use_embeddings: bool = False,
    weights: Optional[dict] = None
) -> pd.DataFrame:
    """
    Find joinable column pairs between two DataFrames.

    Args:
        df_left: Left DataFrame (≤100 rows recommended)
        df_right: Right DataFrame (≤100 rows recommended)
        left_name: Name of left table (used for FK pattern detection)
        right_name: Name of right table (used for FK pattern detection)
        use_embeddings: Whether to use semantic embeddings (requires sentence-transformers)
        weights: Optional custom weights dict with keys: name_sim, value_jaccard, uniqueness, embed_sim

    Returns:
        DataFrame with columns:
        - left_col: Column name from left DataFrame
        - right_col: Column name from right DataFrame
        - type_compat: Boolean, are types compatible
        - name_sim: Name similarity score (0-1)
        - value_jaccard: Jaccard similarity of values (0-1)
        - left_uniqueness: Uniqueness of left column (0-1)
        - right_uniqueness: Uniqueness of right column (0-1)
        - embed_sim: Embedding similarity (0-1, or 0 if disabled)
        - confidence: Overall confidence score (0-1)
        - notes: Additional pattern notes
    """
    # Default weights from story
    if weights is None:
        weights = {
            'name_sim': 0.4,
            'value_jaccard': 0.35,
            'uniqueness': 0.15,
            'embed_sim': 0.10
        }

    # Sample DataFrames to ≤100 rows
    df_left_sample = df_left.head(1000).copy()
    df_right_sample = df_right.head(1000).copy()

    # Initialize embedding model if requested
    embedding_model = None
    if use_embeddings:
        if not EMBEDDINGS_AVAILABLE:
            warnings.warn(
                "sentence-transformers not available. Install with: pip install sentence-transformers. "
                "Continuing without embeddings."
            )
        else:
            try:
                embedding_model = SentenceTransformer('nomic-ai/nomic-embed-text-v1.5', trust_remote_code=True)
            except Exception as e:
                warnings.warn(f"Failed to load embedding model: {e}. Continuing without embeddings.")

    # Collect candidates
    candidates = []

    for left_col in df_left_sample.columns:
        for right_col in df_right_sample.columns:
            # Type compatibility gate
            type_compat = _check_type_compatibility(
                df_left_sample[left_col].dtype,
                df_right_sample[right_col].dtype
            )

            if not type_compat:
                continue  # Skip incompatible types

            # Compute name similarity
            name_sim, notes = _compute_name_similarity(left_col, right_col, left_name, right_name)

            # Compute value overlap
            value_jaccard = _compute_value_jaccard(
                df_left_sample[left_col],
                df_right_sample[right_col]
            )

            # Compute uniqueness
            left_uniqueness = _compute_uniqueness(df_left_sample[left_col])
            right_uniqueness = _compute_uniqueness(df_right_sample[right_col])

            # Compute embedding similarity
            embed_sim = 0.0
            if embedding_model is not None:
                embed_sim = _compute_embedding_similarity(
                    left_col, right_col,
                    df_left_sample[left_col],
                    df_right_sample[right_col],
                    embedding_model
                )

            # Compute confidence score
            uniqueness_component = min(left_uniqueness, 1.0) * min(right_uniqueness, 1.0)

            confidence = (
                weights['name_sim'] * name_sim +
                weights['value_jaccard'] * value_jaccard +
                weights['uniqueness'] * uniqueness_component +
                weights['embed_sim'] * embed_sim
            )

            # FK->PK heuristic boost
            if (left_col.lower().endswith('_id') and
                left_uniqueness < 0.5 and
                right_col.lower() == 'id' and
                right_uniqueness > 0.9):
                confidence = min(1.0, confidence + 0.1)
                notes = f"{notes},fk_pk_boost" if notes else "fk_pk_boost"

            candidates.append({
                'left_col': left_col,
                'right_col': right_col,
                'type_compat': type_compat,
                'name_sim': round(name_sim, 4),
                'value_jaccard': round(value_jaccard, 4),
                'left_uniqueness': round(left_uniqueness, 4),
                'right_uniqueness': round(right_uniqueness, 4),
                'embed_sim': round(embed_sim, 4),
                'confidence': round(confidence, 4),
                'notes': notes
            })

    # Create DataFrame and sort by confidence
    results_df = pd.DataFrame(candidates)

    if len(results_df) > 0:
        results_df = results_df.sort_values('confidence', ascending=False).reset_index(drop=True)

    return results_df

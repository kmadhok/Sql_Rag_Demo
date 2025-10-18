# Join Inference Tool

Automatically infer joinable column pairs from two DataFrame samples using NLP + statistical analysis.

## Overview

This tool analyzes two pandas DataFrames and proposes potential join relationships by combining:
- **Name similarity** - Fuzzy matching with FK/PK pattern detection
- **Type compatibility** - Only suggests joins between compatible types
- **Value overlap** - Jaccard similarity on distinct values
- **Cardinality analysis** - Detects FK (low uniqueness) vs PK (high uniqueness) patterns
- **Semantic similarity** - Optional embeddings for deep semantic matching

## Key Focus: Join Keys (Not Shared Attributes)

**Important:** By default, this tool focuses on identifying **join keys** (e.g., `user_id` ↔ `id`), not shared attributes (e.g., `gender` ↔ `gender` or `created_at` ↔ `created_at`).

### What Gets Filtered Out

The tool automatically excludes columns that are unlikely to be join keys:
- **Datetime columns**: `created_at`, `updated_at`, `shipped_at`, etc.
- **Descriptive attributes**: `name`, `description`, `email`, `phone`, `address`
- **Low-cardinality attributes**: `gender`, `status`, `state` (uniqueness < 0.30)
- **Geographic fields**: `latitude`, `longitude`, `city`, `country`

### What Gets Included

Columns that look like join keys:
- Contains key terms: `id`, `key`, `code`, `ref`, `num`, `pk`, `fk`
- High uniqueness: ≥ 0.30 distinct values
- Numeric/string types with appropriate cardinality

### Example: Before vs After

**Before filtering:**
```
1. gender ↔ gender         (confidence: 0.575)
2. created_at ↔ created_at (confidence: 0.548)
3. user_id ↔ id            (confidence: 0.377)
```

**After filtering (default):**
```
1. user_id ↔ id            (confidence: 0.78+)
2. order_id ↔ id           (confidence: 0.70+)
```

### Disabling Filtering

To include all columns (e.g., for exploratory analysis):

**Python API:**
```python
candidates = find_join_candidates(df_left, df_right, filter_non_keys=False)
```

**CLI:**
```bash
python find_join_candidates.py --left-csv orders.csv --right-csv users.csv --include-all-columns
```

## Use Cases

- **Schema discovery** - Automatically find relationships in unfamiliar databases
- **Data integration** - Suggest join keys when merging datasets from different sources
- **SQL query generation** - Help LLMs propose correct join conditions
- **Data quality** - Identify potential referential integrity issues

## Installation

### Core Dependencies
Already included in `rag_app/requirements.txt`:
```bash
pip install pandas rapidfuzz numpy
```

### Optional: Semantic Embeddings
For enhanced semantic similarity:
```bash
pip install sentence-transformers
```

## Quick Start

### Python API

```python
import pandas as pd
from join_infer import find_join_candidates

# Load your DataFrames
df_orders = pd.read_csv('orders.csv')
df_users = pd.read_csv('users.csv')

# Find join candidates
candidates = find_join_candidates(
    df_left=df_orders,
    df_right=df_users,
    left_name='orders',
    right_name='users',
    use_embeddings=False  # Set True for semantic similarity
)

# Display results
print(candidates.head())

# Filter high-confidence joins
strong_joins = candidates[candidates['confidence'] > 0.7]
print(strong_joins[['left_col', 'right_col', 'confidence', 'notes']])
```

### CLI Usage

```bash
# Basic usage
python find_join_candidates.py \
  --left-csv orders.csv \
  --right-csv users.csv \
  --left-name orders \
  --right-name users

# With semantic embeddings
python find_join_candidates.py \
  --left-csv orders.csv \
  --right-csv users.csv \
  --left-name orders \
  --right-name users \
  --use-embeddings

# Custom output location
python find_join_candidates.py \
  --left-csv orders.csv \
  --right-csv users.csv \
  --output my_joins.csv
```

## Output Format

The tool returns a DataFrame with these columns:

| Column | Description | Range |
|--------|-------------|-------|
| `left_col` | Column name from left DataFrame | - |
| `right_col` | Column name from right DataFrame | - |
| `type_compat` | Are data types compatible? | Boolean |
| `name_sim` | Name similarity score | 0.0 - 1.0 |
| `value_jaccard` | Jaccard overlap of distinct values | 0.0 - 1.0 |
| `left_uniqueness` | Uniqueness of left column (distinct/count) | 0.0 - 1.0 |
| `right_uniqueness` | Uniqueness of right column | 0.0 - 1.0 |
| `cardinality_score` | FK→PK pattern score | 0.0 - 1.0 |
| `key_pattern_score` | Key term presence score | 0.0 - 1.0 |
| `embed_sim` | Semantic embedding similarity | 0.0 - 1.0 |
| `confidence` | Overall confidence score | 0.0 - 1.0 |
| `notes` | Pattern detection notes | String |

### Example Output

```
   left_col right_col  name_sim  value_jaccard  cardinality_score  key_pattern_score  left_uniqueness  right_uniqueness  confidence                    notes
0   user_id        id     0.594          0.000              1.000              1.000            0.930             1.000       0.785  left_is_fk_pattern,right_is_pk_id,key_filtered
1  order_id        id     0.550          0.000              0.600              1.000            1.000             1.000       0.713  left_is_fk_pattern,right_is_pk_id,key_filtered
```

## Confidence Scoring

The confidence score is calculated using weighted components optimized for join key detection:

```
confidence = 0.25 × name_similarity
           + 0.25 × value_jaccard
           + 0.30 × cardinality_score     (NEW - highest weight!)
           + 0.15 × key_pattern_score     (NEW)
           + 0.05 × embedding_similarity  (if enabled)
```

### Scoring Components Explained

**1. Cardinality Score (weight: 0.30)**

Detects FK→PK patterns based on uniqueness:
- **1.0**: Perfect FK→PK (left: 0.3-0.95 unique, right: >0.9 unique)
- **0.8**: Good FK→PK (left < right, right ≥ 0.8)
- **0.6**: 1:1 relationship (both ≥ 0.9 unique)
- **0.0**: Low uniqueness attribute (< 0.3) — **penalized heavily**

**2. Key Pattern Score (weight: 0.15)**

Rewards columns with key-related names:
- **1.0**: Both columns have key terms (`user_id` ↔ `id`)
- **0.5**: One column has key terms (`user_id` ↔ `name`)
- **0.0**: No key terms (`description` ↔ `label`)

Key terms: `id`, `key`, `code`, `ref`, `num`, `pk`, `fk`

**3. Name Similarity, Value Jaccard, Embeddings**

Same as before, but with reduced weights to prioritize cardinality and key patterns.

### Custom Weights

Override default weights for your use case:

```python
# Emphasize value overlap over everything else
custom_weights = {
    'name_sim': 0.15,
    'value_jaccard': 0.50,
    'cardinality_score': 0.20,
    'key_pattern_score': 0.10,
    'embed_sim': 0.05
}

candidates = find_join_candidates(
    df_left, df_right,
    weights=custom_weights
)
```

## How It Works

### 1. Type Compatibility Gate

Only columns with compatible types are compared:
- **Numeric** → `int`, `float` (can join with each other)
- **String** → `str`, `object`
- **Datetime** → `datetime64`
- **Boolean** → `bool`

Cross-type joins are blocked (e.g., `int` ↔ `string`).

### 2. Name Similarity

Uses RapidFuzz's `fuzz.ratio()` for fuzzy string matching, enhanced with:
- **FK pattern detection**: Recognizes `*_id`, `*_key` suffixes
- **Table name matching**: Boosts `{table_name}_id` patterns
- **Exact matches**: Extra confidence for identical names

### 3. Value Overlap (Jaccard)

Computes intersection over union of distinct values:
```
Jaccard(A, B) = |A ∩ B| / |A ∪ B|
```

High Jaccard suggests referential integrity (FK values exist in PK).

### 4. Cardinality Analysis

Uniqueness ratio detects primary vs foreign keys:
- **High uniqueness** (→ 1.0) = likely primary key
- **Low uniqueness** (< 0.5) = likely foreign key

### 5. Semantic Embeddings (Optional)

When enabled, uses `sentence-transformers` to:
1. Embed column names + sampled values
2. Compute cosine similarity
3. Capture semantic relationships beyond lexical matching

## Performance

- **Sample size**: Automatically limits to 100 rows per DataFrame
- **Speed**: ~0.1-0.5s without embeddings, ~2-5s with embeddings (first run loads model)
- **Memory**: Minimal, works with millions of rows (via sampling)

## Examples

### Example 1: E-commerce Orders → Users

```python
df_orders = pd.DataFrame({
    'order_id': [1, 2, 3],
    'user_id': [101, 102, 101],  # FK with duplicates
    'amount': [50.0, 75.0, 100.0]
})

df_users = pd.DataFrame({
    'id': [101, 102, 103],  # PK, all unique
    'name': ['Alice', 'Bob', 'Charlie']
})

candidates = find_join_candidates(df_orders, df_users, 'orders', 'users')
# Expected: user_id ↔ id with confidence > 0.7
```

### Example 2: Fuzzy Name Matching

```python
df_customers = pd.DataFrame({
    'customer_id': [1, 2, 3],
    'name': ['A', 'B', 'C']
})

df_accounts = pd.DataFrame({
    'account_customer_id': [1, 2, 3],
    'balance': [100, 200, 300]
})

candidates = find_join_candidates(df_customers, df_accounts, 'customers', 'accounts')
# Expected: customer_id ↔ account_customer_id with moderate confidence
```

### Example 3: No Valid Joins

```python
df_products = pd.DataFrame({
    'product_id': [1, 2, 3],  # Integer
    'name': ['Widget', 'Gadget', 'Gizmo']
})

df_categories = pd.DataFrame({
    'category_id': ['A', 'B', 'C'],  # String - type mismatch!
    'label': ['Electronics', 'Home', 'Garden']
})

candidates = find_join_candidates(df_products, df_categories)
# Expected: No candidates due to type incompatibility
```

## Testing

Run unit tests:
```bash
cd sql_improvement
pytest test_join_infer.py -v
```

Test coverage includes:
- ✓ Perfect matches (`id` ↔ `id`)
- ✓ FK/PK patterns (`user_id` ↔ `id`)
- ✓ Near-matches (`customer_id` ↔ `user_id`)
- ✓ Type gates (blocking incompatible types)
- ✓ Value overlap scenarios
- ✓ Custom weights
- ✓ Edge cases (empty DataFrames, nulls)

## Limitations

1. **Sample-based**: Works on first 100 rows (configurable) - may miss patterns in larger datasets
2. **No multi-column joins**: Only considers single-column joins
3. **No schema metadata**: Doesn't use database constraints (PRIMARY KEY, FOREIGN KEY annotations)
4. **String conversion**: May be slow for very wide DataFrames with many columns

## Future Enhancements

- [ ] Multi-column composite join detection
- [ ] Integration with database schema metadata
- [ ] Confidence calibration based on historical join success
- [ ] Support for approximate joins (fuzzy matching on values)

## Contributing

Suggestions for improvement:
- Adjust default weights based on your domain
- Add domain-specific FK patterns (e.g., `*_code`, `*_ref`)
- Implement cost-based ranking (prefer joins with lower cardinality)

## License

Part of the SQL RAG project.

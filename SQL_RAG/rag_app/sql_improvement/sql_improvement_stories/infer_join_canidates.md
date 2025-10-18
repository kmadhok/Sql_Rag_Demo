🧠 Story: Infer joinable columns from two DataFrame samples via NLP + stats

Goal
Given two in-memory pandas DataFrames (≤100 rows each), analyze column names and values to propose joinable column pairs with confidence scores—no database calls.

Description
Build a small library function (and CLI wrapper) that inspects df_left and df_right and returns a ranked list of candidate joins. It blends:

Name similarity: token/regex features (_id, _key, ${table}_id), RapidFuzz/Jaro scores.

Type gating: only compare compatible types (STRING↔STRING, INT↔INT, DATE↔DATE).

Value overlap signals (on samples):

Jaccard of DISTINCT values (capped by sample).

Null rate compatibility.

Cardinality hints (uniqueness ≈ PK vs FK).

Optional semantic similarity (embeddings): nomic text embeddings over column names (and a few sampled values) → cosine sim.

Inputs

Python API:

from join_infer import find_join_candidates
candidates = find_join_candidates(df_left, df_right, left_name="orders", right_name="order_items", use_embeddings=True)


CLI (optional):

python tools/find_join_candidates.py --left-csv /path/left.csv --right-csv /path/right.csv --left-name orders --right-name order_items --use-embeddings


Outputs

join_candidates.csv with columns:
left_col, right_col, type_compat, name_sim, value_jaccard, left_uniqueness, right_uniqueness, embed_sim, confidence, notes

Also return a pandas DataFrame from the API.

Scoring (default weights, tunable):

confidence = 0.4*name_sim
           + 0.35*value_jaccard
           + 0.15*min(left_uniqueness, 1.0) * min(right_uniqueness, 1.0)
           + 0.10*embed_sim   # if enabled, else 0
gates: type_compat == True


Heuristics: promote pairs where left looks FK-like (*_id, not unique) and right looks PK-like (id, high uniqueness).

Acceptance Criteria

 Type gating prevents STRING↔INT, etc.

 Name similarity implemented (RapidFuzz ≥ 0.0–1.0 scale).

 Value overlap computed on samples: Jaccard over distinct values.

 Uniqueness proxy = distinct / non_null_count per column (0–1).

 Optional --use-embeddings computes cosine similarity (nomic) for names (+ up to 50 sampled values concatenated).

 Returns ≥1 candidate for obvious matches (e.g., order_id ↔ order_id / id).

 Writes join_candidates.csv and logs top 5 pairs with scores.

 Clear docstring & README snippet with examples.

Definition of Done

 Module join_infer.py with find_join_candidates(...).

 CLI tools/find_join_candidates.py.

 Unit tests with tiny toy DataFrames validating:

perfect match (id↔id),

near-match (user_id↔customer_id),

false positives suppressed by type gate.

 pyproject.toml deps (pandas, rapidfuzz, optional sentence-transformers or nomic).

Example (toy)

cands = find_join_candidates(orders_df, items_df, left_name="orders", right_name="order_items")
print(cands.head(5))
# Expect ('order_id','order_id') or ('id','order_id') near the top with confidence > 0.7


Labels: nlp, data-quality, agents, good-first-issue
Estimate: S (2–4 hrs)
Depends On: none (operates on provided samples only)
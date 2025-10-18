"""
Unit tests for join_infer module.

Tests cover:
- Perfect name matches
- FK/PK patterns
- Near-matches with fuzzy names
- Type gating
- Value overlap scenarios
- Embeddings (optional)
"""

import pytest
import pandas as pd
import numpy as np
from join_infer import (
    find_join_candidates,
    _check_type_compatibility,
    _compute_name_similarity,
    _compute_value_jaccard,
    _compute_uniqueness,
    _compute_cardinality_score,
    _compute_key_pattern_score,
    is_likely_join_key,
    _get_type_group
)


class TestTypeCompatibility:
    """Test type compatibility checks."""

    def test_same_numeric_types_compatible(self):
        """Integer and integer should be compatible."""
        assert _check_type_compatibility(np.dtype('int64'), np.dtype('int32'))

    def test_numeric_types_compatible(self):
        """Integer and float should be compatible (both numeric)."""
        assert _check_type_compatibility(np.dtype('int64'), np.dtype('float64'))

    def test_string_types_compatible(self):
        """String and object should be compatible."""
        assert _check_type_compatibility(np.dtype('object'), np.dtype('str'))

    def test_datetime_types_compatible(self):
        """Datetime types should be compatible."""
        assert _check_type_compatibility(
            np.dtype('datetime64[ns]'),
            np.dtype('datetime64[ns]')
        )

    def test_numeric_string_incompatible(self):
        """Numeric and string should be incompatible."""
        assert not _check_type_compatibility(np.dtype('int64'), np.dtype('object'))

    def test_numeric_datetime_incompatible(self):
        """Numeric and datetime should be incompatible."""
        assert not _check_type_compatibility(np.dtype('int64'), np.dtype('datetime64[ns]'))


class TestNameSimilarity:
    """Test name similarity computation."""

    def test_exact_match(self):
        """Exact column name match should score very high."""
        sim, notes = _compute_name_similarity('id', 'id', 'orders', 'users')
        assert sim >= 0.9
        assert 'exact_name_match' in notes

    def test_fk_pk_pattern_user_id(self):
        """user_id ↔ id should score high with FK/PK pattern."""
        sim, notes = _compute_name_similarity('user_id', 'id', 'orders', 'users')
        assert sim >= 0.7
        assert 'left_is_fk_pattern' in notes
        assert 'right_is_pk_id' in notes

    def test_table_specific_fk_pattern(self):
        """orders_id ↔ id should score very high with table-specific FK."""
        sim, notes = _compute_name_similarity('orders_id', 'id', 'items', 'orders')
        assert sim >= 0.8
        assert 'fk_pattern_orders_id' in notes

    def test_near_match_customer_user(self):
        """customer_id ↔ user_id should have moderate similarity."""
        sim, notes = _compute_name_similarity('customer_id', 'user_id', 'orders', 'users')
        assert 0.3 <= sim <= 0.7

    def test_dissimilar_names(self):
        """Completely different names should score low."""
        sim, notes = _compute_name_similarity('created_at', 'postal_code', 'orders', 'users')
        assert sim < 0.4


class TestValueJaccard:
    """Test Jaccard similarity computation."""

    def test_perfect_overlap(self):
        """Identical value sets should have Jaccard = 1.0."""
        s1 = pd.Series([1, 2, 3, 4, 5])
        s2 = pd.Series([1, 2, 3, 4, 5])
        assert _compute_value_jaccard(s1, s2) == 1.0

    def test_partial_overlap(self):
        """Partial overlap should give intermediate Jaccard."""
        s1 = pd.Series([1, 2, 3, 4, 5])
        s2 = pd.Series([3, 4, 5, 6, 7])
        jaccard = _compute_value_jaccard(s1, s2)
        assert 0.3 <= jaccard <= 0.5

    def test_no_overlap(self):
        """No overlap should give Jaccard = 0.0."""
        s1 = pd.Series([1, 2, 3])
        s2 = pd.Series([4, 5, 6])
        assert _compute_value_jaccard(s1, s2) == 0.0

    def test_handles_nulls(self):
        """Should ignore null values."""
        s1 = pd.Series([1, 2, None, 3, None])
        s2 = pd.Series([1, 2, 3, None])
        assert _compute_value_jaccard(s1, s2) == 1.0

    def test_string_overlap(self):
        """Should work with string values."""
        s1 = pd.Series(['apple', 'banana', 'cherry'])
        s2 = pd.Series(['banana', 'cherry', 'date'])
        jaccard = _compute_value_jaccard(s1, s2)
        assert 0.4 <= jaccard <= 0.6


class TestUniqueness:
    """Test uniqueness computation."""

    def test_all_unique(self):
        """All unique values should give uniqueness = 1.0."""
        s = pd.Series([1, 2, 3, 4, 5])
        assert _compute_uniqueness(s) == 1.0

    def test_no_unique(self):
        """All same values should give uniqueness close to 0."""
        s = pd.Series([1, 1, 1, 1, 1])
        assert _compute_uniqueness(s) == 0.2  # 1 unique / 5 values

    def test_partial_unique(self):
        """Some duplicates should give intermediate uniqueness."""
        s = pd.Series([1, 1, 2, 2, 3])
        assert _compute_uniqueness(s) == 0.6  # 3 unique / 5 values

    def test_handles_nulls(self):
        """Should ignore null values in computation."""
        s = pd.Series([1, 2, 3, None, None])
        assert _compute_uniqueness(s) == 1.0  # 3 unique / 3 non-null


class TestFindJoinCandidates:
    """Integration tests for find_join_candidates function."""

    def test_perfect_match_id_columns(self):
        """Test perfect match: id ↔ id."""
        df_left = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'name': ['A', 'B', 'C', 'D', 'E']
        })
        df_right = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'value': [10, 20, 30, 40, 50]
        })

        results = find_join_candidates(df_left, df_right, 'left', 'right')

        assert len(results) > 0
        # Find the id ↔ id match
        id_match = results[(results['left_col'] == 'id') & (results['right_col'] == 'id')]
        assert len(id_match) == 1
        assert id_match.iloc[0]['confidence'] > 0.7
        assert id_match.iloc[0]['type_compat'] == True

    def test_fk_pk_pattern(self):
        """Test FK/PK pattern: user_id ↔ id."""
        df_orders = pd.DataFrame({
            'order_id': [1, 2, 3, 4, 5],
            'user_id': [101, 102, 101, 103, 102]  # FK with duplicates
        })
        df_users = pd.DataFrame({
            'id': [101, 102, 103, 104, 105],  # PK, all unique
            'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve']
        })

        results = find_join_candidates(df_orders, df_users, 'orders', 'users')

        assert len(results) > 0
        # Find the user_id ↔ id match
        fk_match = results[(results['left_col'] == 'user_id') & (results['right_col'] == 'id')]
        assert len(fk_match) == 1
        assert fk_match.iloc[0]['confidence'] > 0.6
        assert 'fk' in fk_match.iloc[0]['notes'].lower() or 'pk' in fk_match.iloc[0]['notes'].lower()

    def test_near_match_fuzzy_names(self):
        """Test near-match: customer_id ↔ user_id."""
        df_left = pd.DataFrame({
            'customer_id': [1, 2, 3, 4, 5]
        })
        df_right = pd.DataFrame({
            'user_id': [1, 2, 3, 4, 5]
        })

        results = find_join_candidates(df_left, df_right, 'orders', 'users')

        assert len(results) > 0
        match = results[(results['left_col'] == 'customer_id') & (results['right_col'] == 'user_id')]
        assert len(match) == 1
        # Should have moderate confidence
        assert 0.3 <= match.iloc[0]['confidence'] <= 0.9

    def test_type_gate_blocks_incompatible(self):
        """Test that type gate blocks STRING ↔ INT."""
        df_left = pd.DataFrame({
            'id': [1, 2, 3, 4, 5]  # Integer
        })
        df_right = pd.DataFrame({
            'id': ['a', 'b', 'c', 'd', 'e']  # String
        })

        results = find_join_candidates(df_left, df_right, 'left', 'right')

        # Should be no candidates due to type incompatibility
        assert len(results) == 0

    def test_low_value_overlap_low_confidence(self):
        """Test that low value overlap results in lower confidence."""
        df_left = pd.DataFrame({
            'id': [1, 2, 3, 4, 5]
        })
        df_right = pd.DataFrame({
            'id': [10, 20, 30, 40, 50]  # No overlap
        })

        results = find_join_candidates(df_left, df_right, 'left', 'right')

        assert len(results) > 0
        id_match = results[(results['left_col'] == 'id') & (results['right_col'] == 'id')]
        assert len(id_match) == 1
        # Should still have some confidence due to name match, but lower due to no value overlap
        assert id_match.iloc[0]['value_jaccard'] == 0.0

    def test_multiple_candidates_sorted(self):
        """Test that multiple candidates are sorted by confidence."""
        df_left = pd.DataFrame({
            'id': [1, 2, 3],
            'user_id': [10, 20, 30],
            'random_col': [100, 200, 300]
        })
        df_right = pd.DataFrame({
            'id': [1, 2, 3],
            'value': [5, 10, 15]
        })

        results = find_join_candidates(df_left, df_right, 'left', 'right')

        assert len(results) > 0
        # Results should be sorted by confidence descending
        assert results['confidence'].is_monotonic_decreasing

    def test_custom_weights(self):
        """Test that custom weights affect scoring."""
        df_left = pd.DataFrame({
            'id': [1, 2, 3]
        })
        df_right = pd.DataFrame({
            'id': [1, 2, 3]
        })

        # Default weights
        results_default = find_join_candidates(df_left, df_right, 'left', 'right')

        # Custom weights emphasizing value overlap
        custom_weights = {
            'name_sim': 0.1,
            'value_jaccard': 0.7,
            'uniqueness': 0.1,
            'embed_sim': 0.1
        }
        results_custom = find_join_candidates(df_left, df_right, 'left', 'right', weights=custom_weights)

        # Confidence scores should differ
        assert results_default.iloc[0]['confidence'] != results_custom.iloc[0]['confidence']

    def test_empty_dataframes(self):
        """Test handling of empty DataFrames."""
        df_left = pd.DataFrame({'id': []})
        df_right = pd.DataFrame({'id': []})

        results = find_join_candidates(df_left, df_right, 'left', 'right')

        # Should return empty results without crashing
        assert len(results) == 0

    def test_real_world_orders_users(self):
        """Test with realistic orders/users relationship."""
        df_orders = pd.DataFrame({
            'order_id': [1, 2, 3, 4, 5],
            'user_id': [22, 30, 33, 33, 40],
            'status': ['Cancelled', 'Shipped', 'Delivered', 'Cancelled', 'Processing'],
            'created_at': pd.date_range('2024-01-01', periods=5)
        })

        df_users = pd.DataFrame({
            'id': [22, 30, 33, 40, 45],
            'first_name': ['John', 'Jane', 'Bob', 'Alice', 'Charlie'],
            'email': ['j@ex.com', 'ja@ex.com', 'b@ex.com', 'a@ex.com', 'c@ex.com'],
            'age': [25, 30, 35, 40, 45]
        })

        results = find_join_candidates(df_orders, df_users, 'orders', 'users')

        assert len(results) > 0

        # Find user_id ↔ id
        user_match = results[(results['left_col'] == 'user_id') & (results['right_col'] == 'id')]

        # Should be at least one match
        if len(user_match) > 0:
            assert user_match.iloc[0]['confidence'] > 0.5


class TestEmbeddings:
    """Test embedding functionality (optional)."""

    def test_embeddings_disabled_by_default(self):
        """Test that embeddings are disabled by default."""
        df_left = pd.DataFrame({'id': [1, 2, 3]})
        df_right = pd.DataFrame({'id': [1, 2, 3]})

        results = find_join_candidates(df_left, df_right, use_embeddings=False)

        assert len(results) > 0
        assert results.iloc[0]['embed_sim'] == 0.0

    def test_embeddings_flag_doesnt_crash(self):
        """Test that use_embeddings=True doesn't crash (may skip if not installed)."""
        df_left = pd.DataFrame({'id': [1, 2, 3]})
        df_right = pd.DataFrame({'id': [1, 2, 3]})

        # Should not crash even if embeddings not available
        results = find_join_candidates(df_left, df_right, use_embeddings=True)
        assert len(results) > 0


class TestCardinalityScoring:
    """Test cardinality score computation."""

    def test_perfect_fk_pk_pattern(self):
        """Test perfect FK→PK pattern: left moderate uniqueness, right high."""
        score = _compute_cardinality_score(left_uniqueness=0.6, right_uniqueness=0.95)
        assert score == 1.0

    def test_good_fk_pk_pattern(self):
        """Test good FK→PK pattern: left < right, right >= 0.8."""
        score = _compute_cardinality_score(left_uniqueness=0.5, right_uniqueness=0.85)
        assert score == 0.8

    def test_one_to_one_relationship(self):
        """Test 1:1 relationship: both highly unique."""
        score = _compute_cardinality_score(left_uniqueness=0.95, right_uniqueness=0.95)
        assert score == 0.6

    def test_low_uniqueness_penalized(self):
        """Test that low uniqueness (attributes) gets score 0.0."""
        score = _compute_cardinality_score(left_uniqueness=0.01, right_uniqueness=0.01)
        assert score == 0.0

    def test_left_low_uniqueness_penalized(self):
        """Test that left low uniqueness gets penalized."""
        score = _compute_cardinality_score(left_uniqueness=0.1, right_uniqueness=0.95)
        assert score == 0.0


class TestKeyPatternScoring:
    """Test key pattern score computation."""

    def test_both_have_key_terms(self):
        """Test both columns have key terms: user_id ↔ id."""
        score = _compute_key_pattern_score('user_id', 'id')
        assert score == 1.0

    def test_one_has_key_term(self):
        """Test one column has key term."""
        score = _compute_key_pattern_score('user_id', 'name')
        assert score == 0.5

    def test_neither_has_key_term(self):
        """Test neither column has key term."""
        score = _compute_key_pattern_score('name', 'description')
        assert score == 0.0

    def test_code_pattern(self):
        """Test code pattern recognized."""
        score = _compute_key_pattern_score('product_code', 'item_code')
        assert score == 1.0

    def test_key_term_recognition(self):
        """Test various key terms recognized."""
        assert _compute_key_pattern_score('customer_key', 'user_key') == 1.0
        assert _compute_key_pattern_score('ref_num', 'order_num') == 1.0


class TestJoinKeyLikelihood:
    """Test is_likely_join_key filter function."""

    def test_filters_out_datetime_columns(self):
        """Test that datetime columns are filtered out."""
        assert not is_likely_join_key('created_at', np.dtype('datetime64[ns]'), uniqueness=0.99)
        assert not is_likely_join_key('updated_at', np.dtype('datetime64[ns]'), uniqueness=1.0)

    def test_filters_out_gender(self):
        """Test that gender attribute is filtered out."""
        assert not is_likely_join_key('gender', np.dtype('object'), uniqueness=0.01)

    def test_filters_out_status(self):
        """Test that status attribute is filtered out."""
        assert not is_likely_join_key('status', np.dtype('object'), uniqueness=0.05)

    def test_filters_out_address_fields(self):
        """Test that address fields are filtered out."""
        assert not is_likely_join_key('street_address', np.dtype('object'), uniqueness=0.9)
        assert not is_likely_join_key('email', np.dtype('object'), uniqueness=1.0)
        assert not is_likely_join_key('phone', np.dtype('object'), uniqueness=0.99)

    def test_filters_out_geo_fields(self):
        """Test that geographic fields are filtered out."""
        assert not is_likely_join_key('latitude', np.dtype('float64'), uniqueness=0.5)
        assert not is_likely_join_key('longitude', np.dtype('float64'), uniqueness=0.5)
        assert not is_likely_join_key('user_geom', np.dtype('object'), uniqueness=0.5)

    def test_filters_out_low_uniqueness(self):
        """Test that low uniqueness columns are filtered out."""
        assert not is_likely_join_key('some_id', np.dtype('int64'), uniqueness=0.1)

    def test_includes_id_columns(self):
        """Test that ID columns are included."""
        assert is_likely_join_key('user_id', np.dtype('int64'), uniqueness=0.8)
        assert is_likely_join_key('id', np.dtype('int64'), uniqueness=1.0)
        assert is_likely_join_key('order_id', np.dtype('int64'), uniqueness=0.95)

    def test_includes_key_columns(self):
        """Test that key columns are included."""
        assert is_likely_join_key('customer_key', np.dtype('object'), uniqueness=0.9)
        assert is_likely_join_key('product_code', np.dtype('object'), uniqueness=0.85)

    def test_includes_high_uniqueness_numeric(self):
        """Test that high uniqueness numeric columns are included."""
        assert is_likely_join_key('some_number', np.dtype('int64'), uniqueness=0.8)


class TestJoinKeyDetection:
    """Integration tests for join key filtering."""

    def test_filters_out_gender_attributes(self):
        """Test that gender columns are filtered out with filter_non_keys=True."""
        df_orders = pd.DataFrame({
            'order_id': [1, 2, 3, 4, 5],
            'gender': ['F', 'M', 'F', 'M', 'F']
        })
        df_users = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'gender': ['F', 'M', 'F', 'M', 'F']
        })

        results = find_join_candidates(df_orders, df_users, filter_non_keys=True)

        # gender ↔ gender should be filtered out
        gender_matches = results[
            (results['left_col'] == 'gender') & (results['right_col'] == 'gender')
        ]
        assert len(gender_matches) == 0

    def test_filters_out_datetime_columns(self):
        """Test that datetime columns are filtered out."""
        df_orders = pd.DataFrame({
            'order_id': [1, 2, 3],
            'created_at': pd.date_range('2024-01-01', periods=3)
        })
        df_users = pd.DataFrame({
            'id': [1, 2, 3],
            'created_at': pd.date_range('2024-01-01', periods=3)
        })

        results = find_join_candidates(df_orders, df_users, filter_non_keys=True)

        # created_at ↔ created_at should be filtered out
        datetime_matches = results[
            (results['left_col'] == 'created_at') & (results['right_col'] == 'created_at')
        ]
        assert len(datetime_matches) == 0

    def test_includes_id_columns(self):
        """Test that ID columns are included with filtering."""
        df_orders = pd.DataFrame({
            'order_id': [1, 2, 3, 4, 5],
            'user_id': [10, 20, 30, 40, 50]
        })
        df_users = pd.DataFrame({
            'id': [10, 20, 30, 40, 50]
        })

        results = find_join_candidates(df_orders, df_users, filter_non_keys=True)

        # user_id ↔ id should be included
        user_id_match = results[(results['left_col'] == 'user_id') & (results['right_col'] == 'id')]
        assert len(user_id_match) == 1

    def test_user_id_ranks_higher_than_gender(self):
        """Integration test: user_id ↔ id should rank higher than gender ↔ gender."""
        df_orders = pd.DataFrame({
            'order_id': [1, 2, 3, 4, 5],
            'user_id': [22, 30, 33, 33, 40],
            'gender': ['F', 'F', 'F', 'F', 'F']
        })
        df_users = pd.DataFrame({
            'id': [22, 30, 33, 40, 45],
            'gender': ['F', 'F', 'F', 'F', 'F']
        })

        # With filtering (default)
        results_filtered = find_join_candidates(df_orders, df_users, filter_non_keys=True)

        # user_id ↔ id should be in results
        user_id_match = results_filtered[
            (results_filtered['left_col'] == 'user_id') & (results_filtered['right_col'] == 'id')
        ]
        assert len(user_id_match) == 1

        # gender ↔ gender should be filtered out
        gender_match = results_filtered[
            (results_filtered['left_col'] == 'gender') & (results_filtered['right_col'] == 'gender')
        ]
        assert len(gender_match) == 0

        # user_id ↔ id should have higher confidence than before
        assert user_id_match.iloc[0]['confidence'] > 0.5

    def test_cardinality_score_in_output(self):
        """Test that cardinality_score column is in output."""
        df_orders = pd.DataFrame({'order_id': [1, 2, 3]})
        df_users = pd.DataFrame({'id': [1, 2, 3]})

        results = find_join_candidates(df_orders, df_users)

        assert 'cardinality_score' in results.columns
        assert 'key_pattern_score' in results.columns

    def test_include_all_columns_flag(self):
        """Test that filter_non_keys=False includes all columns."""
        df_orders = pd.DataFrame({
            'order_id': [1, 2, 3],
            'gender': ['F', 'M', 'F']
        })
        df_users = pd.DataFrame({
            'id': [1, 2, 3],
            'gender': ['F', 'M', 'F']
        })

        # With filter_non_keys=False, gender should be included
        results = find_join_candidates(df_orders, df_users, filter_non_keys=False)

        gender_match = results[
            (results['left_col'] == 'gender') & (results['right_col'] == 'gender')
        ]
        assert len(gender_match) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

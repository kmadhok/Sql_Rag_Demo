import ast
import re
import pandas as pd
from collections import defaultdict
import json

def safe_get_value(row, col):
    # Handles missing columns and None values
    return row[col] if col in row and pd.notnull(row[col]) else None

def parse_tables_column(tables_raw):
    # If already a list, return as is
    if isinstance(tables_raw, list):
        return tables_raw
    # If string, try to eval or json.loads
    if isinstance(tables_raw, str):
        try:
            return eval(tables_raw)
        except Exception:
            return []
    return []


def parse_joins_column(joins_raw):
    # First, try to parse as a list
    if isinstance(joins_raw, list):
        return joins_raw
    if isinstance(joins_raw, str):
        try:
            return ast.literal_eval(joins_raw)
        except Exception:
            return []
    return []

def extract_tables_from_condition(condition):
    # Try to parse as a list of dicts
    try:
        cond_list = ast.literal_eval(condition)
        if isinstance(cond_list, list):
            return [(d.get('left_table', 'unknown'), d.get('right_table', 'unknown')) for d in cond_list if isinstance(d, dict)]
    except Exception:
        pass
    # Fallback: regex
    pattern = r"'left_table':\s*'([^']*)'.*?'right_table':\s*'([^']*)'"
    return re.findall(pattern, condition)

def analyze_joins(df: pd.DataFrame) -> dict:
    join_analysis = {
        'relationships': [],
        'table_usage': defaultdict(int),
        'join_patterns': [],
        'join_types': defaultdict(int),
        'total_queries': len(df),
        'queries_with_joins': 0,
        'queries_with_descriptions': 0,
        'queries_with_tables': 0,
        'total_individual_joins': 0,
        'max_joins_per_query': 0,
        'join_count_distribution': defaultdict(int),
        'json_format_count': 0,
        'string_format_count': 0
    }

    for _, row in df.iterrows():
        tables_list = parse_tables_column(safe_get_value(row, 'tables'))
        joins_list = parse_joins_column(safe_get_value(row, 'joins'))

        if joins_list:
            join_analysis['queries_with_joins'] += 1
            join_count = len(joins_list)
            join_analysis['join_count_distribution'][join_count] += 1
            join_analysis['total_individual_joins'] += join_count
            join_analysis['max_joins_per_query'] = max(join_analysis['max_joins_per_query'], join_count)
        else:
            join_analysis['join_count_distribution'][0] += 1

        for table in tables_list:
            if table:
                join_analysis['table_usage'][table] += 1

        for join_info in joins_list:
            # If join_info is not a dict, skip
            if not isinstance(join_info, dict):
                continue

            fmt = join_info.get('format', 'string')
            if fmt == 'json':
                join_analysis['json_format_count'] += 1
            else:
                join_analysis['string_format_count'] += 1

            join_type = join_info.get('join_type', 'JOIN')
            join_analysis['join_types'][join_type] += 1

            transformation = join_info.get('transformation')
            condition = join_info.get('condition', '')

            # Try to extract left/right tables from join_info
            left_table = join_info.get('left_table', None)
            right_table = join_info.get('right_table', None)

            # If not present, try to extract from condition
            if not left_table or not right_table:
                extracted = extract_tables_from_condition(condition)
                if extracted:
                    left_table, right_table = extracted[0]
                else:
                    left_table = left_table or 'unknown'
                    right_table = right_table or 'unknown'

            if left_table and left_table != 'unknown':
                join_analysis['table_usage'][left_table] += 1
            if right_table and right_table != 'unknown':
                join_analysis['table_usage'][right_table] += 1

            relationship = {
                'left_table': left_table,
                'right_table': right_table,
                'condition': condition,
                'join_type': join_type,
                'format': fmt,
                'left_column': join_info.get('left_column', ''),
                'right_column': join_info.get('right_column', ''),
                'transformation': transformation if transformation else ''
            }
            join_analysis['relationships'].append(relationship)

    return join_analysis



filtered_df=pd.read_csv(r"debug_filtered_queries.csv")
join_analysis = analyze_joins(filtered_df)
filtered_df.to_csv("debug_filtered_queries_v1.csv", index=False) 
print("Join Analysis type: ", type(join_analysis))
with open('debug_v2.json', "w") as json_file:
    json.dump(join_analysis, json_file, indent=4) # indent for pretty printing

from google.cloud import bigquery
import pandas as pd

# Target dataset
PROJECT = "bigquery-public-data"
DATASET = "thelook_ecommerce"
DATASET_FQN = f"{PROJECT}.{DATASET}"
CSV_OUT = "data_new/thelook_ecommerce_schema.csv"

client = bigquery.Client(project=PROJECT)

rows = []

# 1) List all tables in the dataset  (list_tables)
# Doc: https://cloud.google.com/bigquery/docs/samples/bigquery-list-tables
tables = client.list_tables(DATASET_FQN)

for t in tables:
    # t is a TableListItem: .project, .dataset_id, .table_id available  (Client docs)
    table_fqn = f"{t.project}.{t.dataset_id}.{t.table_id}"

    # 2) Fetch full table to access schema (get_table -> Table.schema)
    # Doc: https://cloud.google.com/bigquery/docs/samples/bigquery-get-table
    tbl = client.get_table(table_fqn)

    # Each field is a SchemaField(name, field_type, mode, fields=...)  (Table / SchemaField docs)
    # https://cloud.google.com/python/docs/reference/bigquery/latest/google.cloud.bigquery.table.Table
    def walk_fields(prefix, fields):
        for f in fields:
            col_name = f"{prefix}.{f.name}" if prefix else f.name
            # include nested field type with STRUCT/RECORD handling
            dtype = f.field_type
            rows.append({
                "full_table_name": table_fqn,
                "table": t.table_id,
                "column": col_name,
                "column_data_type": dtype,
            })
            # Recurse into RECORD/STRUCT subfields
            if f.field_type.upper() in ("RECORD", "STRUCT") and f.fields:
                walk_fields(col_name, f.fields)

    walk_fields("", tbl.schema)

# 3) Save to CSV with the exact 4 columns requested
df = pd.DataFrame(rows, columns=["full_table_name", "table", "column", "column_data_type"])
df.to_csv(CSV_OUT, index=False)

print(f"✅ Wrote {len(df)} rows to {CSV_OUT}")

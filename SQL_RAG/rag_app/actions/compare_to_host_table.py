import pandas as pd
from google.cloud import bigquery
from pull_personal_query_history import pull_queries_from_personal_history

def compare_to_host_table(bq_client):

    fresh_queries = pull_queries_from_personal_history(bq_client)

    existing_query = """
    SELECT *
    FROM `wmt-de-projects.sbx_kanu.query_host`
    """

    try:
        existing_queries = bq_client.query(existing_query).to_dataframe()
        print(f"Found {len(existing_queries)} existing queries in host table")
        
        # Find new queries that aren't already in existing table
        new_queries = fresh_queries[~fresh_queries['query'].isin(existing_queries['query'])]
        print(f"Found {len(new_queries)} new queries to append")
        
        # If existing table has description column, add empty description for new queries
        if 'description' in existing_queries.columns:
            new_queries = new_queries.copy()
            new_queries['description'] = ''  # or pd.NA if you prefer null values
        
        # Combine existing and new queries, preserving existing structure
        all_queries = pd.concat([existing_queries, new_queries], ignore_index=True)
        
    except Exception as e:
        print(f"No existing table found or error: {e}")
        all_queries = fresh_queries

    print(f"Total queries after merge: {len(all_queries)}")

    return all_queries

if __name__ == "__main__":
    
    bq_client = bigquery.Client(project='wmt-454116e4ab929d9df44a742fc8')

    df=compare_to_host_table(bq_client)
    print(len(df))

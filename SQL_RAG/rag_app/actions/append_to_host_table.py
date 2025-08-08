# Appending necessary queries to host table

import pandas as pd
from google.cloud import bigquery
# from .pull_personal_query_history import pull_queries_from_personal_history
# from .compare_to_host_table import compare_to_host_table
def pull_queries_from_personal_history(bq_client):
    query = """
    SELECT distinct query
    FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_USER`
    WHERE job_type = 'QUERY'
    AND error_result IS NULL
    """

    fresh_queries = bq_client.query(query).to_dataframe()

    return fresh_queries
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
def append_to_host_table(bq_client):

    host_table='wmt-de-projects.sbx_kanu.query_host'

    all_queries = compare_to_host_table(bq_client)

    df=all_queries

    df = df.apply(lambda x: x.astype(str))
    columns=df.columns

    table_schema = [
        bigquery.SchemaField(column, bigquery.enums.SqlTypeNames.STRING)
        for column in columns
    ]
    job_config = bigquery.LoadJobConfig(

        schema=table_schema,

        write_disposition="WRITE_APPEND",
    )
    job = bq_client.load_table_from_dataframe(
        df, host_table, job_config=job_config
    )  # Make an API request.
    job.result() 

    return df

if __name__ == "__main__":
    bq_client = bigquery.Client(project='wmt-de-projects')

    all_queries = append_to_host_table(bq_client)
    
    # host_table='wmt-de-projects.sbx_kanu.query_host'
    # # all_queries = all_queries[:100]
    # print(f"Limited to {len(all_queries)} queries for testing")

    # create_table(host_table, all_queries, bq_client)

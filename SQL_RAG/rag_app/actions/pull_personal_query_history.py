import pandas as pd
from google.cloud import bigquery

bq_client = bigquery.Client(project='wmt-454116e4ab929d9df44a742fc8')

def pull_queries_from_personal_history(bq_client):
    query = """
    SELECT distinct query
    FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_USER`
    WHERE job_type = 'QUERY'
    AND error_result IS NULL
    """

    fresh_queries = bq_client.query(query).to_dataframe()

    return fresh_queries

if __name__ == "__main__":
    fresh_queries = pull_queries_from_personal_history(bq_client)
    print(f"Fetched {len(fresh_queries)} distinct queries")
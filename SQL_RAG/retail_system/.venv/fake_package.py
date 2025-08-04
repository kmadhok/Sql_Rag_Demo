# This is a fake Python file in a virtual environment folder
# This should be ignored by the enhanced file discovery

def fake_sql_query():
    return """
    SELECT * FROM should_be_ignored_table
    WHERE venv_file = true;
    """
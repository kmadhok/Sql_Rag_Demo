import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid2";

function metric(label, value) {
  if (value === undefined || value === null) {
    return null;
  }
  return (
    <Grid size={{ xs: 6 }}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body1">{value}</Typography>
    </Grid>
  );
}

function UsageSummary({ usage }) {
  if (!usage) {
    return null;
  }

  return (
    <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        Pipeline Usage
      </Typography>
      <Grid container spacing={1}>
        {metric("Total tokens", usage.total_tokens?.toLocaleString())}
        {metric("Prompt tokens", usage.prompt_tokens?.toLocaleString())}
        {metric("Completion tokens", usage.completion_tokens?.toLocaleString())}
        {metric("Retrieval time", usage.retrieval_time ? `${usage.retrieval_time.toFixed(2)}s` : undefined)}
        {metric("Generation time", usage.generation_time ? `${usage.generation_time.toFixed(2)}s` : undefined)}
        {metric("Documents retrieved", usage.documents_retrieved)}
        {metric("Search method", usage.search_method)}
        {usage.schema_filtering?.enabled &&
          metric(
            "Schema tables",
            `${usage.schema_filtering.relevant_tables} of ${usage.schema_filtering.total_schema_tables}`
          )}
        {usage.sql_validation?.enabled &&
          metric("Validation level", usage.sql_validation.validation_level)}
      </Grid>
    </Paper>
  );
}

export default UsageSummary;

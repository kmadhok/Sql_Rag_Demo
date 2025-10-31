import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Stack from "@mui/material/Stack";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";

const HIGHLIGHTS = [
  "Retrieves relevant context from a FAISS vector index built from sample Looker queries.",
  "Injects schema snippets and LookML join hints before calling Gemini for SQL generation.",
  "Schema-strict validation checks table and column usage before execution.",
  "Optional BigQuery execution with cost controls (dry run, max bytes billed).",
];

function Introduction() {
  return (
    <Paper variant="outlined" sx={{ p: 3, borderRadius: 3 }}>
      <Stack spacing={2}>
        <Typography variant="h5" component="h2">
          Welcome to the SQL RAG Demo
        </Typography>
        <Typography variant="body1">
          This application demonstrates a retrieval-augmented workflow for SQL question answering using Google Gemini. The FastAPI back end exposes the same pipeline that powered the Streamlit app, while this React interface provides a lightweight chat experience.
        </Typography>

        <Typography variant="h6" component="h3">
          How it works
        </Typography>
        <Typography variant="body1">
          When you submit a question, the service retrieves relevant query examples, injects schema context, and asks Gemini to produce an answer with SQL. The generated SQL is validated, executed on demand, and the response includes usage metrics and source chunks so you can trace the result.
        </Typography>

        <Typography variant="h6" component="h3">
          Highlights
        </Typography>
        <List>
          {HIGHLIGHTS.map((item, idx) => (
            <ListItem key={idx} disableGutters>
              <ListItemIcon sx={{ minWidth: 32 }}>
                <CheckCircleIcon color="primary" fontSize="small" />
              </ListItemIcon>
              <ListItemText primary={item} />
            </ListItem>
          ))}
        </List>

        <Typography variant="body2" color="text.secondary">
          Tip: Open the “Data” tab to see a snapshot of the tables available in the demo dataset. When you are ready, switch to “Chat” to start asking questions.
        </Typography>
      </Stack>
    </Paper>
  );
}

export default Introduction;

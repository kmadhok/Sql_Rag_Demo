import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

function SourcesList({ sources }) {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        Source Chunks
      </Typography>
      {sources.map((source, index) => (
        <Accordion key={`${source.metadata?.index ?? index}-${index}`}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography>
              Chunk {index + 1} &mdash; {source.metadata?.description || "Source"}
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography component="pre" sx={{ whiteSpace: "pre-wrap" }}>
              {source.content}
            </Typography>
            {source.metadata && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                {Object.entries(source.metadata)
                  .filter(([, value]) => value)
                  .map(([key, value]) => `${key}: ${value}`)
                  .join(" • ")}
              </Typography>
            )}
          </AccordionDetails>
        </Accordion>
      ))}
    </Paper>
  );
}

export default SourcesList;

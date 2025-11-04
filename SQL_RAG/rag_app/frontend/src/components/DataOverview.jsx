import { useState, useEffect } from "react";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid2";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import IconButton from "@mui/material/IconButton";

import { getTables, getTableColumns, getTableDescription } from "../services/ragClient";

function DataOverview() {
  const [tables, setTables] = useState([]);
  const [expandedTable, setExpandedTable] = useState(null);
  const [tableColumns, setTableColumns] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const fetchTablesData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Fetch table list
        const tablesResponse = await getTables();

        if (!isMounted) return;

        if (!tablesResponse.success || !tablesResponse.tables) {
          throw new Error('Invalid response format from tables API');
        }

        // Fetch descriptions and columns for each table
        const enrichedTablesPromises = tablesResponse.tables.map(async (tableName) => {
          try {
            // Fetch description and columns in parallel
            const [descResponse, columnsResponse] = await Promise.all([
              getTableDescription(tableName),
              getTableColumns(tableName)
            ]);

            // Get first 5 columns for key columns preview
            const keyColumns = (columnsResponse.columns || [])
              .slice(0, 5)
              .map(col => col.name);

            return {
              name: tableName,
              description: descResponse.description || "No description available",
              keyColumns: keyColumns,
              allColumns: columnsResponse.columns || []
            };
          } catch (err) {
            console.error(`Failed to fetch data for table ${tableName}:`, err);
            // Return table with minimal data if individual fetch fails
            return {
              name: tableName,
              description: "Description unavailable",
              keyColumns: [],
              allColumns: []
            };
          }
        });

        const enrichedTables = await Promise.all(enrichedTablesPromises);

        if (isMounted) {
          setTables(enrichedTables);
        }

      } catch (err) {
        console.error('Failed to fetch tables:', err);

        if (isMounted) {
          setError(`Failed to load schema: ${err.message}`);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchTablesData();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, []);

  const handleToggleTable = (tableName) => {
    setExpandedTable(expandedTable === tableName ? null : tableName);
  };

  if (isLoading) {
    return (
      <Paper variant="outlined" sx={{ p: 3, borderRadius: 3, flexGrow: 1 }}>
        <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" minHeight={400}>
          <CircularProgress />
          <Typography variant="body1" sx={{ mt: 2 }} color="text.secondary">
            Loading schema data...
          </Typography>
        </Box>
      </Paper>
    );
  }

  return (
    <Paper variant="outlined" sx={{ p: 3, borderRadius: 3, flexGrow: 1 }}>
      <Stack spacing={2} sx={{ height: "100%" }}>
        <Typography variant="h5" component="h2">
          Dataset overview
        </Typography>

        <Typography variant="body1">
          The demo uses the public <code>bigquery-public-data.thelook_ecommerce</code> dataset. Below is a quick reference for the primary tables and the columns most frequently used in generated SQL.
        </Typography>

        {error && (
          <Alert severity="warning" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {tables.length === 0 && !error && (
          <Alert severity="info">
            No tables found in the schema.
          </Alert>
        )}

        <Grid container spacing={2} sx={{ flexGrow: 1 }}>
          {tables.map((table) => {
            const isExpanded = expandedTable === table.name;
            const displayColumns = isExpanded ? table.allColumns : table.keyColumns.slice(0, 5);

            return (
              <Grid key={table.name} size={{ xs: 12, sm: 6 }}>
                <Paper
                  variant="outlined"
                  sx={{
                    height: "100%",
                    p: 2,
                    borderRadius: 2,
                    display: "flex",
                    flexDirection: "column",
                    gap: 1,
                    cursor: "pointer",
                    transition: "all 0.2s",
                    "&:hover": {
                      boxShadow: 2,
                      borderColor: "primary.main"
                    }
                  }}
                  onClick={() => handleToggleTable(table.name)}
                >
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="subtitle1" fontWeight={600}>
                      {table.name}
                    </Typography>
                    <IconButton size="small" onClick={(e) => { e.stopPropagation(); handleToggleTable(table.name); }}>
                      {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                    </IconButton>
                  </Box>

                  <Typography variant="body2" color="text.secondary">
                    {table.description}
                  </Typography>

                  <Stack direction="row" spacing={0.5} flexWrap="wrap" sx={{ mt: 1, gap: 0.5 }}>
                    {isExpanded ? (
                      // Show all columns with data types when expanded
                      displayColumns.map((column) => (
                        <Chip
                          key={column.name}
                          label={`${column.name} (${column.type})`}
                          size="small"
                          color={column.name.toLowerCase().includes('id') ? "primary" : "default"}
                          variant={column.name.toLowerCase().includes('id') ? "outlined" : "filled"}
                        />
                      ))
                    ) : (
                      // Show first 5 column names when collapsed
                      table.keyColumns.map((columnName) => (
                        <Chip
                          key={columnName}
                          label={columnName}
                          size="small"
                        />
                      ))
                    )}
                  </Stack>

                  {isExpanded && table.allColumns.length > 0 && (
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                      {table.allColumns.length} columns total
                    </Typography>
                  )}
                </Paper>
              </Grid>
            );
          })}
        </Grid>
      </Stack>
    </Paper>
  );
}

export default DataOverview;

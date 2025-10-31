import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid2";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";

const TABLES = [
  {
    name: "users",
    description: "Customer dimension with demographic attributes and signup timestamp.",
    keyColumns: ["id", "email", "gender", "age", "created_at"],
  },
  {
    name: "orders",
    description: "Order headers capturing purchase timestamp and user linkage.",
    keyColumns: ["order_id", "user_id", "status", "created_at"],
  },
  {
    name: "order_items",
    description: "Line items joined to orders and products, including sale price and cost.",
    keyColumns: ["order_id", "user_id", "product_id", "sale_price", "cost"],
  },
  {
    name: "products",
    description: "Product catalog with brand, category, and distribution center references.",
    keyColumns: ["id", "name", "brand", "category", "distribution_center_id"],
  },
  {
    name: "inventory_items",
    description: "Inventory records providing product cost and distribution center mapping.",
    keyColumns: ["id", "product_id", "cost", "product_distribution_center_id"],
  },
  {
    name: "events",
    description: "User interaction events tied to sessions and products (view, add-to-cart, etc.).",
    keyColumns: ["id", "user_id", "event_type", "product_id", "created_at"],
  },
  {
    name: "distribution_centers",
    description: "Locations used to fulfill orders and stock products.",
    keyColumns: ["id", "name", "latitude", "longitude"],
  },
];

function DataOverview() {
  return (
    <Paper variant="outlined" sx={{ p: 3, borderRadius: 3, flexGrow: 1 }}>
      <Stack spacing={2} sx={{ height: "100%" }}>
        <Typography variant="h5" component="h2">
          Dataset overview
        </Typography>
        <Typography variant="body1">
          The demo uses the public <code>bigquery-public-data.thelook_ecommerce</code> dataset. Below is a quick reference for the primary tables and the columns most frequently used in generated SQL.
        </Typography>

        <Grid container spacing={2} sx={{ flexGrow: 1 }}>
          {TABLES.map((table) => (
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
                }}
              >
                <Typography variant="subtitle1" fontWeight={600}>
                  {table.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {table.description}
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 1 }}>
                  {table.keyColumns.map((column) => (
                    <Chip key={column} label={column} size="small" />
                  ))}
                </Stack>
              </Paper>
            </Grid>
          ))}
        </Grid>
      </Stack>
    </Paper>
  );
}

export default DataOverview;

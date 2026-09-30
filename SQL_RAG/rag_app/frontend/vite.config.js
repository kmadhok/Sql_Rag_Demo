import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Production is served at kanumadhok.com/sql-rag/ (proxied by the portfolio site).
export default defineConfig(({ command }) => ({
  base: command === "build" ? "/sql-rag/" : "/",
  plugins: [react()],
  server: {
    port: 3000,
    open: true,
  },
}));

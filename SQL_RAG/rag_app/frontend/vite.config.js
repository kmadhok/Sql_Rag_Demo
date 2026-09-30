import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Production is served at kanumadhok.com/sql-rag/ (proxied by the portfolio site).
export default defineConfig(({ command }) => ({
  base: command === "build" ? "/sql-rag/" : "/",
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    open: true,
  },
}));

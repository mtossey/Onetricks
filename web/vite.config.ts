import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// base "./" makes the built site work from any folder or static host
export default defineConfig({
  plugins: [react()],
  base: "./",
});

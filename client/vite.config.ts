import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  root: ".",
  publicDir: "static",
  plugins: [react()],
  build: { outDir: "../public", emptyOutDir: true },
  server: { proxy: { "/api": "http://localhost:5001" } },
})

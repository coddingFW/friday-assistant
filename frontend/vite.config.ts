import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Porta fixa 1420 é a convenção do Tauri (devUrl em tauri.conf.json).
// O app é um web app puro: roda no navegador (dev/validação) e dentro do Tauri.
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    host: "127.0.0.1",
  },
});

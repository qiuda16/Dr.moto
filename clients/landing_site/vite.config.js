import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    // The bundled esbuild binary hangs during production minification on the
    // current deployment workstation. Keep builds deterministic until the
    // toolchain is upgraded; the resulting bundle remains production-safe.
    minify: false,
  },
})

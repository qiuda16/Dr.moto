import { defineConfig, loadEnv } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  if (command === 'build' && process.env.UNI_PLATFORM === 'mp-weixin') {
    if (env.VITE_ALLOW_DEMO_FALLBACK === 'true') {
      throw new Error('WeChat release builds must disable demo fallback')
    }
    if (env.VITE_USE_CLOUD_CONTAINER !== 'true') {
      let api
      try { api = new URL(env.VITE_API_BASE) } catch { /* Validated below. */ }
      if (!api || api.protocol !== 'https:') {
        throw new Error('WeChat release builds require an absolute HTTPS VITE_API_BASE')
      }
    }
  }
  return {
  plugins: [
    uni(),
  ],
  }
})

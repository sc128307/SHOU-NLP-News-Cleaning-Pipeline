// electron.vite.config.ts
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()]
  },
  preload: {
    plugins: [externalizeDepsPlugin()]
  },
  renderer: {
    // 🟢 新增部分：配置代理
    server: {
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:3333', // 你的 Express/Python 服务器端口
          changeOrigin: true,
          secure: false
        }
      }
    },
    plugins: [react()]
  }
})

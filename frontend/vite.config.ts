import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 開発時はViteサーバーからバックエンド(localhost:8000)へAPIリクエストをプロキシする
    // (基本設計書3章)。実運用時はFastAPIのStaticFilesがビルド成果物を配信するため、
    // このプロキシ設定は使用されない。
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // npm run build の生成物をバックエンドの静的配信ディレクトリへ直接出力する
    // (詳細設計書4.7.5ステップ3)。
    outDir: '../backend/static',
    emptyOutDir: true,
  },
})

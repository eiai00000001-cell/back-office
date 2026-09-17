import '@testing-library/jest-dom/vitest'

// jsdomはResizeObserverを実装していないため、Rechartsのグラフ描画(SC-12財務ダッシュボード)が
// テスト環境で例外にならないよう、最小限のポリフィルを用意する。
if (typeof window !== 'undefined' && !window.ResizeObserver) {
  class ResizeObserverPolyfill {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  window.ResizeObserver = ResizeObserverPolyfill as unknown as typeof ResizeObserver
}

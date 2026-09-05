export type CathedralNativeMessage = {
  type: string
  payload?: Record<string, unknown>
}

declare global {
  interface Window {
    CathedralBridge?: {
      postMessage(message: string): void
    }
  }
}

export function isPackagedCms(): boolean {
  return window.location.hostname === 'appassets.androidplatform.net'
}

export function postNative(message: CathedralNativeMessage): boolean {
  if (!isPackagedCms() || !window.CathedralBridge) return false
  window.CathedralBridge.postMessage(JSON.stringify(message))
  return true
}

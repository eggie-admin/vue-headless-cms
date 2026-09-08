import $ from 'jquery'

// jQuery UI 1.14 still resolves the global `jQuery` symbol at runtime.
// Publish the module instance first, then load the cockpit dynamically.
;(window as any).jQuery = $
;(window as any).$ = $

const app = document.getElementById('app')

void import('./main').catch((error: unknown) => {
  const message = error instanceof Error ? `${error.name}: ${error.message}` : String(error)
  console.error('KAI9000 cockpit boot failed', error)
  if (app) {
    const safe = message.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c] ?? c))
    app.innerHTML = `<main style="min-height:100vh;padding:24px;background:#030914;color:#f4f7ff;font:16px/1.45 system-ui,sans-serif"><h1 style="margin:0 0 12px;font-size:24px">KAI 9000 BOOT ERROR</h1><p style="margin:0 0 12px;color:#a8b7d8">The packaged cockpit failed before initialization.</p><pre style="white-space:pre-wrap;overflow-wrap:anywhere;padding:12px;border:1px solid #33456c;border-radius:8px;background:#081222">${safe}</pre></main>`
  }
})

import $ from 'jquery'

// jQuery UI's npm modules still execute through their browser-global UMD path
// when bundled by Vite. Publish one jQuery instance first, then load the UI
// dependency graph in deterministic order before the cockpit modules register.
;(window as any).jQuery = $
;(window as any).$ = $

const app = document.getElementById('app')

async function bootCockpit() {
  await import('jquery-ui/ui/version')
  await import('jquery-ui/ui/widget')
  await import('jquery-ui/ui/data')
  await import('jquery-ui/ui/disable-selection')
  await import('jquery-ui/ui/focusable')
  await import('jquery-ui/ui/keycode')
  await import('jquery-ui/ui/plugin')
  await import('jquery-ui/ui/position')
  await import('jquery-ui/ui/scroll-parent')
  await import('jquery-ui/ui/tabbable')
  await import('jquery-ui/ui/unique-id')
  await import('jquery-ui/ui/widgets/mouse')
  await import('jquery-ui/ui/widgets/button')
  await import('jquery-ui/ui/widgets/draggable')
  await import('jquery-ui/ui/widgets/resizable')

  const jq = $ as any
  if (typeof jq.widget !== 'function') throw new TypeError('jQuery UI widget factory failed to initialize')
  if (typeof jq.fn.button !== 'function') throw new TypeError('jQuery UI button failed to initialize')
  if (typeof jq.fn.draggable !== 'function') throw new TypeError('jQuery UI draggable failed to initialize')
  if (typeof jq.fn.resizable !== 'function') throw new TypeError('jQuery UI resizable failed to initialize')

  await import('./main')
}

void bootCockpit().catch((error: unknown) => {
  const message = error instanceof Error ? `${error.name}: ${error.message}` : String(error)
  console.error('KAI9000 cockpit boot failed', error)
  if (app) {
    const safe = message.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c] ?? c))
    app.innerHTML = `<main style="min-height:100vh;padding:24px;background:#030914;color:#f4f7ff;font:16px/1.45 system-ui,sans-serif"><h1 style="margin:0 0 12px;font-size:24px">KAI 9000 BOOT ERROR</h1><p style="margin:0 0 12px;color:#a8b7d8">The packaged cockpit failed before initialization.</p><pre style="white-space:pre-wrap;overflow-wrap:anywhere;padding:12px;border:1px solid #33456c;border-radius:8px;background:#081222">${safe}</pre></main>`
  }
})

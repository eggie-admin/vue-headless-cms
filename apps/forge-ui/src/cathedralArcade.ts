import $ from 'jquery'
import './cathedral-arcade.css'

type ArcadeState = {
  regionId: string
  shards: number
  relics: string[]
  d20: number
  bond: { trust: number; spark: number; respect: number; jealousy: number }
  encounterId: string
  enemyHp: number
  enemyMaxHp: number
  turn: number
  wins: number
}

const STORAGE_KEY = 'luhmos.cathedralArcade.v2'
const LEGACY_STORAGE_KEY = 'luhmos.cathedralArcade.v1'

function clampInt(value: unknown, min: number, max: number, fallback: number): number {
  const n = Number(value)
  return Number.isFinite(n) ? Math.max(min, Math.min(max, Math.trunc(n))) : fallback
}

function sanitizeState(value: unknown): ArcadeState | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const raw = value as Record<string, unknown>
  const bondRaw = raw.bond && typeof raw.bond === 'object' && !Array.isArray(raw.bond)
    ? raw.bond as Record<string, unknown>
    : {}
  return {
    regionId: typeof raw.regionId === 'string' ? raw.regionId.slice(0, 40) : 'glass_coast',
    shards: clampInt(raw.shards, 0, 99999, 120),
    relics: Array.isArray(raw.relics) ? raw.relics.filter((x): x is string => typeof x === 'string').map(x => x.slice(0, 80)).slice(-40) : [],
    d20: clampInt(raw.d20, 0, 20, 0),
    bond: {
      trust: clampInt(bondRaw.trust, 0, 100, 17),
      spark: clampInt(bondRaw.spark, 0, 100, 5),
      respect: clampInt(bondRaw.respect, 0, 100, 18),
      jealousy: clampInt(bondRaw.jealousy, 0, 100, 8),
    },
    encounterId: typeof raw.encounterId === 'string' ? raw.encounterId.slice(0, 40) : '',
    enemyHp: clampInt(raw.enemyHp, 0, 9999, 0),
    enemyMaxHp: clampInt(raw.enemyMaxHp, 0, 9999, 0),
    turn: clampInt(raw.turn, 1, 999, 1),
    wins: clampInt(raw.wins, 0, 99999, 0),
  }
}

function readState(): ArcadeState | null {
  for (const key of [STORAGE_KEY, LEGACY_STORAGE_KEY]) {
    try {
      const raw = localStorage.getItem(key)
      if (!raw) continue
      const clean = sanitizeState(JSON.parse(raw))
      if (clean) return clean
    } catch { /* invalid local save is ignored */ }
  }
  return null
}

/**
 * Mount Cathedral Arcade as an opaque-origin sandbox.
 * Scripts are the only granted browser capability. Same-origin elevation, forms,
 * popups, downloads and top navigation stay absent, so the game cannot read the
 * cockpit DOM, sessionStorage, CMS write token, or native CathedralBridge.
 * Its sole parent capability is the source-locked, schema-limited save adapter.
 */
export function mountCathedralArcade(): void {
  $(() => {
    const tabs = $('#kai-tabs')
    if (!tabs.length || tabs.find('#arcade').length) return

    const nav = tabs.children('.kai-nav')
    nav.children().eq(-1).before('<li><a href="#arcade">⚔<span>Arcade</span></a></li>')
    tabs.children('#settings').before(`
      <section id="arcade" class="kai-page arc-sandbox-page" aria-label="Cathedral Arcade isolated game surface">
        <div class="arc-sandbox-head">
          <div><p class="eyebrow">CATHEDRAL ARCADE // ISOLATED REALM</p><h2>Dungeon process sealed from the Crown bridge</h2></div>
          <span>OPAQUE ORIGIN · SAVE CAPABILITY ONLY</span>
        </div>
        <iframe
          class="arc-sandbox-frame"
          title="LuHm OS Cathedral Arcade"
          src="./arcade/index.html"
          sandbox="allow-scripts"
          referrerpolicy="no-referrer"
          loading="eager"></iframe>
      </section>`)
    ;(tabs as any).tabs('refresh')

    const frame = tabs.find<HTMLIFrameElement>('.arc-sandbox-frame').get(0)
    if (!frame) return

    const onMessage = (event: MessageEvent) => {
      if (event.source !== frame.contentWindow) return
      const message = event.data
      if (!message || typeof message !== 'object' || Array.isArray(message)) return
      const record = message as Record<string, unknown>

      if (record.type === 'arcade.load') {
        frame.contentWindow?.postMessage({ type: 'arcade.state', state: readState() }, '*')
        return
      }

      if (record.type === 'arcade.save') {
        const clean = sanitizeState(record.state)
        if (!clean) return
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(clean)) } catch { /* save is optional */ }
        return
      }

      if (record.type === 'arcade.reset') {
        try {
          localStorage.removeItem(STORAGE_KEY)
          localStorage.removeItem(LEGACY_STORAGE_KEY)
        } catch { /* reset is optional */ }
      }
    }

    window.addEventListener('message', onMessage)
  })
}

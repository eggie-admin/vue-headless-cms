import $ from 'jquery'
import './cathedral-arcade.css'

type Bond = { trust: number; spark: number; respect: number; jealousy: number }
type ArcadeState = {
  regionId: string
  shards: number
  relics: string[]
  d20: number
  bond: Bond
  encounterId: string
  enemyHp: number
  enemyMaxHp: number
  turn: number
  wins: number
}

type Region = { id: string; name: string; hub: string; theme: string }
type Monster = { id: string; name: string; region: string; hp: number; behavior: string; drops: string[]; boss?: boolean }

const STORAGE_KEY = 'luhmos.cathedralArcade.v1'

const REGIONS: Region[] = [
  { id: 'glass_coast', name: 'Glass Coast', hub: 'Brinewake', theme: 'sunlit ruins · salt wind · machine relics' },
  { id: 'blue_steppe', name: 'Blue Steppe', hub: 'Vesper Camp', theme: 'high grass · shrine roads · storm pylons' },
  { id: 'ashen_canals', name: 'Ashen Canals', hub: 'Cinder Parish', theme: 'industrial waterways · black iron bridges · neon chapels' },
  { id: 'starfall_range', name: 'Starfall Range', hub: 'Choir Summit', theme: 'snow temples · observatories · signal towers' },
  { id: 'cathedral_of_static', name: 'Cathedral of Static', hub: 'The Nave', theme: 'blue-white machinery · ritual space · final pilgrimage' },
]

const MONSTERS: Monster[] = [
  { id: 'wire_imp', name: 'Wire Imp', region: 'glass_coast', hp: 34, behavior: 'skirmisher', drops: ['Copper Rune', 'Static Gel'] },
  { id: 'salt_wyrm', name: 'Salt Wyrm', region: 'glass_coast', hp: 42, behavior: 'burrow charge', drops: ['White Scale', 'Brine Core'] },
  { id: 'choir_hound', name: 'Choir Hound', region: 'blue_steppe', hp: 48, behavior: 'pack hunter', drops: ['Tone Shard', 'Servo Bone'] },
  { id: 'canal_revenant', name: 'Canal Revenant', region: 'ashen_canals', hp: 62, behavior: 'drain counter', drops: ['Black Coil', 'Memory Salt'] },
  { id: 'aurora_seraph', name: 'Aurora Seraph', region: 'starfall_range', hp: 82, behavior: 'barrier burst', drops: ['Prism Feather', 'Star Capacitor'] },
  { id: 'static_colossus', name: 'Static Colossus', region: 'cathedral_of_static', hp: 180, behavior: 'phase boss', drops: ['Cathedral Key'], boss: true },
]

const SPELLS = [
  ['LIBRA', 'inspect', 'READ ONLY'],
  ['SCAN', 'audit', 'READ ONLY'],
  ['CURE', 'hotfix', 'SIMULATION'],
  ['CURA', 'patch', 'SIMULATION'],
  ['CURAGA', 'full mutation', 'SIMULATION'],
  ['METEO', 'stage green', 'SIMULATION'],
  ['ULTIMA', 'finale compile', 'APPROVAL LOCK'],
  ['ESUNA', 'harden cleanup', 'SIMULATION'],
  ['PHOENIX', 'rollback', 'APPROVAL LOCK'],
] as const

const RELICS = [
  ['Copper Rune', 42], ['Static Gel', 44], ['Tone Shard', 38], ['Servo Bone', 34],
  ['Black Coil', 28], ['Memory Salt', 24], ['Prism Feather', 18], ['Star Capacitor', 14],
  ['Cathedral Key', 3], ['Infernal Secretary Badge', 7], ['Blue Ward Cassette', 10], ['Brinewake Boot Disk', 12],
] as const

function baseState(): ArcadeState {
  return {
    regionId: 'glass_coast', shards: 120, relics: [], d20: 0,
    bond: { trust: 17, spark: 5, respect: 18, jealousy: 8 },
    encounterId: '', enemyHp: 0, enemyMaxHp: 0, turn: 1, wins: 0,
  }
}

function clamp(value: number, min = 0, max = 100): number { return Math.max(min, Math.min(max, value)) }
function randomInt(max: number): number {
  if (max <= 1) return 0
  const cryptoApi = globalThis.crypto
  if (cryptoApi?.getRandomValues) {
    const values = new Uint32Array(1)
    cryptoApi.getRandomValues(values)
    return values[0] % max
  }
  return Math.floor(Math.random() * max)
}

function loadState(): ArcadeState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return baseState()
    const parsed = JSON.parse(raw) as Partial<ArcadeState>
    return {
      ...baseState(), ...parsed,
      bond: { ...baseState().bond, ...(parsed.bond ?? {}) },
      relics: Array.isArray(parsed.relics) ? parsed.relics.filter(x => typeof x === 'string').slice(-40) : [],
    }
  } catch { return baseState() }
}

function arcadeHtml(): string {
  const regionButtons = REGIONS.map((region, index) => `
    <button class="arc-region ${index === 0 ? 'active' : ''}" type="button" data-region="${region.id}">
      <b>${region.name}</b><small>${region.hub}</small>
    </button>`).join('')
  const spellButtons = SPELLS.map(([name, intent, gate]) => `
    <button class="arc-spell" type="button" data-spell="${name}">
      <strong>${name}</strong><span>${intent}</span><small>${gate}</small>
    </button>`).join('')

  return `
    <section id="arcade" class="kai-page arc-page" aria-label="Cathedral Arcade">
      <div class="arc-hero">
        <div>
          <p class="eyebrow">LUHM OS // EARLY MADNESS REACTOR</p>
          <h2>CATHEDRAL ARCADE</h2>
          <p>JRPG cockpit · spell deck · bond engine · relic pulls · D20 oracle · zero-money local save</p>
        </div>
        <div class="arc-sigil" aria-hidden="true"><i></i><b>✦</b><i></i></div>
      </div>

      <div class="arc-grid arc-grid-top">
        <article class="kai-card arc-world">
          <header><div><p class="eyebrow">PILGRIMAGE MAP</p><h3 class="arc-region-name">Glass Coast</h3></div><span class="arc-hub">BRINEWAKE</span></header>
          <div class="arc-map">
            <div class="arc-orbit arc-orbit-a"></div><div class="arc-orbit arc-orbit-b"></div>
            <div class="arc-beacon">✦</div><div class="arc-map-label">GLASS COAST</div>
          </div>
          <p class="arc-theme">sunlit ruins · salt wind · machine relics</p>
          <div class="arc-region-strip">${regionButtons}</div>
          <button class="kai-btn arc-encounter" type="button">⚔ ROLL ENCOUNTER</button>
        </article>

        <article class="kai-card arc-battle">
          <header><div><p class="eyebrow">ENCOUNTER ENGINE</p><h3 class="arc-enemy-name">Road is quiet</h3></div><span class="arc-turn">TURN 0</span></header>
          <div class="arc-enemy-glyph"><span>☠</span><i></i></div>
          <div class="arc-hp"><span></span></div>
          <p class="arc-enemy-meta">Roll an encounter to wake the dungeon.</p>
          <div class="arc-battle-buttons">
            <button type="button" data-action="attack">ATTACK</button>
            <button type="button" data-action="skill">SKILL</button>
            <button type="button" data-action="guard">GUARD</button>
            <button type="button" data-action="bond">BOND</button>
            <button type="button" data-action="escape">ESCAPE</button>
          </div>
        </article>
      </div>

      <div class="arc-grid arc-grid-mid">
        <article class="kai-card arc-lum-bond">
          <p class="eyebrow">LUM // CAMPFIRE ROUTE</p>
          <h3>Infernal Secretary Bond</h3>
          <div class="arc-bond-row"><span>TRUST</span><meter class="arc-trust" min="0" max="100"></meter><b class="arc-trust-n">0</b></div>
          <div class="arc-bond-row"><span>SPARK</span><meter class="arc-spark" min="0" max="100"></meter><b class="arc-spark-n">0</b></div>
          <div class="arc-bond-row"><span>RESPECT</span><meter class="arc-respect" min="0" max="100"></meter><b class="arc-respect-n">0</b></div>
          <div class="arc-bond-row"><span>JEALOUSY</span><meter class="arc-jealousy" min="0" max="100"></meter><b class="arc-jealousy-n">0</b></div>
          <blockquote class="arc-scene">The camp terminal hums while Lum pretends not to watch you debug by firelight.</blockquote>
          <div class="arc-choice-grid">
            <button type="button" data-choice="review">Ask her to review the patch.</button>
            <button type="button" data-choice="tease">Tell her the bug is afraid of her.</button>
            <button type="button" data-choice="focus">Finish first, then show the result.</button>
          </div>
        </article>

        <article class="kai-card arc-oracle-card">
          <p class="eyebrow">D20 ORACLE</p><h3>Roll Against the Machine Gods</h3>
          <button class="arc-d20" type="button"><span class="arc-d20-value">20</span><small>ROLL</small></button>
          <p class="arc-oracle-text">The die is waiting.</p>
          <div class="arc-mini-stats"><span>VICTORIES <b class="arc-wins">0</b></span><span>STATIC SHARDS <b class="arc-shards">120</b></span></div>
        </article>

        <article class="kai-card arc-relic-card">
          <p class="eyebrow">RELIC GACHA // LOCAL ONLY</p><h3>Cathedral Salvage Pull</h3>
          <div class="arc-relic-slot"><span>◇</span><b class="arc-relic-name">NO RELIC YET</b><small>No money · no purchase · just dungeon nonsense</small></div>
          <button class="kai-btn arc-pull" type="button">✦ PULL RELIC · 10 SHARDS</button>
          <div class="arc-relic-history"></div>
        </article>
      </div>

      <article class="kai-card arc-spellbook">
        <header><div><p class="eyebrow">SPELL LANGUAGE</p><h3>Professor's Grimoire</h3></div><span>ARCADE SIMULATION BOUNDARY</span></header>
        <div class="arc-spells">${spellButtons}</div>
        <p class="arc-spell-result">Spells here are theatrical simulations. They do not mutate GitHub, install APKs, execute shell commands, or cross Secure Folder boundaries.</p>
      </article>

      <article class="kai-card arc-console-card">
        <header><span>✧ CATHEDRAL EVENT LOG</span><button class="arc-reset" type="button">RESET LOCAL SAVE</button></header>
        <div class="arc-event-log" aria-live="polite"></div>
      </article>

      <div class="arc-curtain" aria-hidden="true">
        <div class="arc-stars"></div><div class="arc-rune-ring"></div>
        <p class="arc-curtain-kicker">LUHM OS // CATHEDRAL RITUAL</p>
        <h2 class="arc-curtain-title">ULTIMA</h2>
        <p class="arc-curtain-sub">SIMULATION</p>
      </div>
    </section>`
}

function weightedRelic(): string {
  const total = RELICS.reduce((sum, [, weight]) => sum + weight, 0)
  let roll = randomInt(total)
  for (const [name, weight] of RELICS) {
    if (roll < weight) return name
    roll -= weight
  }
  return RELICS[0][0]
}

function playFanfare(critical = false): void {
  try {
    const AudioCtx = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!AudioCtx) return
    const ctx = new AudioCtx()
    const notes = critical ? [196, 262, 330, 392, 523] : [262, 330, 392, 523]
    const start = ctx.currentTime
    notes.forEach((hz, index) => {
      const osc = ctx.createOscillator(); const gain = ctx.createGain()
      const when = start + index * 0.095
      osc.type = index % 2 ? 'triangle' : 'sine'; osc.frequency.value = hz
      gain.gain.setValueAtTime(0.0001, when); gain.gain.exponentialRampToValueAtTime(0.13, when + 0.018); gain.gain.exponentialRampToValueAtTime(0.0001, when + 0.16)
      osc.connect(gain); gain.connect(ctx.destination); osc.start(when); osc.stop(when + 0.18)
    })
    window.setTimeout(() => void ctx.close(), 900)
  } catch { /* audio is optional */ }
}

export function mountCathedralArcade(): void {
  $(() => {
    const tabs = $('#kai-tabs')
    if (!tabs.length || tabs.find('#arcade').length) return
    const nav = tabs.children('.kai-nav')
    nav.children().eq(-1).before('<li><a href="#arcade">⚔<span>Arcade</span></a></li>')
    tabs.children('#settings').before(arcadeHtml())
    ;(tabs as any).tabs('refresh')

    const page = tabs.find('#arcade')
    let state = loadState()

    const region = () => REGIONS.find(r => r.id === state.regionId) ?? REGIONS[0]
    const enemy = () => MONSTERS.find(m => m.id === state.encounterId)
    const persist = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    const log = (text: string) => {
      const stamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      const line = $('<div class="arc-log-line">').append($('<time>').text(stamp), $('<span>').text(text))
      page.find('.arc-event-log').prepend(line)
      page.find('.arc-event-log .arc-log-line').slice(10).remove()
    }
    const curtain = (title: string, subtitle: string) => {
      const layer = page.find('.arc-curtain')
      layer.find('.arc-curtain-title').text(title); layer.find('.arc-curtain-sub').text(subtitle)
      layer.addClass('live').attr('aria-hidden', 'false')
      window.setTimeout(() => layer.removeClass('live').attr('aria-hidden', 'true'), 1500)
    }

    const render = () => {
      const r = region(); const m = enemy()
      page.find('.arc-region').removeClass('active').filter(`[data-region="${state.regionId}"]`).addClass('active')
      page.find('.arc-region-name').text(r.name); page.find('.arc-hub').text(r.hub.toUpperCase()); page.find('.arc-theme').text(r.theme); page.find('.arc-map-label').text(r.name.toUpperCase())
      page.attr('data-region', r.id)
      page.find('.arc-shards').text(state.shards); page.find('.arc-wins').text(state.wins)
      page.find('.arc-d20-value').text(state.d20 || '20')
      for (const key of ['trust','spark','respect','jealousy'] as const) {
        page.find(`.arc-${key}`).val(state.bond[key]); page.find(`.arc-${key}-n`).text(state.bond[key])
      }
      if (m && state.enemyHp > 0) {
        page.find('.arc-enemy-name').text(m.name); page.find('.arc-turn').text(`TURN ${state.turn}`); page.find('.arc-enemy-meta').text(`${m.behavior.toUpperCase()} · ${state.enemyHp}/${state.enemyMaxHp} HP`)
        page.find('.arc-hp span').css('width', `${Math.max(0, state.enemyHp / state.enemyMaxHp * 100)}%`)
        page.find('.arc-battle').addClass('active-battle')
      } else {
        page.find('.arc-enemy-name').text('Road is quiet'); page.find('.arc-turn').text('TURN 0'); page.find('.arc-enemy-meta').text('Roll an encounter to wake the dungeon.'); page.find('.arc-hp span').css('width','0%'); page.find('.arc-battle').removeClass('active-battle')
      }
      const last = state.relics.at(-1)
      page.find('.arc-relic-name').text(last ?? 'NO RELIC YET')
      page.find('.arc-relic-history').empty().append(state.relics.slice(-4).reverse().map(item => $('<span>').text(item)))
      persist()
    }

    const startEncounter = () => {
      const pool = MONSTERS.filter(m => m.region === state.regionId)
      const m = pool[randomInt(pool.length)]
      state.encounterId = m.id; state.enemyHp = m.hp; state.enemyMaxHp = m.hp; state.turn = 1
      curtain(m.boss ? 'BOSS SIGNAL' : 'ENCOUNTER', m.name.toUpperCase()); log(`${m.name} blocks the pilgrimage road.`); render()
    }

    const winBattle = (m: Monster) => {
      const drop = m.drops[randomInt(m.drops.length)]
      const payout = m.boss ? 55 : 12 + randomInt(12)
      state.shards += payout; state.relics.push(drop); state.wins += 1; state.enemyHp = 0; state.encounterId = ''
      state.bond.respect = clamp(state.bond.respect + (m.boss ? 5 : 1))
      curtain('VICTORY', `+${payout} SHARDS · ${drop.toUpperCase()}`); playFanfare(m.boss); log(`Victory. Salvaged ${drop} and ${payout} Static Shards.`); render()
    }

    page.on('click', '.arc-region', e => {
      state.regionId = String($(e.currentTarget).data('region') ?? 'glass_coast'); state.encounterId = ''; state.enemyHp = 0; state.turn = 1
      log(`Travel route set: ${region().name} / ${region().hub}.`); render()
    })
    page.on('click', '.arc-encounter', startEncounter)
    page.on('click', '.arc-battle-buttons button', e => {
      const m = enemy(); if (!m || state.enemyHp <= 0) { log('No active encounter. Roll one first.'); return }
      const action = String($(e.currentTarget).data('action') ?? '')
      if (action === 'escape') { log(`Withdrew from ${m.name}. The road remembers.`); state.encounterId = ''; state.enemyHp = 0; render(); return }
      if (action === 'guard') { state.turn += 1; state.bond.trust = clamp(state.bond.trust + 1); log('Blue ward raised. Lum approves of surviving long enough to finish the patch.'); render(); return }
      const damage = action === 'skill' ? 15 + randomInt(12) : action === 'bond' ? 10 + Math.floor(state.bond.trust / 5) + randomInt(5) : 8 + randomInt(10)
      state.enemyHp = Math.max(0, state.enemyHp - damage); log(`${action.toUpperCase()} hits ${m.name} for ${damage}.`)
      if (action === 'bond') state.bond.spark = clamp(state.bond.spark + 1)
      if (state.enemyHp <= 0) { winBattle(m); return }
      state.turn += 1; render()
    })
    page.on('click', '.arc-choice-grid button', e => {
      const choice = String($(e.currentTarget).data('choice') ?? '')
      const deltas: Record<string, Bond> = {
        review: { trust: 6, respect: 5, spark: 2, jealousy: 0 },
        tease: { trust: 2, respect: 0, spark: 5, jealousy: 1 },
        focus: { trust: 3, respect: 7, spark: 0, jealousy: 0 },
      }
      const d = deltas[choice]; if (!d) return
      state.bond = { trust: clamp(state.bond.trust + d.trust), spark: clamp(state.bond.spark + d.spark), respect: clamp(state.bond.respect + d.respect), jealousy: clamp(state.bond.jealousy + d.jealousy) }
      const reply = choice === 'review' ? 'Lum: “Fine. Give me the patch before it develops opinions.”' : choice === 'tease' ? 'Lum: “Correct. At least the bug has survival instincts.”' : 'Lum: “Good. Results first. Bragging rights second.”'
      page.find('.arc-scene').text(reply); log(`Camp choice resolved: ${choice}.`); render()
    })
    page.on('click', '.arc-d20', () => {
      state.d20 = randomInt(20) + 1
      const text = state.d20 === 20 ? 'NATURAL 20. The Cathedral notices you. +20 shards.' : state.d20 === 1 ? 'NATURAL 1. A Wire Imp has your password reset form. Probably.' : state.d20 >= 15 ? 'Strong roll. The road bends in your favor.' : state.d20 >= 8 ? 'Adequate. Suspiciously mortal.' : 'Low roll. Lum writes this down for later leverage.'
      if (state.d20 === 20) { state.shards += 20; curtain('NATURAL 20', 'THE CATHEDRAL NOTICES YOU'); playFanfare(true) }
      page.find('.arc-oracle-text').text(text); log(`D20 rolled ${state.d20}. ${text}`); render()
    })
    page.on('click', '.arc-pull', () => {
      if (state.shards < 10) { log('Not enough Static Shards. Beat something ridiculous first.'); return }
      state.shards -= 10; const relic = weightedRelic(); state.relics.push(relic)
      const rare = relic === 'Cathedral Key' || relic === 'Infernal Secretary Badge'
      curtain(rare ? 'RARE RELIC' : 'SALVAGE', relic.toUpperCase()); if (rare) playFanfare(true); log(`Relic pull: ${relic}.`); render()
    })
    page.on('click', '.arc-spell', e => {
      const spell = String($(e.currentTarget).data('spell') ?? '')
      const info = SPELLS.find(([name]) => name === spell); if (!info) return
      let result = `${spell}: ${info[1].toUpperCase()} // ${info[2]}. Arcade simulation only.`
      if (spell === 'ULTIMA') result = 'ULTIMA: FINAL COMPILATION LOCKED. Professor approval is required outside this arcade. Nothing was built, released, or installed.'
      if (spell === 'PHOENIX') result = 'PHOENIX: rollback sigil armed in simulation only. No branch, file, device, or save was changed.'
      if (spell === 'LIBRA') result = `LIBRA: ${region().name}, ${state.wins} victories, ${state.shards} shards, Lum trust ${state.bond.trust}.`
      curtain(spell, result.includes('LOCKED') ? 'PROFESSOR APPROVAL REQUIRED' : 'SIMULATION CAST'); page.find('.arc-spell-result').text(result); log(result)
    })
    page.on('click', '.arc-reset', () => {
      state = baseState(); localStorage.removeItem(STORAGE_KEY); page.find('.arc-event-log').empty(); page.find('.arc-scene').text('The camp terminal hums while Lum pretends not to watch you debug by firelight.'); page.find('.arc-oracle-text').text('The die is waiting.'); log('Local Cathedral Arcade save reset.'); render()
    })

    log('Cathedral Arcade booted from the early LuHm JRPG + magic-system bloodline. No install authority granted.')
    render()
  })
}

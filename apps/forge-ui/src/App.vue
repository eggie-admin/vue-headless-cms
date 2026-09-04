<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { attachLegacyWindowHost } from './lib/jqueryWindowHost'
import { isPackagedCms, postNative } from './lib/cathedralBridge'

const apiState = ref<'connecting' | 'online' | 'offline'>('connecting')
const avatarState = ref('idle')
const cacheState = ref('unknown')
const progress = ref(0)
const cleanupFns: Array<() => void> = []
const packagedCms = isPackagedCms()
const apiBase = packagedCms ? 'http://127.0.0.1:8000' : ''

let socket: WebSocket | null = null
let healthTimer: number | null = null

async function refreshHealth() {
  try {
    const response = await fetch(`${apiBase}/api/health`, { cache: 'no-store' })
    if (!response.ok) throw new Error(String(response.status))
    const data = await response.json()
    apiState.value = 'online'
    cacheState.value = data.cache_state ?? 'unknown'
    if (typeof data.progress === 'number') progress.value = data.progress
    if (typeof data.avatar_state === 'string') avatarState.value = data.avatar_state
  } catch {
    apiState.value = 'offline'
  }
}

function connectEvents() {
  if (packagedCms) {
    healthTimer = window.setInterval(refreshHealth, 1000)
    return
  }

  const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
  socket = new WebSocket(`${scheme}://${location.host}/ws/events`)
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (typeof data.progress === 'number') progress.value = data.progress
    if (typeof data.avatar_state === 'string') avatarState.value = data.avatar_state
    if (typeof data.cache_state === 'string') cacheState.value = data.cache_state
  }
  socket.onclose = () => {
    if (apiState.value === 'online') apiState.value = 'offline'
  }
}

function requestGodotWindow(panel: string) {
  postNative({ type: 'godot.window.open', payload: { panel } })
}

onMounted(async () => {
  document.querySelectorAll<HTMLElement>('[data-legacy-window]').forEach((el) => {
    cleanupFns.push(attachLegacyWindowHost(el, { containment: '#window-cage' }))
  })
  postNative({ type: 'cms.ready', payload: { version: '0.5.0-dev' } })
  await refreshHealth()
  connectEvents()
})

onUnmounted(() => {
  cleanupFns.splice(0).forEach((fn) => fn())
  socket?.close()
  if (healthTimer !== null) window.clearInterval(healthTimer)
})
</script>

<template>
  <main class="cage-shell">
    <section class="avatar-stage" aria-label="Godot avatar stage placeholder">
      <div class="avatar-orbit">
        <div class="avatar-core">LUM</div>
        <span>{{ avatarState }}</span>
      </div>
    </section>

    <section id="window-cage" class="window-cage" aria-label="Video Forge control windows">
      <article class="forge-window jobs-window" data-legacy-window>
        <header data-window-handle>
          <strong>Video Forge</strong>
          <span>API {{ apiState }}</span>
        </header>
        <div class="window-body">
          <p>USB cache: <b>{{ cacheState }}</b></p>
          <label>Render progress</label>
          <progress :value="progress" max="100" />
          <small>{{ progress.toFixed(0) }}%</small>
          <button type="button" @click="requestGodotWindow('renderQueue')">Open Godot render window</button>
        </div>
      </article>

      <article class="forge-window agent-window" data-legacy-window>
        <header data-window-handle>
          <strong>Lum Agent</strong>
          <span>local-first router</span>
        </header>
        <div class="window-body">
          <p>Ollama Lite handles low-risk local commands.</p>
          <p>OpenAI Sol handles complex planning and tool orchestration.</p>
        </div>
      </article>

      <article class="forge-window scene-window" data-legacy-window>
        <header data-window-handle>
          <strong>Cutscene Director</strong>
          <span>Godot 4.7.2</span>
        </header>
        <div class="window-body">
          <p>Scene JSON drives cameras, animation states, dialogue cues and checkpoints.</p>
        </div>
      </article>
    </section>
  </main>
</template>

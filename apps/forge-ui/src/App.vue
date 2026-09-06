<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { isPackagedCms, postNative } from './lib/cathedralBridge'

type Tab = 'chat' | 'agents' | 'gallery' | 'system' | 'cms'
type Target = 'auto' | 'local' | 'openai'
type CmsSummary = { id: string; kind: string; title: string; revision: number; updated_at: string }
type CmsDocument = CmsSummary & { payload: Record<string, unknown>; created_at: string }
type Decision = {
  intent: string
  lane: 'local' | 'cloud'
  tool: string
  arguments: Record<string, unknown>
  risk: 'low' | 'medium' | 'high'
  requires_confirmation: boolean
  rationale: string
}
type ChatEntry = { role: 'user' | 'assistant'; text: string; provider?: string; decision?: Decision }

const packagedCms = isPackagedCms()
const apiBase = packagedCms ? 'http://127.0.0.1:8000' : ''
const tab = ref<Tab>('chat')
const apiState = ref<'connecting' | 'online' | 'offline'>('connecting')
const health = ref<Record<string, unknown>>({})
const providers = ref<Record<string, unknown>>({})
const device = ref<Record<string, unknown>>({})
const gallery = ref<Record<string, unknown> | null>(null)
const kiosk = ref(false)

const target = ref<Target>('auto')
const chatInput = ref('')
const chatBusy = ref(false)
const chat = ref<ChatEntry[]>([
  { role: 'assistant', text: 'Luhm OS cockpit online. KAI 9000 working-title antenna mode. High-impact actions stop at approval.' },
])

const documents = ref<CmsSummary[]>([])
const selected = ref<CmsDocument | null>(null)
const editorText = ref('{}')
const writeToken = ref(sessionStorage.getItem('cathedralCmsToken') ?? '')
const notice = ref('')
const saving = ref(false)
const newId = ref('')
const newTitle = ref('Untitled Document')
const newKind = ref('content')

const selectedLabel = computed(() => selected.value ? `${selected.value.kind} · r${selected.value.revision}` : 'No document selected')
const providerLabel = computed(() => target.value === 'auto' ? 'AUTO ANTENNA' : target.value.toUpperCase())

function headers(write = false): HeadersInit {
  const result: Record<string, string> = { 'Content-Type': 'application/json' }
  if (write && writeToken.value) result['X-Cathedral-Token'] = writeToken.value
  return result
}

async function refreshSystem() {
  try {
    const [healthResponse, providerResponse] = await Promise.all([
      fetch(`${apiBase}/api/health`, { cache: 'no-store' }),
      fetch(`${apiBase}/api/boss/providers`, { cache: 'no-store' }),
    ])
    if (!healthResponse.ok) throw new Error(`health ${healthResponse.status}`)
    health.value = await healthResponse.json()
    providers.value = providerResponse.ok ? await providerResponse.json() : { ok: false, status: providerResponse.status }
    apiState.value = 'online'
  } catch (error) {
    apiState.value = 'offline'
    health.value = { ok: false, error: String(error) }
  }
}

async function sendChat() {
  const message = chatInput.value.trim()
  if (!message || chatBusy.value) return
  chat.value.push({ role: 'user', text: message })
  chatInput.value = ''
  chatBusy.value = true
  try {
    const response = await fetch(`${apiBase}/api/agent/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, target: target.value }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail ?? `chat ${response.status}`)
    const decision = data.decision as Decision
    chat.value.push({
      role: 'assistant',
      provider: String(data.provider ?? 'unknown'),
      decision,
      text: decision.rationale || `${decision.intent} → ${decision.tool}`,
    })
  } catch (error) {
    chat.value.push({ role: 'assistant', text: `Antenna error: ${String(error)}` })
  } finally {
    chatBusy.value = false
  }
}

function approveDecision(entry: ChatEntry) {
  if (!entry.decision) return
  const d = entry.decision
  if (d.tool === 'set_avatar_state') {
    postNative({ type: 'godot.avatar.state', payload: { state: String(d.arguments.state ?? 'idle') } })
    entry.text = `${entry.text}\nApproved bounded avatar-state action.`
    return
  }
  if (d.tool === 'get_system_status') {
    void refreshSystem()
    entry.text = `${entry.text}\nSystem refresh requested.`
    return
  }
  entry.text = `${entry.text}\nNo executor is registered for ${d.tool}; proposal remains non-executing.`
}

function chooseGalleryImage() {
  gallery.value = null
  postNative({ type: 'android.gallery.pick' })
}

function setKiosk(enabled: boolean) {
  kiosk.value = enabled
  postNative({ type: 'android.kiosk.set', payload: { enabled } })
}

function requestDeviceSnapshot() {
  postNative({ type: 'android.device.snapshot' })
}

function rememberToken() {
  sessionStorage.setItem('cathedralCmsToken', writeToken.value)
  notice.value = writeToken.value ? 'Write token stored for this WebView session.' : 'Write token cleared.'
}

async function refreshDocuments(preferId?: string) {
  try {
    const response = await fetch(`${apiBase}/api/cms/documents`, { cache: 'no-store' })
    if (!response.ok) throw new Error(`CMS list ${response.status}`)
    const data = await response.json()
    documents.value = data.documents ?? []
    apiState.value = 'online'
    const nextId = preferId ?? selected.value?.id ?? documents.value[0]?.id
    if (nextId) await loadDocument(nextId)
  } catch (error) {
    apiState.value = 'offline'
    notice.value = String(error)
  }
}

async function loadDocument(id: string) {
  const response = await fetch(`${apiBase}/api/cms/documents/${encodeURIComponent(id)}`, { cache: 'no-store' })
  if (!response.ok) throw new Error(`CMS document ${response.status}`)
  const data = await response.json()
  selected.value = data.document
  editorText.value = JSON.stringify(data.document.payload, null, 2)
  notice.value = ''
}

async function saveDocument() {
  if (!selected.value) return
  saving.value = true
  try {
    const payload = JSON.parse(editorText.value)
    const response = await fetch(`${apiBase}/api/cms/documents/${encodeURIComponent(selected.value.id)}`, {
      method: 'PUT', headers: headers(true),
      body: JSON.stringify({ kind: selected.value.kind, title: selected.value.title, payload, expected_revision: selected.value.revision }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail ?? `save ${response.status}`)
    selected.value = data.document
    editorText.value = JSON.stringify(data.document.payload, null, 2)
    notice.value = `Saved ${data.document.id} revision ${data.document.revision}.`
    postNative({ type: 'cms.document.saved', payload: { id: data.document.id, revision: data.document.revision } })
    await refreshDocuments(data.document.id)
  } catch (error) {
    notice.value = String(error)
  } finally {
    saving.value = false
  }
}

async function createDocument() {
  const id = newId.value.trim().toLowerCase()
  if (!/^[a-z0-9][a-z0-9_.-]{0,79}$/.test(id)) {
    notice.value = 'Document id must use lowercase letters, numbers, dot, dash or underscore.'
    return
  }
  const response = await fetch(`${apiBase}/api/cms/documents/${encodeURIComponent(id)}`, {
    method: 'PUT', headers: headers(true),
    body: JSON.stringify({ kind: newKind.value, title: newTitle.value.trim() || id, payload: {} }),
  })
  const data = await response.json()
  if (!response.ok) { notice.value = data.detail ?? `create ${response.status}`; return }
  newId.value = ''
  notice.value = `Created ${id}.`
  postNative({ type: 'cms.document.saved', payload: { id, revision: 1 } })
  await refreshDocuments(id)
}

async function deleteSelected() {
  if (!selected.value) return
  const id = selected.value.id
  const response = await fetch(`${apiBase}/api/cms/documents/${encodeURIComponent(id)}?revision=${selected.value.revision}`, {
    method: 'DELETE', headers: headers(true),
  })
  const data = await response.json()
  if (!response.ok) { notice.value = data.detail ?? `delete ${response.status}`; return }
  selected.value = null
  editorText.value = '{}'
  notice.value = `Deleted ${id}.`
  postNative({ type: 'cms.document.deleted', payload: { id } })
  await refreshDocuments()
}

function onNativeMessage(event: MessageEvent) {
  let message: any = event.data
  try { if (typeof message === 'string') message = JSON.parse(message) } catch { return }
  if (!message || typeof message !== 'object') return
  if (message.type === 'android.gallery.selected') gallery.value = message.payload ?? null
  if (message.type === 'android.device.snapshot') device.value = message.payload ?? {}
}

onMounted(async () => {
  window.addEventListener('message', onNativeMessage)
  postNative({ type: 'cms.ready', payload: { version: '0.7.0-dev', product: 'Luhm OS', workingTitle: 'KAI 9000', surface: 'fdroid-ai-cockpit' } })
  requestDeviceSnapshot()
  await Promise.all([refreshSystem(), refreshDocuments()])
})
</script>

<template>
  <main class="cockpit-shell">
    <header class="cockpit-topbar">
      <div class="brand-block">
        <strong>LUHM OS · KAI 9000</strong>
        <span class="status" :data-state="apiState">{{ apiState }}</span>
      </div>
      <div class="top-actions">
        <span class="chip">{{ providerLabel }}</span>
        <button type="button" @click="setKiosk(!kiosk)">Kiosk {{ kiosk ? 'ON' : 'OFF' }}</button>
      </div>
    </header>

    <nav class="cockpit-tabs" aria-label="Luhm OS cockpit">
      <button v-for="name in (['chat','agents','gallery','system','cms'] as Tab[])" :key="name" type="button" :class="{ active: tab === name }" @click="tab = name">{{ name }}</button>
    </nav>

    <section v-if="tab === 'chat'" class="pane chat-pane">
      <div class="chat-stream">
        <article v-for="(entry, index) in chat" :key="index" class="chat-bubble" :data-role="entry.role">
          <small>{{ entry.role === 'assistant' ? `LUHM${entry.provider ? ` · ${entry.provider}` : ''}` : 'YOU' }}</small>
          <p>{{ entry.text }}</p>
          <div v-if="entry.decision" class="decision-card" :data-risk="entry.decision.risk">
            <div><strong>{{ entry.decision.intent }}</strong><span>{{ entry.decision.lane }} · {{ entry.decision.tool }}</span></div>
            <code>{{ entry.decision.risk }} risk{{ entry.decision.requires_confirmation ? ' · approval required' : '' }}</code>
            <button type="button" @click="approveDecision(entry)">Approve bounded action</button>
          </div>
        </article>
      </div>
      <form class="chat-compose" @submit.prevent="sendChat">
        <select v-model="target" aria-label="AI provider target">
          <option value="auto">Auto antenna</option>
          <option value="local">Qwen local</option>
          <option value="openai">OpenAI</option>
        </select>
        <textarea v-model="chatInput" rows="2" maxlength="20000" placeholder="Talk to Luhm OS…" @keydown.ctrl.enter.prevent="sendChat" />
        <button type="submit" :disabled="chatBusy || !chatInput.trim()">{{ chatBusy ? 'Thinking…' : 'Send' }}</button>
      </form>
    </section>

    <section v-else-if="tab === 'agents'" class="pane cards-pane">
      <article class="control-card"><strong>Local antenna</strong><span>Qwen 2.5 0.5B · preferred hot model</span><small>Fast routing, UI help, status and bounded automation.</small><button type="button" @click="target = 'local'; tab = 'chat'">Use local</button></article>
      <article class="control-card"><strong>Director</strong><span>Qwen 2.5 3B · optional</span><small>Load only when needed. One model hot at a time on the phone profile.</small></article>
      <article class="control-card"><strong>Cloud antenna</strong><span>OpenAI · optional</span><small>Complex reasoning when explicitly configured. Secrets never belong in the APK.</small><button type="button" @click="target = 'openai'; tab = 'chat'">Use OpenAI</button></article>
      <article class="control-card"><strong>Copilot</strong><span>GitHub developer/build assistant</span><small>Forge-side only. It is not an APK runtime authority.</small></article>
      <article class="control-card wide"><strong>Provider readiness</strong><pre>{{ JSON.stringify(providers, null, 2) }}</pre></article>
    </section>

    <section v-else-if="tab === 'gallery'" class="pane gallery-pane">
      <article class="control-card wide">
        <strong>Edge Gallery</strong>
        <span>Android system Photo Picker</span>
        <small>Luhm OS receives only the item you select. No broad storage permission.</small>
        <button type="button" @click="chooseGalleryImage">Choose image</button>
        <pre v-if="gallery">{{ JSON.stringify(gallery, null, 2) }}</pre>
      </article>
    </section>

    <section v-else-if="tab === 'system'" class="pane cards-pane">
      <article class="control-card"><strong>Runtime</strong><span>{{ apiState }}</span><button type="button" @click="refreshSystem">Refresh</button></article>
      <article class="control-card"><strong>Security</strong><span>Rooted S24 dev lane</span><small>Privileged operations stay behind the typed root broker. AI and WebView receive no generic su or shell authority.</small></article>
      <article class="control-card"><strong>Kiosk shell</strong><span>{{ kiosk ? 'immersive ON' : 'immersive OFF' }}</span><button type="button" @click="setKiosk(!kiosk)">Toggle kiosk</button></article>
      <article class="control-card"><strong>Device</strong><button type="button" @click="requestDeviceSnapshot">Snapshot</button><pre>{{ JSON.stringify(device, null, 2) }}</pre></article>
      <article class="control-card wide"><strong>Luhm OS health</strong><pre>{{ JSON.stringify(health, null, 2) }}</pre></article>
    </section>

    <section v-else class="pane cms-pane">
      <aside class="sidebar">
        <div class="sidebar-title">Documents <button type="button" @click="refreshDocuments()">↻</button></div>
        <button v-for="doc in documents" :key="doc.id" class="doc-card" :class="{ active: selected?.id === doc.id }" type="button" @click="loadDocument(doc.id)">
          <strong>{{ doc.title }}</strong><span>{{ doc.id }}</span><small>{{ doc.kind }} · r{{ doc.revision }}</small>
        </button>
        <div class="create-card">
          <strong>New document</strong><input v-model="newId" placeholder="document-id" /><input v-model="newTitle" placeholder="Title" />
          <select v-model="newKind"><option value="ui_manifest">UI manifest</option><option value="scene_manifest">Scene manifest</option><option value="content">Content</option><option value="character_bible">Character bible</option><option value="visual_bible">Visual bible</option><option value="asset_manifest">Asset manifest</option><option value="cutscene">Cutscene</option></select>
          <button type="button" @click="createDocument">Create</button>
        </div>
      </aside>
      <section class="editor-panel">
        <div class="editor-head">
          <div><input v-if="selected" v-model="selected.title" class="title-input" /><strong v-else>Select a CMS document</strong><small>{{ selectedLabel }}</small></div>
          <div class="editor-actions"><input v-model="writeToken" type="password" autocomplete="off" placeholder="CMS write token" @change="rememberToken" /><button type="button" @click="rememberToken">Arm writes</button><button type="button" :disabled="!selected || saving" @click="saveDocument">{{ saving ? 'Saving…' : 'Save revision' }}</button><button type="button" class="danger" :disabled="!selected" @click="deleteSelected">Delete</button></div>
        </div>
        <textarea v-model="editorText" spellcheck="false" aria-label="JSON document editor" />
        <footer>{{ notice || 'JSON payloads are revisioned and conflicting writes fail closed.' }}</footer>
      </section>
    </section>
  </main>
</template>
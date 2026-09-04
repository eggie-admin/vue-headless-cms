<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { isPackagedCms, postNative } from './lib/cathedralBridge'

type CmsSummary = { id: string; kind: string; title: string; revision: number; updated_at: string }
type CmsDocument = CmsSummary & { payload: Record<string, unknown>; created_at: string }

const packagedCms = isPackagedCms()
const apiBase = packagedCms ? 'http://127.0.0.1:8000' : ''
const apiState = ref<'connecting' | 'online' | 'offline'>('connecting')
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

function headers(write = false): HeadersInit {
  const result: Record<string, string> = { 'Content-Type': 'application/json' }
  if (write && writeToken.value) result['X-Cathedral-Token'] = writeToken.value
  return result
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
    const target = preferId ?? selected.value?.id ?? documents.value[0]?.id
    if (target) await loadDocument(target)
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
      method: 'PUT',
      headers: headers(true),
      body: JSON.stringify({
        kind: selected.value.kind,
        title: selected.value.title,
        payload,
        expected_revision: selected.value.revision,
      }),
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
    method: 'PUT',
    headers: headers(true),
    body: JSON.stringify({ kind: newKind.value, title: newTitle.value.trim() || id, payload: {} }),
  })
  const data = await response.json()
  if (!response.ok) {
    notice.value = data.detail ?? `create ${response.status}`
    return
  }
  newId.value = ''
  notice.value = `Created ${id}.`
  postNative({ type: 'cms.document.saved', payload: { id, revision: 1 } })
  await refreshDocuments(id)
}

async function deleteSelected() {
  if (!selected.value) return
  const id = selected.value.id
  const revision = selected.value.revision
  const response = await fetch(`${apiBase}/api/cms/documents/${encodeURIComponent(id)}?revision=${revision}`, {
    method: 'DELETE', headers: headers(true),
  })
  const data = await response.json()
  if (!response.ok) {
    notice.value = data.detail ?? `delete ${response.status}`
    return
  }
  selected.value = null
  editorText.value = '{}'
  notice.value = `Deleted ${id}.`
  postNative({ type: 'cms.document.deleted', payload: { id } })
  await refreshDocuments()
}

function openGodotWindow() {
  postNative({ type: 'godot.window.open', payload: { panel: 'renderQueue' } })
}

onMounted(async () => {
  postNative({ type: 'cms.ready', payload: { version: '0.6.0-dev' } })
  await refreshDocuments()
})
</script>

<template>
  <main class="cms-shell">
    <header class="topbar">
      <div>
        <strong>Video Forge Cathedral CMS</strong>
        <span class="status" :data-state="apiState">{{ apiState }}</span>
      </div>
      <div class="token-row">
        <input v-model="writeToken" type="password" autocomplete="off" placeholder="CMS write token" @change="rememberToken" />
        <button type="button" @click="rememberToken">Arm writes</button>
        <button type="button" @click="openGodotWindow">Godot window</button>
      </div>
    </header>

    <section class="cms-grid">
      <aside class="sidebar">
        <div class="sidebar-title">Documents <button type="button" @click="refreshDocuments()">↻</button></div>
        <button
          v-for="doc in documents"
          :key="doc.id"
          class="doc-card"
          :class="{ active: selected?.id === doc.id }"
          type="button"
          @click="loadDocument(doc.id)"
        >
          <strong>{{ doc.title }}</strong>
          <span>{{ doc.id }}</span>
          <small>{{ doc.kind }} · r{{ doc.revision }}</small>
        </button>

        <div class="create-card">
          <strong>New document</strong>
          <input v-model="newId" placeholder="document-id" />
          <input v-model="newTitle" placeholder="Title" />
          <select v-model="newKind">
            <option value="ui_manifest">UI manifest</option>
            <option value="scene_manifest">Scene manifest</option>
            <option value="content">Content</option>
            <option value="character_bible">Character bible</option>
            <option value="visual_bible">Visual bible</option>
            <option value="asset_manifest">Asset manifest</option>
            <option value="cutscene">Cutscene</option>
          </select>
          <button type="button" @click="createDocument">Create</button>
        </div>
      </aside>

      <section class="editor-panel">
        <div class="editor-head">
          <div>
            <input v-if="selected" v-model="selected.title" class="title-input" />
            <strong v-else>Select a CMS document</strong>
            <small>{{ selectedLabel }}</small>
          </div>
          <div class="editor-actions">
            <button type="button" :disabled="!selected || saving" @click="saveDocument">{{ saving ? 'Saving…' : 'Save revision' }}</button>
            <button type="button" class="danger" :disabled="!selected" @click="deleteSelected">Delete</button>
          </div>
        </div>
        <textarea v-model="editorText" spellcheck="false" aria-label="JSON document editor" />
        <footer>{{ notice || 'JSON payloads are versioned in SQLite. Conflicting revisions fail closed.' }}</footer>
      </section>
    </section>
  </main>
</template>

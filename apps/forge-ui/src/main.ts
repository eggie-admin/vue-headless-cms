import $ from 'jquery'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'jquery-ui/themes/base/all.css'
import 'jquery-ui/ui/widgets/dialog'
import 'jquery-ui/ui/widgets/sortable'
import 'jquery-ui/ui/widgets/tabs'
import './styles.css'
import { isPackagedCms, postNative } from './lib/cathedralBridge'

type CmsSummary = { id: string; kind: string; title: string; revision: number; updated_at: string }
type CmsDocument = CmsSummary & { payload: Record<string, unknown>; created_at: string }
type ApiState = 'connecting' | 'online' | 'offline'
type CockpitOptions = { version?: string }

const QUESTS = ['Set up project structure','Implement core logic','Add error handling','Refactor for clarity','Write documentation','Prepare for deployment']
const COMMANDS = [
  ['/compile','Build your project'],
  ['/debug',"Find what's wrong"],
  ['/refactor','Make it better'],
  ['/ship','Deploy to the world'],
  ['/save 1','Save your progress'],
] as const

class Kai9000Cockpit {
  root: JQuery<HTMLElement>
  apiBase = isPackagedCms() ? 'http://127.0.0.1:8000' : ''
  state: ApiState = 'connecting'
  docs: CmsSummary[] = []
  selected: CmsDocument | null = null
  token = sessionStorage.getItem('cathedralCmsToken') ?? ''
  version: string

  constructor(el: HTMLElement, options: CockpitOptions = {}) {
    this.root = $(el)
    this.version = options.version ?? '1.0.0'
    this.render()
    this.bind()
    this.widgets()
    postNative({ type: 'cms.ready', payload: { version: this.version, shell: 'jquery-ui-bootstrap' } })
    void this.refreshDocs()
  }

  render() {
    const quests = QUESTS.map((q,i)=>`<li class="kai-quest ${i===0?'done':''}"><span class="grip">⋮⋮</span><label><input type="checkbox" ${i===0?'checked':''}><span>${q}</span></label></li>`).join('')
    const commands = COMMANDS.map(([c,l])=>`<button class="kai-command" type="button" data-command="${c}"><b>${c}</b><small>${l}</small></button>`).join('')
    this.root.html(`
      <main class="kai-shell">
        <header class="kai-topbar">
          <span class="kai-sigil">✦</span>
          <div><h1>KAI 9000</h1><p>CODE ✦ CREATE ✦ CONQUER</p></div>
          <span class="kai-version">v${this.version}</span>
          <span class="kai-online-pill"><i></i><b>CONNECTING</b></span>
        </header>

        <div id="kai-tabs">
          <ul class="kai-nav">
            <li><a href="#cockpit">⌂<span>Cockpit</span></a></li>
            <li><a href="#projects">▱<span>Projects</span></a></li>
            <li><a href="#acodex">▣<span>AcodeX</span></a></li>
            <li><a href="#artifacts">◇<span>Artifacts</span></a></li>
            <li><a href="#settings">⚙<span>Settings</span></a></li>
          </ul>

          <section id="cockpit" class="kai-page">
            <div class="container-fluid px-0">
              <div class="row g-3 align-items-stretch">
                <aside class="col-12 col-lg-3 kai-left">
                  <article class="kai-card kai-lum-card">
                    <p class="eyebrow">LUM</p><h2>Infernal Secretary</h2><small>AI operative · local cockpit avatar</small>
                    <hr><p class="loyal">♡ LOYAL<br>DANGEROUS<br>EFFICIENT<br>YOURS…</p>
                    <blockquote>“I don’t just collect code. I manage expectations.”</blockquote>
                    <div class="motto">DISCIPLINE CREATES FREEDOM</div>
                  </article>
                </aside>

                <section class="col-12 col-lg-6">
                  <article class="kai-avatar-card" role="img" aria-label="Lum AI avatar">
                    <div class="kai-avatar"></div>
                    <div class="kai-halo"></div>
                    <div class="kai-scan"></div>
                    <div class="kai-avatar-caption"><span class="kai-avatar-state">BOOTING</span><b>LUM</b><small>jQuery cockpit operative</small></div>
                  </article>
                </section>

                <aside class="col-12 col-lg-3 kai-right">
                  <article class="kai-card"><p class="eyebrow">ACTIVE QUESTS</p><ul class="kai-quests">${quests}</ul></article>
                  <article class="kai-card kai-rewards"><p class="eyebrow">REWARDS</p><div>✧ <b>Clean Build</b></div><div>⚙ <b>Fewer Bugs</b></div><div>✦ <b>A Happier You</b></div><div>◇ <b>Lum's Approval ♡</b></div></article>
                </aside>
              </div>

              <article class="kai-card kai-terminal">
                <header><span>✧ ACODEX TERMINAL</span><span>LOCAL BRIDGE</span></header>
                <div class="kai-terminal-grid">
                  <div class="kai-log">KAI9000 v${this.version} // jQuery Intelligence Layer<br>Type <b>/help</b> or tap a command.<br><span class="console">user@kai9000:~$ <i>▮</i></span></div>
                  <div class="kai-command-grid">${commands}</div>
                </div>
                <form class="kai-command-form"><span>user@kai9000:~$</span><input autocomplete="off" spellcheck="false" placeholder="/help"><button>RUN</button></form>
              </article>
            </div>
          </section>

          <section id="projects" class="kai-page">
            <div class="kai-page-head"><div><p class="eyebrow">PROJECTS / CMS</p><h2>KAI 9000 Document Forge</h2></div><div><button class="kai-btn refresh">↻ Refresh</button><button class="kai-btn new-doc">＋ New</button></div></div>
            <div class="kai-cms-grid">
              <aside class="kai-card kai-doc-list"></aside>
              <article class="kai-card kai-editor">
                <header><div><input class="kai-title" disabled placeholder="Select a CMS document"><small class="kai-selected">No document selected</small></div><div><button class="kai-btn save" disabled>Save revision</button><button class="kai-btn danger delete" disabled>Delete</button></div></header>
                <textarea class="kai-json" spellcheck="false">{}</textarea>
                <footer class="kai-notice">JSON payloads are versioned in SQLite. Conflicting revisions fail closed.</footer>
              </article>
            </div>
          </section>

          <section id="acodex" class="kai-page">
            <div class="kai-page-head"><div><p class="eyebrow">ACODEX</p><h2>Command Deck</h2></div></div>
            <article class="kai-card kai-acodex"><p>Commands emit <code>kai.command</code> through the native bridge. The WebView does not execute arbitrary shell text.</p><div class="kai-command-grid">${commands}</div></article>
          </section>

          <section id="artifacts" class="kai-page">
            <div class="kai-page-head"><div><p class="eyebrow">ARTIFACTS</p><h2>Save Slots</h2></div></div>
            <div class="kai-save-grid"><article class="kai-card"><b>1 · FINAL RELEASE</b><span>KAI9000_FINAL_MILESTONE_GREEN_20260908</span></article><article class="kai-card"><b>2 · COMPILE GREEN</b><span>KAI9000_COMPILE_GREEN_20260908</span></article><article class="kai-card"><b>3 · BASELINE</b><span>KAI9000_FINAL_MUTATION_GREEN_20260907</span></article></div>
          </section>

          <section id="settings" class="kai-page">
            <div class="kai-page-head"><div><p class="eyebrow">SETTINGS</p><h2>Cockpit Controls</h2></div></div>
            <div class="kai-save-grid"><article class="kai-card"><h3>CMS writes</h3><p>Token stays in sessionStorage.</p><button class="kai-btn arm">Arm writes</button></article><article class="kai-card"><h3>Godot</h3><p>Open the native render queue.</p><button class="kai-btn godot">Godot window</button></article><article class="kai-card"><h3>Avatar</h3><p>Local supplied Lum art with CSS motion.</p><button class="kai-btn avatar-toggle">Pause avatar</button></article></div>
          </section>
        </div>

        <div id="token-dialog" title="Arm CMS writes"><label>CMS write token<input id="write-token" type="password" autocomplete="off"></label></div>
        <div id="new-dialog" title="New CMS document">
          <label>Document id<input id="new-id" placeholder="document-id"></label>
          <label>Title<input id="new-title" value="Untitled Document"></label>
          <label>Kind<select id="new-kind"><option value="content">Content</option><option value="ui_manifest">UI manifest</option><option value="scene_manifest">Scene manifest</option><option value="character_bible">Character bible</option><option value="visual_bible">Visual bible</option><option value="asset_manifest">Asset manifest</option><option value="cutscene">Cutscene</option></select></label>
        </div>
      </main>
    `)
  }

  widgets() {
    ;(this.root.find('#kai-tabs') as any).tabs({ active: 0 })
    ;(this.root.find('.kai-quests') as any).sortable({ handle: '.grip', axis: 'y' })
    ;(this.root.find('#token-dialog') as any).dialog({
      autoOpen:false, modal:true, width:Math.min(420,window.innerWidth-24),
      buttons:{
        'Arm writes':()=>{ this.token=String(this.root.find('#write-token').val()??''); sessionStorage.setItem('cathedralCmsToken',this.token); this.notice(this.token?'Write token stored for this WebView session.':'Write token cleared.'); (this.root.find('#token-dialog') as any).dialog('close') },
        Cancel:()=> (this.root.find('#token-dialog') as any).dialog('close'),
      }
    })
    ;(this.root.find('#new-dialog') as any).dialog({
      autoOpen:false, modal:true, width:Math.min(440,window.innerWidth-24),
      buttons:{ Create:()=>void this.createDoc(), Cancel:()=> (this.root.find('#new-dialog') as any).dialog('close') }
    })
  }

  bind() {
    this.root.on('change','.kai-quest input',(e)=>$(e.currentTarget).closest('.kai-quest').toggleClass('done',(e.currentTarget as HTMLInputElement).checked))
    this.root.on('click','.kai-command',(e)=>this.command(String($(e.currentTarget).data('command')??'')))
    this.root.on('submit','.kai-command-form',(e)=>{ e.preventDefault(); const input=$(e.currentTarget).find('input'); this.command(String(input.val()??'')); input.val('') })
    this.root.on('click','.refresh',()=>void this.refreshDocs())
    this.root.on('click','.new-doc',()=> (this.root.find('#new-dialog') as any).dialog('open'))
    this.root.on('click','.save',()=>void this.saveDoc())
    this.root.on('click','.delete',()=>void this.deleteDoc())
    this.root.on('click','.kai-doc',(e)=>void this.loadDoc(String($(e.currentTarget).data('id')??'')))
    this.root.on('input','.kai-title',(e)=>{ if(this.selected)this.selected.title=String((e.currentTarget as HTMLInputElement).value) })
    this.root.on('click','.arm',()=>{ this.root.find('#write-token').val(this.token); (this.root.find('#token-dialog') as any).dialog('open') })
    this.root.on('click','.godot',()=>this.notice(postNative({type:'godot.window.open',payload:{panel:'renderQueue'}})?'Requested Godot render queue.':'Native bridge unavailable in browser preview.'))
    this.root.on('click','.avatar-toggle',(e)=>{ const paused=this.root.toggleClass('avatar-paused').hasClass('avatar-paused'); $(e.currentTarget).text(paused?'Resume avatar':'Pause avatar'); this.avatar(paused?'standby':'ready') })
  }

  command(command:string) {
    const c=command.trim()
    if(!c)return
    if(c==='/help'){ this.console('/compile · /debug · /refactor · /ship · /save 1'); return }
    if(!COMMANDS.some(([x])=>x===c)){ this.console(`Unknown command: ${c}`); return }
    this.avatar('thinking')
    const sent=postNative({type:'kai.command',payload:{command:c}})
    this.console(sent?`${c} → native bridge`:`${c} → preview only`)
    window.setTimeout(()=>this.avatar(this.state==='online'?'ready':'standby'),650)
  }

  console(text:string){ this.root.find('.console').html(`user@kai9000:~$ ${this.escape(text)} <i>▮</i>`) }
  avatar(state:string){ this.root.attr('data-avatar-state',state); this.root.find('.kai-avatar-state').text(state.toUpperCase()) }
  headers(write=false){ const h:Record<string,string>={'Content-Type':'application/json'}; if(write&&this.token)h['X-Cathedral-Token']=this.token; return h }
  setState(state:ApiState){ this.state=state; this.root.attr('data-api-state',state); this.root.find('.kai-online-pill b').text(state.toUpperCase()); this.avatar(state==='online'?'ready':state==='offline'?'standby':'booting') }
  notice(text:string){ this.root.find('.kai-notice').text(text) }

  async refreshDocs(prefer?:string) {
    try {
      const r=await fetch(`${this.apiBase}/api/cms/documents`,{cache:'no-store'})
      if(!r.ok)throw new Error(`CMS list ${r.status}`)
      const data=await r.json(); this.docs=data.documents??[]; this.setState('online'); this.renderDocs()
      const target=prefer??this.selected?.id??this.docs[0]?.id; if(target)await this.loadDoc(target)
    } catch(e){ this.setState('offline'); this.notice(String(e)); this.renderDocs() }
  }

  renderDocs() {
    const box=this.root.find('.kai-doc-list').empty()
    if(!this.docs.length){ box.append('<div class="kai-empty">No CMS documents yet.</div>'); return }
    for(const d of this.docs) box.append(`<button class="kai-doc ${this.selected?.id===d.id?'active':''}" data-id="${this.escape(d.id)}"><b>${this.escape(d.title)}</b><span>${this.escape(d.id)}</span><small>${this.escape(d.kind)} · r${d.revision}</small></button>`)
  }

  async loadDoc(id:string) {
    if(!id)return
    try{
      const r=await fetch(`${this.apiBase}/api/cms/documents/${encodeURIComponent(id)}`,{cache:'no-store'})
      if(!r.ok)throw new Error(`CMS document ${r.status}`)
      const data=await r.json(); this.selected=data.document; this.root.find('.kai-title').prop('disabled',false).val(this.selected?.title??''); this.root.find('.kai-selected').text(this.selected?`${this.selected.kind} · r${this.selected.revision}`:''); this.root.find('.kai-json').val(JSON.stringify(this.selected?.payload??{},null,2)); this.root.find('.save,.delete').prop('disabled',false); this.renderDocs(); this.notice('')
    }catch(e){this.notice(String(e))}
  }

  async saveDoc() {
    if(!this.selected)return
    try{
      const payload=JSON.parse(String(this.root.find('.kai-json').val()??'{}'))
      const r=await fetch(`${this.apiBase}/api/cms/documents/${encodeURIComponent(this.selected.id)}`,{method:'PUT',headers:this.headers(true),body:JSON.stringify({kind:this.selected.kind,title:this.selected.title,payload,expected_revision:this.selected.revision})})
      const data=await r.json(); if(!r.ok)throw new Error(data.detail??`save ${r.status}`)
      this.selected=data.document; postNative({type:'cms.document.saved',payload:{id:data.document.id,revision:data.document.revision}}); this.notice(`Saved ${data.document.id} revision ${data.document.revision}.`); await this.refreshDocs(data.document.id)
    }catch(e){this.notice(String(e))}
  }

  async createDoc() {
    const id=String(this.root.find('#new-id').val()??'').trim().toLowerCase()
    const title=String(this.root.find('#new-title').val()??'').trim()||id
    const kind=String(this.root.find('#new-kind').val()??'content')
    if(!/^[a-z0-9][a-z0-9_.-]{0,79}$/.test(id)){this.notice('Document id must use lowercase letters, numbers, dot, dash or underscore.');return}
    try{
      const r=await fetch(`${this.apiBase}/api/cms/documents/${encodeURIComponent(id)}`,{method:'PUT',headers:this.headers(true),body:JSON.stringify({kind,title,payload:{}})})
      const data=await r.json(); if(!r.ok)throw new Error(data.detail??`create ${r.status}`)
      postNative({type:'cms.document.saved',payload:{id,revision:1}}); (this.root.find('#new-dialog') as any).dialog('close'); this.notice(`Created ${id}.`); await this.refreshDocs(id)
    }catch(e){this.notice(String(e))}
  }

  async deleteDoc() {
    if(!this.selected)return
    try{
      const id=this.selected.id, rev=this.selected.revision
      const r=await fetch(`${this.apiBase}/api/cms/documents/${encodeURIComponent(id)}?revision=${rev}`,{method:'DELETE',headers:this.headers(true)})
      const data=await r.json(); if(!r.ok)throw new Error(data.detail??`delete ${r.status}`)
      postNative({type:'cms.document.deleted',payload:{id}}); this.selected=null; this.root.find('.kai-title').prop('disabled',true).val(''); this.root.find('.kai-json').val('{}'); this.root.find('.save,.delete').prop('disabled',true); this.notice(`Deleted ${id}.`); await this.refreshDocs()
    }catch(e){this.notice(String(e))}
  }

  escape(v:string){return $('<div>').text(v).html()}
}

;(($.fn as any).kai9000Cockpit=function(options:CockpitOptions={}){
  return this.each(function(){ const el=this as HTMLElement; if(!$.data(el,'kai9000Cockpit'))$.data(el,'kai9000Cockpit',new Kai9000Cockpit(el,options)) })
}) as unknown

$(()=> ($('#app') as any).kai9000Cockpit({version:'1.0.0'}))

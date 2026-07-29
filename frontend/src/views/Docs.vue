<template>
  <div class="docs-page">
    <!-- Sidebar toggle for mobile -->
    <button class="sidebar-toggle" @click="sidebarOpen = !sidebarOpen">
      <span>{{ sidebarOpen ? '\u2715' : '\u2630' }}</span> {{ sidebarOpen ? '关闭目录' : '目录' }}
    </button>

    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-search">
        <input
          v-model="searchQuery"
          placeholder="搜索文档..."
          @input="onSearchInput"
        />
      </div>
      <div class="sidebar-tree">
        <div v-for="cat in catalog" :key="cat.name" class="tree-cat">
          <div class="tree-cat__title" @click="cat.expanded = !cat.expanded">
            <span>{{ cat.expanded ? '\u25BE' : '\u25B8' }}</span> {{ cat.name }}
          </div>
          <div v-show="cat.expanded" class="tree-items">
            <router-link
              v-for="doc in filteredDocs(cat.items)"
              :key="doc.id"
              :to="'/docs/' + doc.id"
              :class="{ active: currentId == doc.id }"
              @click="sidebarOpen = false"
            >
              {{ doc.title }}
            </router-link>
          </div>
        </div>
      </div>
    </aside>

    <!-- Document detail -->
    <article class="doc-content" v-if="currentDoc && !docLoading">
      <div class="doc-header">
        <p class="breadcrumb">
          <router-link to="/docs">文档</router-link> /
          <span v-if="currentDoc.category">{{ currentDoc.category }}</span>
        </p>
        <h1>{{ currentDoc.title }}</h1>
        <p class="doc-meta">更新于 {{ currentDoc.updated_at || '2026-07-10' }}</p>
      </div>

      <div class="doc-body" ref="docBodyRef" v-html="renderMarkdown(currentDoc.content)"></div>

      <div class="doc-footer">
        <p>这篇文章对你有帮助吗？</p>
        <button class="btn-feedback" @click="feedback('yes')">有帮助</button>
        <button class="btn-feedback" @click="feedback('no')">没帮助</button>
      </div>
    </article>

    <!-- Document skeleton -->
    <article class="doc-content" v-if="docLoading">
      <div class="doc-header">
        <SkeletonLoader width="140px" height="14px" />
        <SkeletonLoader width="60%" height="28px" style="margin-top:12px" />
        <SkeletonLoader width="160px" height="13px" style="margin-top:8px" />
      </div>
      <div class="doc-body">
        <SkeletonLoader width="100%" height="15px" v-for="n in 12" :key="n" style="margin-bottom:10px" />
        <SkeletonLoader width="70%" height="15px" />
      </div>
    </article>

    <!-- Document list (no specific doc selected) -->
    <article class="doc-content" v-if="!currentDoc && !docLoading">
      <h1>{{ searchQuery ? '搜索结果' : '文档中心' }}</h1>
      <div class="card-grid" v-if="allDocs.length">
        <router-link v-for="doc in allDocs" :key="doc.id" :to="'/docs/' + doc.id" class="doc-card">
          <h3>{{ doc.title }}</h3>
          <p>{{ doc.summary || doc.content?.slice(0, 100) }}</p>
          <span class="tag">{{ doc.category }}</span>
        </router-link>
      </div>
      <div class="empty-state" v-else>
        <p v-if="searchQuery">未找到与「{{ searchQuery }}」相关的文档</p>
        <p v-else>暂无文档</p>
      </div>
    </article>

    <!-- TOC -->
    <aside class="toc" v-if="currentDoc && !docLoading">
      <h4>目录</h4>
      <nav v-html="tocHtml"></nav>
    </aside>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick, inject } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import SkeletonLoader from '../components/SkeletonLoader.vue'
import { request } from '../composables/useRequest'

const route = useRoute()
const toast = inject('$toast', null)
const searchQuery = ref('')
const allDocs = ref([])
const catalog = ref([])
const docLoading = ref(false)
const sidebarOpen = ref(false)
const docBodyRef = ref(null)
let debounceTimer = null

const currentId = computed(() => route.params.id)

const currentDoc = computed(() => {
  if (!currentId.value) return null
  for (const cat of catalog.value) {
    const found = cat.items?.find(d => d.id == currentId.value)
    if (found) return found
  }
  return allDocs.value.find(d => d.id == currentId.value) || null
})

function attachCopyButtons() {
  nextTick(() => {
    if (!docBodyRef.value) return
    const pres = docBodyRef.value.querySelectorAll('pre')
    pres.forEach(pre => {
      if (pre.querySelector('.copy-btn')) return
      const btn = document.createElement('button')
      btn.className = 'copy-btn'
      btn.textContent = '复制'
      btn.addEventListener('click', async () => {
        const code = pre.querySelector('code')?.textContent || pre.textContent
        try {
          await navigator.clipboard.writeText(code)
          btn.textContent = '已复制'
          btn.classList.add('copied')
          setTimeout(() => {
            btn.textContent = '复制'
            btn.classList.remove('copied')
          }, 2000)
        } catch {
          const ta = document.createElement('textarea')
          ta.value = code
          ta.style.position = 'fixed'; ta.style.opacity = '0'
          document.body.appendChild(ta)
          ta.select()
          document.execCommand('copy')
          document.body.removeChild(ta)
          btn.textContent = '已复制'
          btn.classList.add('copied')
          setTimeout(() => {
            btn.textContent = '复制'
            btn.classList.remove('copied')
          }, 2000)
        }
      })
      pre.appendChild(btn)
    })
  })
}

async function loadDoc(id) {
  const found = currentDoc.value
  if (found && !found.content) {
    docLoading.value = true
    try {
      const res = await request(`/api/docs/${id}`)
      if (res.ok) {
        const data = await res.json()
        Object.assign(found, data)
        attachCopyButtons()
      }
    } catch (e) { console.error(e) }
    docLoading.value = false
  } else if (found?.content) {
    attachCopyButtons()
  }
}

watch(currentId, (id) => {
  if (id) loadDoc(id)
  else docLoading.value = false
}, { immediate: true })

onMounted(async () => {
  try {
    const [docsRes, catRes] = await Promise.all([
      request('/api/docs', { silent: true }),
      request('/api/docs/catalog', { silent: true }),
    ])
    if (docsRes.ok) allDocs.value = await docsRes.json()
    if (catRes.ok) catalog.value = (await catRes.json()).map(c => ({ ...c, expanded: true }))
  } catch {
    toast?.error('获取文档列表失败')
  }
  if (currentId.value) loadDoc(currentId.value)
})

function onSearchInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    // 300ms debounce — the computed filteredDocs reacts to searchQuery
  }, 300)
}

function filteredDocs(items) {
  if (!searchQuery.value) return items || []
  const q = searchQuery.value.toLowerCase()
  return (items || []).filter(d => d.title?.toLowerCase().includes(q))
}

function renderMarkdown(text) {
  if (!text) return ''
  marked.setOptions({ breaks: true, gfm: true })
  const html = marked(text)
  return DOMPurify.sanitize(html)
}

const tocHtml = computed(() => {
  const doc = currentDoc.value
  if (!doc?.content) return ''
  const headings = doc.content.match(/^#{1,3} .+/gm) || []
  const html = headings.map(h => {
    const level = h.match(/^#+/)[0].length
    const text = h.replace(/^#+ /, '')
    const slug = text.toLowerCase().replace(/\s+/g, '-').replace(/[^\w\u4e00-\u9fff-]/g, '')
    return `<a href="#${slug}" class="toc-h${level}">${text}</a>`
  }).join('')
  return DOMPurify.sanitize(html)
})

function feedback(type) {
  if (toast) {
    toast.success(type === 'yes' ? '感谢你的反馈！' : '我们会继续改进')
  }
}
</script>

<style scoped>
.docs-page {
  display: grid;
  grid-template-columns: 260px 1fr 180px;
  gap: 32px;
}

/* Sidebar toggle (mobile) */
.sidebar-toggle {
  display: none;
  width: 100%;
  padding: 10px 16px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
  margin-bottom: 16px;
  min-height: 44px;
  align-items: center;
}
.sidebar-toggle span { margin-right: 6px; }

/* Sidebar */
.sidebar {
  position: sticky; top: 80px; align-self: start;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
}
.sidebar-search input {
  width: 100%; padding: 10px 14px; border: 1px solid var(--border); border-radius: var(--radius);
  font-size: 14px; outline: none; margin-bottom: 16px;
}
.sidebar-search input:focus { border-color: var(--primary); }

.tree-cat { margin-bottom: 8px; }
.tree-cat__title {
  font-size: 13px; font-weight: 700; color: var(--text-muted); cursor: pointer;
  padding: 4px 0; user-select: none; text-transform: uppercase; letter-spacing: .5px;
  min-height: 32px; display: flex; align-items: center;
}
.tree-items a {
  display: block; font-size: 14px; padding: 8px 12px; border-radius: var(--radius-sm);
  color: var(--text); margin: 2px 0; transition: background .1s;
  min-height: 36px; display: flex; align-items: center;
}
.tree-items a:hover, .tree-items a.active {
  background: #eef2ff; color: var(--primary); font-weight: 500; text-decoration: none;
}

/* Document Content */
.doc-content { min-height: 60vh; }
.doc-header { margin-bottom: 28px; }
.breadcrumb { font-size: 13px; color: var(--text-muted); margin-bottom: 8px; }
.doc-header h1 { font-size: 30px; font-weight: 800; margin: 8px 0 4px; line-height: 1.3; }
.doc-meta { font-size: 13px; color: var(--text-muted); }

/* Document Body Typography */
.doc-body { line-height: 1.85; font-size: 15px; color: var(--text); }
.doc-body :deep(h2) {
  margin-top: 40px; margin-bottom: 14px; font-size: 22px; font-weight: 700;
  padding-bottom: 8px; border-bottom: 1px solid var(--border);
}
.doc-body :deep(h3) {
  margin-top: 32px; margin-bottom: 10px; font-size: 18px; font-weight: 600;
}
.doc-body :deep(h4) {
  margin-top: 24px; margin-bottom: 8px; font-size: 16px; font-weight: 600;
}
.doc-body :deep(p) {
  margin-bottom: 14px;
}
.doc-body :deep(ul), .doc-body :deep(ol) {
  margin-bottom: 14px; padding-left: 22px;
}
.doc-body :deep(li) { margin-bottom: 6px; }

.doc-body :deep(code) {
  background: #f1f5f9; padding: 2px 8px; border-radius: 4px; font-size: 13px;
  color: var(--primary-dark); font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
}
.doc-body :deep(pre) {
  background: var(--code-bg); color: var(--code-fg);
  padding: 20px; border-radius: var(--radius);
  overflow-x: auto; margin: 20px 0;
  font-size: 14px; line-height: 1.55;
  position: relative;
}
.doc-body :deep(pre code) {
  background: none; padding: 0; color: inherit; font-size: inherit;
}

/* Zebra table */
.doc-body :deep(table) {
  width: 100%; border-collapse: collapse; margin: 16px 0;
  font-size: 14px;
}
.doc-body :deep(th) {
  background: #f1f5f9; padding: 10px 14px; text-align: left;
  font-weight: 600; border-bottom: 2px solid var(--border);
}
.doc-body :deep(td) {
  padding: 10px 14px; border-bottom: 1px solid var(--border);
}
.doc-body :deep(tr:nth-child(even) td) {
  background: #f8fafc;
}

.doc-body :deep(blockquote) {
  border-left: 3px solid var(--primary);
  padding: 8px 16px; margin: 16px 0;
  background: #f8f9fb; border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  color: var(--text-muted);
}
.doc-body :deep(hr) {
  border: none; border-top: 1px solid var(--border); margin: 32px 0;
}

/* Doc Footer */
.doc-footer {
  margin-top: 48px; padding-top: 24px; border-top: 1px solid var(--border);
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}
.doc-footer p { font-size: 14px; color: var(--text-muted); margin: 0; }
.btn-feedback {
  padding: 8px 20px; border: 1px solid var(--border); border-radius: 20px;
  background: var(--card); cursor: pointer; font-size: 13px;
  transition: all .15s; min-height: 36px;
}
.btn-feedback:hover { border-color: var(--primary); color: var(--primary); }

/* TOC */
.toc { position: sticky; top: 80px; align-self: start; }
.toc h4 {
  font-size: 13px; text-transform: uppercase; color: var(--text-muted);
  margin-bottom: 12px; letter-spacing: .5px;
}
.toc :deep(a) { display: block; font-size: 13px; color: var(--text-muted); padding: 5px 0; }
.toc :deep(a:hover) { color: var(--primary); text-decoration: none; }
.toc :deep(.toc-h2) { padding-left: 0; }
.toc :deep(.toc-h3) { padding-left: 14px; font-size: 12px; }

/* Empty State */
.empty-state {
  text-align: center; padding: 60px 0;
}
.empty-state p { color: var(--text-muted); font-size: 15px; }

/* Card Grid (document list) */
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-top: 20px; }
.doc-card {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 20px; display: block; color: inherit; text-decoration: none;
  transition: box-shadow .2s, transform .2s;
}
.doc-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); text-decoration: none; }
.doc-card h3 { font-size: 16px; margin-bottom: 6px; }
.doc-card p { font-size: 13px; color: var(--text-muted); margin-bottom: 10px; line-height: 1.5; }
.tag { font-size: 12px; background: #eef2ff; color: var(--primary); padding: 2px 10px; border-radius: 20px; }

/* Responsive */
@media (max-width: 1024px) {
  .docs-page {
    grid-template-columns: 1fr;
  }
  .toc { display: none; }
  .sidebar {
    display: block;
    position: static;
    max-height: 0;
    overflow: hidden;
    transition: max-height .3s ease, padding .3s ease, margin .3s ease;
    margin-bottom: 0;
    padding-bottom: 0;
  }
  .sidebar.open {
    max-height: 2000px;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
  }
  .sidebar-toggle { display: flex; }
}
@media (max-width: 480px) {
  .doc-header h1 { font-size: 24px; }
  .doc-body { font-size: 14px; }
  .doc-body :deep(pre) {
    font-size: 12px;
    padding: 14px;
    border-radius: var(--radius-sm);
  }
  .doc-body :deep(pre code) { font-size: 12px; }
  .card-grid { grid-template-columns: 1fr; }
}
</style>

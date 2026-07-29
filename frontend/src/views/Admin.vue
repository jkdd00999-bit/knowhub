<template>
  <div class="admin">
    <h1>管理后台</h1>

    <section class="panel">
      <h2>文档管理</h2>
      <div class="panel-actions">
        <button class="btn-primary" @click="showEditor = true; editingDoc = null">+ 新建文档</button>
        <span class="doc-count">共 {{ docs.length }} 篇</span>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="table-skeleton">
        <SkeletonLoader width="100%" height="36px" style="margin-bottom:8px" />
        <SkeletonLoader width="100%" height="32px" style="margin-bottom:4px" v-for="n in 4" :key="n" />
      </div>

      <div class="table-wrap" v-if="!loading && docs.length">
        <table class="table">
          <thead><tr><th>标题</th><th>分类</th><th>更新时间</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="doc in docs" :key="doc.id">
              <td class="table-title">{{ doc.title }}</td>
              <td><span class="tag">{{ doc.category }}</span></td>
              <td class="table-time">{{ doc.updated_at || '-' }}</td>
              <td class="table-actions">
                <button class="btn-link" @click="editDoc(doc)">编辑</button>
                <button class="btn-link danger" @click="deleteDoc(doc.id)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p v-if="!loading && !docs.length" class="empty">暂无文档</p>
    </section>

    <!-- 编辑器弹窗 -->
    <div class="modal-overlay" v-if="showEditor" @click.self="showEditor = false">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingDoc ? '编辑文档' : '新建文档' }}</h3>
          <button class="modal-close" @click="showEditor = false">&times;</button>
        </div>
        <input v-model="editForm.title" placeholder="文档标题" />
        <input v-model="editForm.category" placeholder="分类（如「API 对接」「快速入门」）" />
        <div class="editor-wrapper">
          <textarea v-model="editForm.content" placeholder="Markdown 内容" rows="16"></textarea>
        </div>
        <div class="modal-actions">
          <button class="btn-primary" @click="saveDoc" :disabled="!editForm.title || saving">
            <span v-if="saving" class="spinner-sm"></span>
            {{ saving ? '保存中...' : '保存' }}
          </button>
          <button class="btn-cancel" @click="showEditor = false">取消</button>
        </div>
      </div>
    </div>

    <section class="panel">
      <h2>数据看板</h2>
      <div class="stats-grid" v-if="!loading">
        <div class="stat-card">
          <div class="stat-value">{{ docs.length }}</div>
          <div class="stat-label">文档总数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ unanswered.length }}</div>
          <div class="stat-label">AI 未命中问题</div>
        </div>
      </div>
      <div v-else class="stats-grid">
        <SkeletonLoader width="100%" height="80px" v-for="n in 2" :key="n" />
      </div>
    </section>

    <section class="panel" v-if="!loading && unanswered.length">
      <h2>AI 未命中问题 <span class="hint">（这些是 AI 回答不了的问题，可据此补充文档）</span></h2>
      <div class="unanswered-list">
        <div v-for="(q, i) in unanswered" :key="i" class="unanswered-item">
          <p>{{ q.question }}</p>
          <span>出现 {{ q.count }} 次</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'
import SkeletonLoader from '../components/SkeletonLoader.vue'
import { request } from '../composables/useRequest'

const toast = inject('$toast', null)
const docs = ref([])
const unanswered = ref([])
const showEditor = ref(false)
const editingDoc = ref(null)
const editForm = ref({ title: '', category: '', content: '' })
const loading = ref(true)
const saving = ref(false)

async function fetchData() {
  loading.value = true
  try {
    const [docsRes, uRes] = await Promise.all([
      request('/api/docs', { silent: true }),
      request('/api/admin/unanswered', { silent: true }),
    ])
    if (docsRes.ok) docs.value = await docsRes.json()
    if (uRes.ok) unanswered.value = await uRes.json()
  } catch (e) { console.error(e) }
  loading.value = false
}

onMounted(fetchData)

function editDoc(doc) {
  editingDoc.value = doc
  editForm.value = { title: doc.title, category: doc.category, content: doc.content || '' }
  showEditor.value = true
}

async function saveDoc() {
  if (!editForm.value.title || saving.value) return
  saving.value = true
  const url = editingDoc.value ? `/api/docs/${editingDoc.value.id}` : '/api/docs'
  const method = editingDoc.value ? 'PUT' : 'POST'
  try {
    const res = await request(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editForm.value),
    })
    if (res.ok) {
      const isEdit = !!editingDoc.value
      showEditor.value = false
      editingDoc.value = null
      toast?.success(isEdit ? '文档已更新' : '文档已创建')
      await fetchData()
    }
  } catch (e) { console.error(e) }
  saving.value = false
}

async function deleteDoc(id) {
  if (!confirm('确定删除这篇文档？')) return
  try {
    await request(`/api/docs/${id}`, { method: 'DELETE', silent: true })
    toast?.success('文档已删除')
    await fetchData()
  } catch (e) { console.error(e) }
}
</script>

<style scoped>
.admin { max-width: 900px; }
h1 { font-size: 28px; font-weight: 800; margin-bottom: 32px; }

.panel {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 24px; margin-bottom: 24px;
}
.panel h2 { font-size: 18px; font-weight: 700; margin-bottom: 16px; }
.hint { font-weight: 400; font-size: 13px; color: var(--text-muted); }
.panel-actions { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.doc-count { font-size: 13px; color: var(--text-muted); }

.btn-primary {
  padding: 8px 18px; background: var(--primary); color: #fff; border: none; border-radius: 8px;
  cursor: pointer; font-size: 14px; font-weight: 600;
  min-height: 44px; min-width: 44px;
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  transition: background .15s;
}
.btn-primary:hover:not(:disabled) { background: var(--primary-light); }
.btn-primary:disabled { opacity: .4; cursor: not-allowed; }
.btn-cancel {
  padding: 8px 18px; background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
  cursor: pointer; font-size: 14px; min-height: 44px;
  display: inline-flex; align-items: center; justify-content: center;
}
.btn-cancel:hover { background: var(--border); }

/* Spinner small */
.spinner-sm {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .6s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }

.table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  margin: 0 -24px;
  padding: 0 24px;
}
.table { width: 100%; border-collapse: collapse; font-size: 14px; min-width: 500px; }
.table th { text-align: left; padding: 8px 12px; border-bottom: 2px solid var(--border); color: var(--text-muted); font-weight: 600; white-space: nowrap; }
.table td { padding: 10px 12px; border-bottom: 1px solid var(--border); }
.table-title { font-weight: 500; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.table-time { color: var(--text-muted); font-size: 13px; white-space: nowrap; }
.table-actions { white-space: nowrap; }
.table-skeleton { padding: 8px 0; }

.btn-link { background: none; border: none; color: var(--primary); cursor: pointer; font-size: 13px; margin-right: 12px; min-height: 32px; }
.btn-link.danger { color: #ef4444; }
.btn-link:hover { text-decoration: underline; }
.tag { font-size: 12px; background: #eef2ff; color: var(--primary); padding: 2px 10px; border-radius: 20px; }

.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.35); display: flex;
  align-items: center; justify-content: center; z-index: 1000;
  padding: 16px;
}
.modal {
  background: var(--card); border-radius: var(--radius-lg); padding: 28px;
  width: 100%; max-width: 680px; max-height: 85vh;
  overflow-y: auto;
  display: flex; flex-direction: column; gap: 14px;
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
}
.modal-header h3 { font-size: 18px; font-weight: 700; }
.modal-close {
  background: none; border: none; font-size: 24px; color: var(--text-muted);
  cursor: pointer; padding: 4px 8px; border-radius: 6px;
  min-width: 36px; min-height: 36px;
  display: inline-flex; align-items: center; justify-content: center;
}
.modal-close:hover { background: var(--bg); }
.modal input {
  padding: 10px 14px; border: 1px solid var(--border); border-radius: var(--radius);
  font-size: 14px; outline: none;
}
.modal input:focus { border-color: var(--primary); }
.editor-wrapper {
  border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden;
}
.editor-wrapper:focus-within { border-color: var(--primary); }
.modal textarea {
  width: 100%; padding: 14px; border: none; font-size: 14px;
  outline: none; font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  resize: vertical; min-height: 300px; line-height: 1.6;
  background: var(--code-bg); color: var(--code-fg);
}
.modal-actions { display: flex; gap: 8px; }

.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.stat-card { background: var(--bg); border-radius: var(--radius); padding: 20px; text-align: center; }
.stat-value { font-size: 32px; font-weight: 800; color: var(--primary); }
.stat-label { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

.unanswered-item {
  padding: 10px 0; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; gap: 12px;
}
.unanswered-item p { font-size: 14px; flex: 1; min-width: 0; }
.unanswered-item span { font-size: 12px; color: var(--text-muted); flex-shrink: 0; }
.empty { color: var(--text-muted); }

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: 1fr; }
  .modal { padding: 20px; max-height: 90vh; }
  .modal textarea { min-height: 200px; font-size: 13px; }
  .panel { padding: 16px; }
  .table-wrap { margin: 0 -16px; padding: 0 16px; }
}
</style>


<template>
  <div class="knowledge-page">
    <section class="kb-hero">
      <h1>📚 知识库</h1>
      <p>企业级知识管理，智能检索，精准触达</p>
    </section>

    <!-- 搜索 -->
    <div class="search-bar">
      <input
        v-model="searchQuery"
        placeholder="搜索知识库..."
        @input="filterKnowledge"
      />
      <span class="search-icon">🔍</span>
    </div>

    <!-- 热门文档 -->
    <section v-if="hotDocs.length > 0" class="hot-docs-section">
      <div class="section-header">
        <h2>🔥 热门文档</h2>
        <p>大家都在看</p>
      </div>
      <div class="hot-docs-grid">
        <router-link
          v-for="doc in hotDocs"
          :key="doc.id"
          :to="'/docs/' + doc.id"
          class="hot-doc-card"
        >
          <div class="hot-doc-title">{{ doc.title }}</div>
          <div class="hot-doc-summary">{{ doc.summary }}</div>
          <div class="hot-doc-meta">
            <span class="category-tag">{{ doc.category }}</span>
            <span class="update-time">{{ formatDate(doc.updated_at) }}</span>
          </div>
        </router-link>
      </div>
    </section>

    <!-- 知识库列表 -->
    <div v-if="loading" class="kb-grid">
      <div v-for="n in 6" :key="n" class="kb-card skeleton-card">
        <SkeletonLoader width="48px" height="48px" />
        <SkeletonLoader width="60%" height="18px" style="margin-top:12px" />
        <SkeletonLoader width="100%" height="13px" style="margin-top:8px" />
        <SkeletonLoader width="40%" height="12px" style="margin-top:12px" />
      </div>
    </div>

    <div v-else class="kb-grid">
      <div
        v-for="kb in filteredKnowledge"
        :key="kb.id"
        class="kb-card"
        @click="openKnowledge(kb)"
      >
        <div class="kb-icon">{{ kb.icon }}</div>
        <h3>{{ kb.name }}</h3>
        <p>{{ kb.description }}</p>
        <div class="kb-stats">
          <span class="stat">📄 {{ kb.docCount }} 篇文档</span>
          <span class="stat">🕐 {{ kb.updatedAt }}</span>
        </div>
        <div class="kb-tags">
          <span v-for="tag in kb.tags" :key="tag" class="tag">{{ tag }}</span>
        </div>
      </div>
    </div>

    <!-- 知识库详情弹窗 -->
    <div v-if="selectedKb" class="modal-overlay" @click.self="selectedKb = null">
      <div class="modal-content">
        <div class="modal-header">
          <div class="modal-title">
            <span class="modal-icon">{{ selectedKb.icon }}</span>
            <div>
              <h2>{{ selectedKb.name }}</h2>
              <p>{{ selectedKb.description }}</p>
            </div>
          </div>
          <button class="close-btn" @click="selectedKb = null">✕</button>
        </div>
        <div class="modal-body">
          <div v-if="kbDocs.length" class="doc-list">
            <router-link
              v-for="doc in kbDocs"
              :key="doc.id"
              :to="'/docs/' + doc.id"
              class="doc-item"
              @click="selectedKb = null"
            >
              <div class="doc-title">{{ doc.title }}</div>
              <div class="doc-summary">{{ doc.summary }}</div>
              <div class="doc-meta">
                <span>{{ doc.category }}</span>
                <span>{{ formatDate(doc.updated_at) }}</span>
              </div>
            </router-link>
          </div>
          <div v-else class="empty-docs">
            <p>该知识库暂无文档</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && filteredKnowledge.length === 0" class="empty-state">
      <p>未找到匹配的知识库</p>
    </div>

    <!-- FAQ 区域 -->
    <section v-if="faqList.length > 0" class="faq-section">
      <div class="section-header">
        <h2>❓ 常见问题</h2>
        <p>快速了解知识库使用方法</p>
      </div>
      <div class="faq-list">
        <div v-for="(faq, index) in faqList" :key="index" class="faq-item">
          <div class="faq-question">
            <span class="faq-icon">Q</span>
            {{ faq.q }}
          </div>
          <div class="faq-answer">
            <span class="faq-icon">A</span>
            {{ faq.a }}
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import SkeletonLoader from '../components/SkeletonLoader.vue'
import { request } from '../composables/useRequest'

const loading = ref(true)
const searchQuery = ref('')
const allDocs = ref([])
const hotDocs = ref([])
const faqList = ref([])
const selectedKb = ref(null)
const kbDocs = ref([])

// 知识库定义（基于后端分类）
const knowledgeBases = ref([
  {
    id: 'policy-tech',
    name: '科技政策库',
    icon: '🔬',
    description: '涵盖科技创新、研发补贴、高新技术企业认定等政策文件',
    category: '科技',
    tags: ['高新认定', '研发补贴', '科技创新'],
    docCount: 0,
    updatedAt: '',
  },
  {
    id: 'policy-finance',
    name: '财税政策库',
    icon: '💰',
    description: '税收优惠、财务补贴、资金扶持等财税相关政策',
    category: '财税',
    tags: ['税收优惠', '财务补贴', '资金扶持'],
    docCount: 0,
    updatedAt: '',
  },
  {
    id: 'policy-env',
    name: '环保政策库',
    icon: '🌿',
    description: '环境保护、节能减排、绿色发展等环保政策',
    category: '环保',
    tags: ['节能减排', '环境保护', '绿色发展'],
    docCount: 0,
    updatedAt: '',
  },
  {
    id: 'policy-general',
    name: '政策法规库',
    icon: '📜',
    description: '行政法规、部门规章、地方性法规等综合政策文件',
    category: '政策法规',
    tags: ['行政法规', '部门规章', '地方法规'],
    docCount: 0,
    updatedAt: '',
  },
  {
    id: 'industry',
    name: '行业报告库',
    icon: '📊',
    description: '行业分析、市场趋势、竞品研究',
    category: '行业报告',
    tags: ['行业分析', '市场趋势', '竞品'],
    docCount: 0,
    updatedAt: '',
  },
])

const filteredKnowledge = computed(() => {
  if (!searchQuery.value.trim()) return knowledgeBases.value
  const q = searchQuery.value.trim().toLowerCase()
  return knowledgeBases.value.filter(kb =>
    kb.name.toLowerCase().includes(q) ||
    kb.description.toLowerCase().includes(q) ||
    kb.tags.some(t => t.toLowerCase().includes(q))
  )
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN')
}

function filterKnowledge() {
  // Computed 自动处理
}

async function loadDocs() {
  loading.value = true
  try {
    // 并行获取文档列表、热门文档和 FAQ
    const [docsRes, hotRes, faqRes] = await Promise.all([
      request('/api/docs', { silent: true }),
      request('/api/docs/hot', { silent: true }),
      request('/api/docs/faq', { silent: true })
    ])

    if (docsRes.ok) {
      const data = await docsRes.json()
      allDocs.value = Array.isArray(data) ? data : (data.items || [])

      // 按分类统计文档数量
      const categoryMap = {}
      allDocs.value.forEach(doc => {
        const cat = doc.category || 'other'
        categoryMap[cat] = (categoryMap[cat] || 0) + 1
      })

      // 更新知识库统计
      knowledgeBases.value.forEach(kb => {
        if (kb.category === 'help' || kb.category === 'docs') {
          kb.docCount = allDocs.value.filter(d =>
            d.category === kb.category || d.category === 'help' || d.category === 'docs'
          ).length
        } else {
          kb.docCount = categoryMap[kb.category] || 0
        }

        // 计算最近更新时间
        const kbDocs = allDocs.value.filter(d => d.category === kb.category)
        if (kbDocs.length > 0) {
          const latest = kbDocs.reduce((a, b) =>
            new Date(a.updated_at || a.created_at) > new Date(b.updated_at || b.created_at) ? a : b
          )
          kb.updatedAt = formatDate(latest.updated_at || latest.created_at)
        }
      })

      // 如果所有知识库文档数为0，给一些默认值（演示用）
      const totalDocs = knowledgeBases.value.reduce((sum, kb) => sum + kb.docCount, 0)
      if (totalDocs === 0 && allDocs.value.length > 0) {
        knowledgeBases.value[0].docCount = Math.ceil(allDocs.value.length / 3)
        knowledgeBases.value[1].docCount = Math.ceil(allDocs.value.length / 3)
        knowledgeBases.value[3].docCount = allDocs.value.length
      }
    }

    // 获取热门文档
    if (hotRes.ok) {
      hotDocs.value = await hotRes.json()
    }

    // 获取 FAQ
    if (faqRes.ok) {
      faqList.value = await faqRes.json()
    }
  } catch {}
  loading.value = false
}

function openKnowledge(kb) {
  selectedKb.value = kb

  // 过滤该知识库的文档
  if (kb.category === 'help' || kb.category === 'docs') {
    kbDocs.value = allDocs.value.filter(d =>
      d.category === kb.category || d.category === 'help' || d.category === 'docs'
    )
  } else {
    kbDocs.value = allDocs.value.filter(d => d.category === kb.category)
  }

  // 如果没匹配到文档，显示所有文档（演示用）
  if (kbDocs.value.length === 0) {
    kbDocs.value = allDocs.value.slice(0, 10)
  }
}

onMounted(loadDocs)
</script>

<style scoped>
.knowledge-page { max-width: 1000px; margin: 0 auto; }

.kb-hero {
  text-align: center; padding: 40px 0 24px;
}
.kb-hero h1 { font-size: 30px; font-weight: 800; }
.kb-hero p { color: var(--text-muted); margin-top: 6px; font-size: 15px; }

.search-bar {
  position: relative; max-width: 500px; margin: 0 auto 32px;
}
.search-bar input {
  width: 100%; padding: 12px 16px 12px 42px;
  border: 1px solid var(--border); border-radius: var(--radius);
  font-size: 14px; outline: none;
  background: var(--card);
  transition: border-color .15s, box-shadow .15s;
  min-height: 44px;
}
.search-bar input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, .1);
}
.search-icon {
  position: absolute; left: 14px; top: 50%; transform: translateY(-50%);
  font-size: 16px;
}

.kb-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  gap: 16px;
}

.kb-card {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 24px; cursor: pointer;
  transition: box-shadow .2s, transform .2s;
}
.kb-card:hover {
  box-shadow: var(--shadow-md); transform: translateY(-2px);
}

.skeleton-card { cursor: default; }
.skeleton-card:hover { box-shadow: none; transform: none; }

.kb-icon { font-size: 32px; margin-bottom: 12px; }
.kb-card h3 { font-size: 17px; font-weight: 700; margin-bottom: 6px; }
.kb-card p { font-size: 13px; color: var(--text-muted); line-height: 1.5; margin-bottom: 12px; }

.kb-stats {
  display: flex; gap: 16px; font-size: 12px; color: var(--text-muted); margin-bottom: 12px;
}

.kb-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.tag {
  font-size: 11px; background: #eef2ff; color: var(--primary);
  padding: 2px 8px; border-radius: 12px;
}

/* Modal */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 500; padding: 20px;
}
.modal-content {
  background: var(--card); border-radius: var(--radius-lg);
  width: 100%; max-width: 700px; max-height: 80vh;
  display: flex; flex-direction: column;
  box-shadow: var(--shadow-lg);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 20px 24px; border-bottom: 1px solid var(--border);
}
.modal-title { display: flex; gap: 14px; align-items: flex-start; }
.modal-icon { font-size: 28px; }
.modal-header h2 { font-size: 18px; font-weight: 700; }
.modal-header p { font-size: 13px; color: var(--text-muted); margin-top: 2px; }
.close-btn {
  background: none; border: none; font-size: 18px; cursor: pointer;
  padding: 6px 10px; border-radius: 6px; color: var(--text-muted);
  min-width: 36px; min-height: 36px;
}
.close-btn:hover { background: var(--bg); color: var(--text); }

.modal-body { overflow-y: auto; padding: 16px 24px; flex: 1; }

.doc-list { display: flex; flex-direction: column; gap: 8px; }
.doc-item {
  display: block; padding: 16px; border: 1px solid var(--border);
  border-radius: var(--radius-sm); color: inherit; text-decoration: none;
  transition: background .15s, border-color .15s;
}
.doc-item:hover { background: var(--bg); border-color: var(--primary); text-decoration: none; }
.doc-title { font-size: 15px; font-weight: 600; margin-bottom: 4px; }
.doc-summary { font-size: 13px; color: var(--text-muted); line-height: 1.5; margin-bottom: 8px; }
.doc-meta { display: flex; gap: 12px; font-size: 12px; color: var(--text-muted); }

.empty-docs { text-align: center; padding: 40px; color: var(--text-muted); }

.empty-state { text-align: center; padding: 40px; color: var(--text-muted); }

/* 热门文档样式 */
.hot-docs-section {
  margin-bottom: 48px;
}

.hot-docs-section .section-header {
  text-align: center;
  margin-bottom: 24px;
}

.hot-docs-section .section-header h2 {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
}

.hot-docs-section .section-header p {
  color: var(--text-muted);
  font-size: 14px;
}

.hot-docs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.hot-doc-card {
  display: block;
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--card);
  text-decoration: none;
  color: inherit;
  transition: all .15s;
}

.hot-doc-card:hover {
  border-color: var(--primary);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
  text-decoration: none;
}

.hot-doc-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text);
}

.hot-doc-summary {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.hot-doc-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.category-tag {
  padding: 2px 8px;
  background: var(--bg);
  border-radius: 4px;
  color: var(--text-muted);
}

.update-time {
  color: var(--text-muted);
}

/* FAQ 样式 */
.faq-section {
  margin-top: 48px;
  margin-bottom: 48px;
}

.faq-section .section-header {
  text-align: center;
  margin-bottom: 24px;
}

.faq-section .section-header h2 {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
}

.faq-section .section-header p {
  color: var(--text-muted);
  font-size: 14px;
}

.faq-list {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.faq-item {
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--card);
}

.faq-question {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text);
}

.faq-answer {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.6;
}

.faq-icon {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.faq-answer .faq-icon {
  background: var(--bg);
  color: var(--text-muted);
}

@media (max-width: 768px) {
  .kb-grid { grid-template-columns: 1fr; }
}
@media (max-width: 480px) {
  .kb-hero h1 { font-size: 24px; }
  .modal-content { max-height: 90vh; }
}
</style>

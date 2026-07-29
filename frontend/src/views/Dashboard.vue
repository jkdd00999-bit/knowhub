<template>
  <div class="dashboard">
    <section class="welcome">
      <div class="welcome-text">
        <h1>你好，{{ username }} 👋</h1>
        <p>欢迎回到知智 — 你的企业级智能知识助手</p>
      </div>
    </section>

    <!-- 统计卡片 -->
    <section class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon blue">💬</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.conversations }}</div>
          <div class="stat-label">对话记录</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon green">📚</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.knowledge }}</div>
          <div class="stat-label">知识库</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon purple">📄</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.files }}</div>
          <div class="stat-label">已上传文档</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon orange">🧠</div>
        <div class="stat-info">
          <div class="stat-value">AI</div>
          <div class="stat-label">智能记忆</div>
        </div>
      </div>
    </section>

    <!-- 快速操作 -->
    <section class="section">
      <h2>快速操作</h2>
      <div class="actions-grid" style="grid-template-columns: repeat(3, 1fr);">
        <a href="#" class="action-card" @click.prevent="openAiAssistant">
          <div class="action-icon">💬</div>
          <h3>开始对话</h3>
          <p>向 AI 助手提问，获取智能回答</p>
        </a>
        <router-link to="/knowledge" class="action-card">
          <div class="action-icon">📚</div>
          <h3>浏览知识库</h3>
          <p>探索已有的知识分类和文档</p>
        </router-link>
        <router-link to="/docs" class="action-card">
          <div class="action-icon">📖</div>
          <h3>查阅文档</h3>
          <p>查看使用指南和技术文档</p>
        </router-link>
      </div>
    </section>

    <!-- 最近对话 -->
    <section class="section">
      <div class="section-header">
        <h2>最近对话</h2>
        <router-link to="/conversations" class="view-all">查看全部 →</router-link>
      </div>
      <div v-if="recentConversations.length" class="conversation-list">
        <router-link
          v-for="conv in recentConversations"
          :key="conv.id"
          :to="'/conversations?open=' + conv.id"
          class="conv-item"
        >
          <div class="conv-icon">💬</div>
          <div class="conv-info">
            <div class="conv-title">{{ conv.title || '新对话' }}</div>
            <div class="conv-meta">{{ formatDate(conv.updated_at || conv.created_at) }} · {{ conv.message_count || 0 }} 条消息</div>
          </div>
          <div class="conv-arrow">→</div>
        </router-link>
      </div>
      <div v-else-if="!statsLoading" class="empty-hint">
        <p>还没有对话记录</p>
        <router-link to="/conversations" class="btn-primary">开始第一次对话</router-link>
      </div>
      <div v-else class="loading-skeleton">
        <div v-for="n in 3" :key="n" class="skeleton-item">
          <SkeletonLoader width="100%" height="16px" />
        </div>
      </div>
    </section>

    <!-- 已上传文件 -->
    <section class="section">
      <div class="section-header">
        <h2>我的文档</h2>
      </div>
      <div v-if="files.length" class="files-list">
        <div v-for="file in files" :key="file.id" class="file-item">
          <div class="file-icon">📄</div>
          <div class="file-info">
            <div class="file-name">{{ file.filename }}</div>
            <div class="file-meta">{{ file.chunk_count || 0 }} 个文本块</div>
          </div>
        </div>
      </div>
      <div v-else-if="!statsLoading" class="empty-hint">
        <p>还没有上传文档</p>
      </div>
    </section>

    <!-- 个人信息 -->
    <section class="section">
      <h2>账户信息</h2>
      <div class="profile-card">
        <div class="profile-row">
          <span class="profile-label">用户名</span>
          <span class="profile-value">{{ username }}</span>
        </div>
        <div class="profile-row">
          <span class="profile-label">用户ID</span>
          <span class="profile-value">{{ userId }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import SkeletonLoader from '../components/SkeletonLoader.vue'
import { formatDate } from '../utils/date.js'
import { getAuthHeaders } from '../utils/auth.js'
import { request } from '../composables/useRequest'

const username = ref(localStorage.getItem('username') || '')
const userId = ref(localStorage.getItem('userId') || '')

const statsLoading = ref(true)
const stats = ref({
  conversations: 0,
  knowledge: 0,
  files: 0,
})
const recentConversations = ref([])
const files = ref([])

function openAiAssistant() {
  // 触发 AI 助手悬浮窗打开
  const event = new CustomEvent('open-ai-assistant')
  window.dispatchEvent(event)
}

async function loadStats() {
  statsLoading.value = true
  try {
    const headers = getAuthHeaders()

    const [convRes, filesRes] = await Promise.all([
      request('/api/conversations', { headers, silent: true }),
      request('/api/files', { headers, silent: true }),
    ])

    if (convRes.ok) {
      const convData = await convRes.json()
      const convs = convData.data || []
      stats.value.conversations = convs.length
      recentConversations.value = convs.slice(0, 5)
    }

    if (filesRes.ok) {
      const filesData = await filesRes.json()
      const fileList = filesData.data || []
      stats.value.files = fileList.length
      files.value = fileList.slice(0, 5)
    }
  } catch (e) {
    console.error('Dashboard load error:', e)
  }
  statsLoading.value = false
}

onMounted(loadStats)
</script>

<style scoped>
.dashboard { max-width: 900px; margin: 0 auto; }

.welcome {
  margin-bottom: 32px;
}
.welcome h1 {
  font-size: 28px; font-weight: 800;
}
.welcome p {
  color: var(--text-muted); margin-top: 4px; font-size: 15px;
}

.stats-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
  margin-bottom: 36px;
}
.stat-card {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 20px; display: flex; align-items: center; gap: 14px;
  transition: box-shadow .2s;
}
.stat-card:hover { box-shadow: var(--shadow-md); }
.stat-icon {
  width: 44px; height: 44px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
}
.stat-icon.blue { background: #eef2ff; }
.stat-icon.green { background: #ecfdf5; }
.stat-icon.purple { background: #f5f3ff; }
.stat-icon.orange { background: #fff7ed; }
.stat-value { font-size: 24px; font-weight: 800; }
.stat-label { font-size: 13px; color: var(--text-muted); }

.section { margin-bottom: 36px; }
.section h2 { font-size: 20px; font-weight: 700; margin-bottom: 16px; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.section-header h2 { margin-bottom: 0; }
.view-all { font-size: 14px; color: var(--primary); font-weight: 500; }
.view-all:hover { text-decoration: none; }

.actions-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
}
.action-card {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 24px 20px; text-align: center;
  transition: box-shadow .2s, transform .2s;
  color: inherit; text-decoration: none; display: block;
}
.action-card:hover {
  box-shadow: var(--shadow-md); transform: translateY(-2px);
  text-decoration: none;
}
.action-icon { font-size: 28px; margin-bottom: 12px; }
.action-card h3 { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
.action-card p { font-size: 13px; color: var(--text-muted); line-height: 1.5; }

.conversation-list { display: flex; flex-direction: column; gap: 8px; }
.conv-item {
  display: flex; align-items: center; gap: 14px;
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 16px 20px;
  transition: box-shadow .15s;
  color: inherit; text-decoration: none;
}
.conv-item:hover { box-shadow: var(--shadow); text-decoration: none; }
.conv-icon { font-size: 20px; }
.conv-info { flex: 1; }
.conv-title { font-size: 14px; font-weight: 600; }
.conv-meta { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.conv-arrow { color: var(--text-muted); font-size: 14px; }

.files-list { display: flex; flex-direction: column; gap: 8px; }
.file-item {
  display: flex; align-items: center; gap: 12px;
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 14px 18px;
}
.file-icon { font-size: 18px; }
.file-info { flex: 1; }
.file-name { font-size: 14px; font-weight: 600; }
.file-meta { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

.empty-hint {
  text-align: center; padding: 32px; color: var(--text-muted);
  background: var(--card); border: 1px dashed var(--border); border-radius: var(--radius);
}
.empty-hint p { margin-bottom: 16px; }

.loading-skeleton { display: flex; flex-direction: column; gap: 8px; }
.skeleton-item {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 16px 20px;
}

.profile-card {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 4px 0;
}
.profile-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
}
.profile-row:last-child { border-bottom: none; }
.profile-label { font-size: 14px; color: var(--text-muted); }
.profile-value { font-size: 14px; font-weight: 600; }

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .actions-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
  .stats-grid { grid-template-columns: 1fr; }
  .actions-grid { grid-template-columns: 1fr; }
  .welcome h1 { font-size: 22px; }
}
</style>

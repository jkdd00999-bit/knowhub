<template>
  <div class="conversations-page">
    <div class="page-header">
      <h1>💬 对话历史</h1>
      <p>查看你与 AI 助手的历史对话记录</p>
    </div>

    <!-- 对话列表 -->
    <div v-if="loading" class="loading-state">
      <div v-for="n in 5" :key="n" class="skeleton-item">
        <SkeletonLoader width="60%" height="16px" />
        <SkeletonLoader width="30%" height="12px" style="margin-top:8px" />
      </div>
    </div>

    <div v-else-if="conversations.length" class="conv-list">
      <div
        v-for="conv in conversations"
        :key="conv.id"
        class="conv-card"
        :class="{ active: selectedConv?.id === conv.id }"
        @click="openConversation(conv)"
      >
        <div class="conv-card-header">
          <div class="conv-title">{{ conv.title || '新对话' }}</div>
          <button class="delete-btn" @click.stop="deleteConversation(conv.id)" title="删除对话">🗑️</button>
        </div>
        <div class="conv-meta">
          <span>{{ formatDate(conv.updated_at || conv.created_at) }}</span>
          <span class="msg-count">{{ conv.message_count || 0 }} 条消息</span>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <div class="empty-icon">💬</div>
      <h2>还没有对话记录</h2>
      <p>点击右下角的 AI 助手按钮开始你的第一次对话吧</p>
    </div>

    <!-- 对话详情弹窗 -->
    <div v-if="selectedConv" class="modal-overlay" @click.self="selectedConv = null">
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ selectedConv.title || '对话详情' }}</h2>
          <button class="close-btn" @click="selectedConv = null">✕</button>
        </div>
        <div class="modal-body">
          <div v-if="detailLoading" class="detail-loading">加载中...</div>
          <div v-else class="messages-list">
            <div
              v-for="(msg, idx) in detailMessages"
              :key="idx"
              class="message"
              :class="msg.role"
            >
              <div class="msg-role">{{ msg.role === 'user' ? '你' : 'AI 助手' }}</div>
              <div class="msg-content" v-html="renderMarkdown(msg.content)"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import SkeletonLoader from '../components/SkeletonLoader.vue'
import { marked } from 'marked'

const loading = ref(true)
const detailLoading = ref(false)
const conversations = ref([])
const selectedConv = ref(null)
const detailMessages = ref([])

marked.setOptions({
  breaks: true,
  gfm: true,
})

function renderMarkdown(text) {
  if (!text) return ''
  return marked.parse(text)
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + ' 分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + ' 小时前'
  if (diff < 604800000) return Math.floor(diff / 86400000) + ' 天前'
  return d.toLocaleDateString('zh-CN')
}

function getAuthHeaders() {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function loadConversations() {
  loading.value = true
  try {
    const res = await fetch('/api/conversations', {
      headers: getAuthHeaders(),
    })
    if (res.ok) {
      const data = await res.json()
      conversations.value = data.data || []
    }
  } catch {}
  loading.value = false
}

async function openConversation(conv) {
  selectedConv.value = conv
  detailLoading.value = true
  detailMessages.value = []

  try {
    const res = await fetch(`/api/conversations/${conv.id}`, {
      headers: getAuthHeaders(),
    })
    if (res.ok) {
      const data = await res.json()
      const convData = data.data
      detailMessages.value = Array.isArray(convData.messages) ? convData.messages : []
    }
  } catch {}
  detailLoading.value = false
}

async function deleteConversation(convId) {
  if (!confirm('确定要删除这个对话记录吗？')) return

  try {
    const res = await fetch(`/api/conversations/${convId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    })
    if (res.ok) {
      conversations.value = conversations.value.filter(c => c.id !== convId)
      if (selectedConv.value?.id === convId) {
        selectedConv.value = null
      }
    }
  } catch {}
}

onMounted(loadConversations)
</script>

<style scoped>
.conversations-page { max-width: 800px; margin: 0 auto; }

.page-header {
  margin-bottom: 28px;
}
.page-header h1 { font-size: 26px; font-weight: 800; }
.page-header p { color: var(--text-muted); margin-top: 4px; font-size: 14px; }

.loading-state { display: flex; flex-direction: column; gap: 12px; }
.skeleton-item {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 20px;
}

.conv-list { display: flex; flex-direction: column; gap: 10px; }
.conv-card {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 18px 20px; cursor: pointer;
  transition: box-shadow .15s, border-color .15s;
}
.conv-card:hover { box-shadow: var(--shadow-md); border-color: var(--primary); }
.conv-card.active { border-color: var(--primary); box-shadow: 0 0 0 2px rgba(79, 70, 229, .15); }

.conv-card-header { display: flex; justify-content: space-between; align-items: flex-start; }
.conv-title { font-size: 15px; font-weight: 600; flex: 1; }
.delete-btn {
  background: none; border: none; cursor: pointer; font-size: 14px;
  padding: 4px 8px; border-radius: 6px; opacity: 0;
  transition: opacity .15s, background .15s;
}
.conv-card:hover .delete-btn { opacity: 1; }
.delete-btn:hover { background: #fef2f2; }

.conv-meta {
  display: flex; gap: 16px; margin-top: 6px;
  font-size: 12px; color: var(--text-muted);
}
.msg-count { color: var(--primary); font-weight: 500; }

.empty-state {
  text-align: center; padding: 60px 20px;
  background: var(--card); border: 1px dashed var(--border); border-radius: var(--radius);
}
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-state h2 { font-size: 20px; margin-bottom: 8px; }
.empty-state p { color: var(--text-muted); font-size: 14px; }

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
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 24px; border-bottom: 1px solid var(--border);
}
.modal-header h2 { font-size: 18px; font-weight: 700; }
.close-btn {
  background: none; border: none; font-size: 18px; cursor: pointer;
  padding: 6px 10px; border-radius: 6px; color: var(--text-muted);
  min-width: 36px; min-height: 36px;
}
.close-btn:hover { background: var(--bg); color: var(--text); }

.modal-body {
  overflow-y: auto; padding: 20px 24px; flex: 1;
}
.detail-loading { text-align: center; color: var(--text-muted); padding: 40px; }

.messages-list { display: flex; flex-direction: column; gap: 16px; }
.message {
  padding: 14px 18px; border-radius: var(--radius); max-width: 85%;
}
.message.user {
  background: var(--primary); color: #fff;
  margin-left: auto; border-bottom-right-radius: 4px;
}
.message.assistant {
  background: var(--bg); border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
}
.msg-role { font-size: 12px; font-weight: 600; margin-bottom: 6px; opacity: .7; }
.msg-content { font-size: 14px; line-height: 1.7; }
.msg-content :deep(p) { margin: 0; }
.msg-content :deep(code) { background: rgba(0,0,0,.06); padding: 1px 4px; border-radius: 3px; font-size: 13px; }
.message.user .msg-content :deep(code) { background: rgba(255,255,255,.15); }
.msg-content :deep(pre) { background: var(--code-bg); color: var(--code-fg); padding: 12px; border-radius: 6px; overflow-x: auto; margin: 8px 0; }

@media (max-width: 480px) {
  .modal-content { max-height: 90vh; }
  .message { max-width: 95%; }
}
</style>

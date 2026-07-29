<template>
  <div class="ai-widget" :class="{ open: isOpen }">
    <!-- 悬浮按钮 -->
    <button v-if="!isOpen" class="ai-fab" @click="isOpen = true" title="AI 助手">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
    </button>

    <!-- 对话框 -->
    <div v-else class="ai-panel">
      <div class="ai-panel__header">
        <span class="ai-panel__title">AI 助手</span>
        <div class="ai-panel__actions">
          <button class="ai-btn-icon" @click="clearChat" title="清空">&#8635;</button>
          <button class="ai-btn-icon" @click="isOpen = false" title="关闭">&times;</button>
        </div>
      </div>

      <div class="ai-panel__body" ref="msgList">
        <div v-for="(m, i) in messages" :key="m.id || i" :class="['msg', m.role]">
          <div class="msg-bubble" v-html="renderMarkdown(m.content)"></div>
          <div v-if="m.references?.length" class="msg-refs">
            参考：<a v-for="ref in m.references" :href="'/docs/' + ref.doc_id" @click.prevent="isOpen = false; $router.push('/docs/' + ref.doc_id)">{{ ref.title }}</a>
          </div>
        </div>
        <div v-if="loading" class="msg assistant"><span class="typing">思考中...</span></div>
      </div>

      <div class="ai-panel__input">
        <textarea
          v-model="input"
          placeholder="输入你的问题，如「怎么配置 Webhook？」"
          rows="1"
          maxlength="2000"
          @keydown.enter.exact.prevent="send"
          @input="autoResize"
          ref="inputEl"
        ></textarea>
        <button class="ai-send-btn" @click="send" :disabled="!input.trim() || loading">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { request } from '../composables/useRequest'

marked.setOptions({ breaks: true })

const isOpen = ref(false)
const input = ref('')
const messages = ref([])
const loading = ref(false)
const msgList = ref(null)
const inputEl = ref(null)
const conversationId = ref(null)
let msgIdCounter = 0

// 监听外部事件打开面板
function handleOpenEvent() { isOpen.value = true }
onMounted(() => window.addEventListener('open-ai-assistant', handleOpenEvent))
onUnmounted(() => window.removeEventListener('open-ai-assistant', handleOpenEvent))

function renderMarkdown(text) {
  const html = marked(text || '')
  return DOMPurify.sanitize(html)
}

function scrollBottom() {
  nextTick(() => {
    if (msgList.value) msgList.value.scrollTop = msgList.value.scrollHeight
  })
}

function autoResize() {
  const el = inputEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return
  messages.value.push({ id: ++msgIdCounter, role: 'user', content: text })
  input.value = ''
  loading.value = true
  scrollBottom()

  try {
    const token = localStorage.getItem('token')
    const headers = { 'Content-Type': 'application/json' }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const resp = await request('/api/chat', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        message: text,
        conversation_id: conversationId.value,
      }),
      silent: true,
      timeout: 180000,  // AI 对话需要较长超时（180秒）
    })

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`)
    }

    const data = await resp.json()
    // 保存会话ID，后续消息复用同一会话
    if (data.conversation_id) {
      conversationId.value = data.conversation_id
    }
    messages.value.push({
      id: ++msgIdCounter,
      role: 'assistant',
      content: data.answer || '抱歉，我暂时无法回答这个问题。',
      references: data.references || [],
    })
  } catch (e) {
    console.error('Chat request failed:', e)
    messages.value.push({ id: ++msgIdCounter, role: 'assistant', content: `抱歉，请求失败：${e.message || e}。请检查后端是否运行中。` })
  } finally {
    loading.value = false
    scrollBottom()
  }
}

function clearChat() {
  messages.value = []
}

watch(isOpen, (val) => {
  if (val) {
    nextTick(() => inputEl.value?.focus())
    if (messages.value.length === 0) {
      messages.value.push({
        id: ++msgIdCounter,
        role: 'assistant',
        content: '你好！我是 AI 助手，可以帮你查找文档、解答产品使用问题。试着问我吧～',
      })
    }
    scrollBottom()
  }
})
</script>

<style scoped>
.ai-widget { position: fixed; bottom: 24px; right: 24px; z-index: 999; }
.ai-fab {
  width: 56px; height: 56px; border-radius: 50%; border: none;
  background: var(--primary); color: #fff; cursor: pointer;
  box-shadow: 0 4px 16px rgba(79,70,229,.4);
  display: flex; align-items: center; justify-content: center;
  transition: transform .15s, box-shadow .15s;
}
.ai-fab:hover { transform: scale(1.06); box-shadow: 0 6px 20px rgba(79,70,229,.5); }

.ai-panel {
  width: 380px; height: 560px; background: var(--card); border-radius: 16px;
  box-shadow: 0 8px 40px rgba(0,0,0,.12); display: flex; flex-direction: column;
  overflow: hidden; border: 1px solid var(--border);
}

.ai-panel__header {
  padding: 14px 18px; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
  flex-shrink: 0;
}
.ai-panel__title { font-weight: 600; font-size: 15px; }
.ai-btn-icon {
  background: none; border: none; font-size: 20px; color: var(--text-muted);
  cursor: pointer; padding: 2px 6px; border-radius: 6px;
  min-width: 36px; min-height: 36px;
  display: inline-flex; align-items: center; justify-content: center;
}
.ai-btn-icon:hover { background: var(--bg); }

.ai-panel__body {
  flex: 1; overflow-y: auto; padding: 16px;
  display: flex; flex-direction: column; gap: 12px;
  scroll-behavior: smooth;
}

.msg { max-width: 85%; animation: msgIn .25s ease-out; }
.msg.user { align-self: flex-end; }
.msg.assistant { align-self: flex-start; }

@keyframes msgIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.msg-bubble {
  padding: 10px 14px; border-radius: 14px; font-size: 14px; line-height: 1.55;
  white-space: pre-wrap; word-break: break-word;
}
.msg-bubble :deep(p) { margin: 0; }
.msg-bubble :deep(code) {
  background: rgba(0,0,0,.06); padding: 2px 6px; border-radius: 4px; font-size: 13px;
}
.msg.user .msg-bubble { background: var(--primary); color: #fff; border-bottom-right-radius: 4px; }
.msg.assistant .msg-bubble { background: var(--bg); color: var(--text); border-bottom-left-radius: 4px; }

.msg-refs { margin-top: 4px; font-size: 12px; color: var(--text-muted); display: flex; gap: 6px; flex-wrap: wrap; }
.msg-refs a { color: var(--primary); font-size: 12px; }

.typing { color: var(--text-muted); font-size: 14px; }

.ai-panel__input {
  padding: 12px 16px; border-top: 1px solid var(--border);
  display: flex; gap: 8px; align-items: flex-end;
  flex-shrink: 0;
  background: var(--card);
}
.ai-panel__input textarea {
  flex: 1; border: 1px solid var(--border); border-radius: 10px;
  padding: 10px 14px; font-size: 14px; resize: none; outline: none;
  font-family: inherit; max-height: 120px; min-height: 40px;
}
.ai-panel__input textarea:focus { border-color: var(--primary); }
.ai-send-btn {
  width: 40px; height: 40px; border-radius: 10px; border: none;
  background: var(--primary); color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; transition: opacity .15s;
}
.ai-send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.ai-send-btn:hover:not(:disabled) { background: var(--primary-light); }

/* Mobile: full-screen panel */
@media (max-width: 480px) {
  .ai-widget { bottom: 0; right: 0; }
  .ai-widget.open {
    position: fixed; inset: 0; z-index: 1001;
  }
  .ai-panel {
    width: 100%; height: 100%; border-radius: 0;
    max-height: 100vh; max-height: 100dvh;
  }
  .ai-fab {
    width: 50px; height: 50px;
    bottom: 16px; right: 16px;
    position: fixed;
  }
}
</style>


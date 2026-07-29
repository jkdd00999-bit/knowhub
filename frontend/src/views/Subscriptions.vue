<template>
  <div class="subscriptions-page">
    <div class="page-header">
      <h1>📬 智能订阅</h1>
      <p>订阅感兴趣的领域，AI 将定时检索最新信息并推送到你的邮箱</p>
    </div>

    <!-- 邮箱未设置提醒 -->
    <div v-if="!userEmail" class="email-banner">
      <div class="banner-content">
        <span class="banner-icon">⚠️</span>
        <span>你还没有设置邮箱，请先设置后才能创建订阅</span>
      </div>
      <div class="banner-input">
        <input
          v-model="newEmail"
          type="email"
          placeholder="请输入邮箱地址"
          @keyup.enter="saveEmail"
        />
        <button @click="saveEmail" :disabled="!newEmail || !isValidEmail">保存</button>
      </div>
    </div>

    <!-- 创建订阅表单 -->
    <div class="create-section" v-if="userEmail">
      <h2>创建新订阅</h2>
      <div class="create-form">
        <input
          v-model="newTopic"
          type="text"
          placeholder="输入订阅主题，如：最新环保政策、AI 发展动态"
          @keyup.enter="createSubscription"
          :disabled="creating"
        />
        <select v-model="newFrequency">
          <option value="daily">每天推送</option>
          <option value="weekly">每周推送</option>
        </select>
        <button @click="createSubscription" :disabled="!newTopic.trim() || creating">
          {{ creating ? '创建中...' : '创建订阅' }}
        </button>
      </div>
    </div>

    <!-- 订阅列表 -->
    <div v-if="loading" class="loading-state">
      <div v-for="n in 3" :key="n" class="skeleton-item">
        <SkeletonLoader width="50%" height="16px" />
        <SkeletonLoader width="30%" height="12px" style="margin-top:8px" />
      </div>
    </div>

    <div v-else-if="subscriptions.length" class="sub-list">
      <h2>我的订阅 ({{ subscriptions.length }})</h2>
      <div
        v-for="sub in subscriptions"
        :key="sub.id"
        class="sub-card"
      >
        <div class="sub-header">
          <div class="sub-topic">
            <span class="topic-icon">{{ sub.frequency === 'daily' ? '📅' : '📆' }}</span>
            <span>{{ sub.topic }}</span>
          </div>
          <button class="cancel-btn" @click="cancelSubscription(sub.id)" title="取消订阅">取消</button>
        </div>
        <div class="sub-meta">
          <span class="freq-tag">{{ sub.frequency === 'daily' ? '每天' : '每周' }}</span>
          <span>📧 {{ sub.email }}</span>
          <span v-if="sub.last_run">上次推送: {{ formatDate(sub.last_run) }}</span>
          <span v-else class="no-run">尚未推送</span>
        </div>
        <div class="sub-time">创建于 {{ formatDate(sub.created_at) }}</div>
      </div>
    </div>

    <div v-else-if="!loading && userEmail" class="empty-state">
      <div class="empty-icon">📭</div>
      <h2>还没有订阅</h2>
      <p>在上方输入你感兴趣的领域，AI 将定时为你搜集最新信息</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import SkeletonLoader from '../components/SkeletonLoader.vue'
import { formatDate } from '../utils/date.js'
import { getAuthHeaders } from '../utils/auth.js'
import { useToast } from '../composables/useToast'
import { request } from '../composables/useRequest'

const toast = useToast()

const loading = ref(true)
const creating = ref(false)
const subscriptions = ref([])
const userEmail = ref('')
const newEmail = ref('')
const newTopic = ref('')
const newFrequency = ref('daily')

const isValidEmail = ref(true)

async function loadUserData() {
  try {
    const res = await request('/api/auth/me', {
      headers: getAuthHeaders(),
    })
    if (res.ok) {
      const data = await res.json()
      userEmail.value = data.data?.email || localStorage.getItem('email') || ''
    } else {
      // token 失效，用 localStorage 兜底
      userEmail.value = localStorage.getItem('email') || ''
    }
  } catch {
    userEmail.value = localStorage.getItem('email') || ''
  }
}

async function loadSubscriptions() {
  loading.value = true
  try {
    const res = await request('/api/subscriptions', {
      headers: getAuthHeaders(),
    })
    if (res.ok) {
      const data = await res.json()
      subscriptions.value = data.data || []
    }
  } catch (e) { console.error(e) }
  loading.value = false
}

async function saveEmail() {
  const email = newEmail.value.trim()
  if (!email) return
  // 简单邮箱验证
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    isValidEmail.value = false
    return
  }
  isValidEmail.value = true

  try {
    const res = await request('/api/auth/me', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ email }),
    })
    if (res.ok) {
      userEmail.value = email
      localStorage.setItem('email', email)
      newEmail.value = ''
    } else {
      const err = await res.json().catch(() => ({}))
      toast.error('邮箱保存失败，请重新登录后再试')
    }
  } catch (e) {
    toast.error('网络错误，邮箱保存失败')
  }
}

async function createSubscription() {
  const topic = newTopic.value.trim()
  if (!topic) return

  creating.value = true
  try {
    const res = await request('/api/subscriptions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        topic,
        frequency: newFrequency.value,
        email: userEmail.value || localStorage.getItem('email') || '',
      }),
    })
    const data = await res.json()
    if (res.ok && data.code === 200) {
      newTopic.value = ''
      await loadSubscriptions()
    } else {
      toast.error(data.message || '创建失败')
    }
  } catch {
    toast.error('创建失败，请重试')
  }
  creating.value = false
}

async function cancelSubscription(subId) {
  if (!confirm('确定要取消这个订阅吗？')) return

  try {
    const res = await request(`/api/subscriptions/${subId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    })
    if (res.ok) {
      subscriptions.value = subscriptions.value.filter(s => s.id !== subId)
    }
  } catch (e) { console.error(e) }
}

onMounted(async () => {
  await loadUserData()
  await loadSubscriptions()
})
</script>

<style scoped>
.subscriptions-page { max-width: 800px; margin: 0 auto; }

.page-header {
  margin-bottom: 28px;
}
.page-header h1 { font-size: 26px; font-weight: 800; }
.page-header p { color: var(--text-muted); margin-top: 4px; font-size: 14px; }

/* 邮箱提醒横幅 */
.email-banner {
  background: #fffbeb;
  border: 1px solid #fbbf24;
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 24px;
}
.banner-content {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 500;
  color: #92400e;
}
.banner-icon { font-size: 18px; }
.banner-input {
  display: flex;
  gap: 8px;
}
.banner-input input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
}
.banner-input input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(79, 70, 229, .15);
}
.banner-input button {
  padding: 8px 16px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
}
.banner-input button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 创建表单 */
.create-section {
  margin-bottom: 32px;
}
.create-section h2 {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 12px;
}
.create-form {
  display: flex;
  gap: 8px;
}
.create-form input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
  background: var(--card);
  outline: none;
}
.create-form input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(79, 70, 229, .15);
}
.create-form select {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
  background: var(--card);
  outline: none;
  cursor: pointer;
}
.create-form button {
  padding: 10px 20px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: var(--radius);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity .15s;
}
.create-form button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.create-form button:not(:disabled):hover {
  opacity: 0.9;
}

/* 加载态 */
.loading-state { display: flex; flex-direction: column; gap: 12px; }
.skeleton-item {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 20px;
}

/* 订阅列表 */
.sub-list h2 {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 12px;
}
.sub-list { margin-bottom: 32px; }

.sub-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 20px;
  margin-bottom: 10px;
  transition: box-shadow .15s, border-color .15s;
}
.sub-card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--primary);
}

.sub-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sub-topic {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
}
.topic-icon { font-size: 18px; }

.cancel-btn {
  background: none;
  border: 1px solid #ef4444;
  color: #ef4444;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: background .15s, color .15s;
}
.cancel-btn:hover {
  background: #ef4444;
  color: #fff;
}

.sub-meta {
  display: flex;
  gap: 16px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
  flex-wrap: wrap;
}
.freq-tag {
  background: var(--primary-light, rgba(79, 70, 229, 0.1));
  color: var(--primary);
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}
.no-run {
  color: #f59e0b;
  font-style: italic;
}

.sub-time {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 6px;
  opacity: 0.7;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: var(--card);
  border: 1px dashed var(--border);
  border-radius: var(--radius);
}
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-state h2 { font-size: 20px; margin-bottom: 8px; }
.empty-state p { color: var(--text-muted); font-size: 14px; }

@media (max-width: 768px) {
  .create-form {
    flex-direction: column;
  }
  .banner-input {
    flex-direction: column;
  }
}
</style>

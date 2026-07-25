<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <router-link to="/" class="auth-logo">
          <span class="logo-icon">知</span> 知智
        </router-link>
        <h1>创建账户</h1>
        <p>注册即可使用智能知识助手</p>
      </div>

      <form @submit.prevent="handleRegister" class="auth-form">
        <div class="form-group">
          <label for="username">用户名</label>
          <input
            id="username"
            v-model="form.username"
            type="text"
            placeholder="请输入用户名（3-20个字符）"
            required
            minlength="3"
            maxlength="20"
            autocomplete="username"
          />
        </div>

        <div class="form-group">
          <label for="password">密码</label>
          <input
            id="password"
            v-model="form.password"
            type="password"
            placeholder="请输入密码（至少6个字符）"
            required
            minlength="6"
            autocomplete="new-password"
          />
        </div>

        <div class="form-group">
          <label for="confirmPassword">确认密码</label>
          <input
            id="confirmPassword"
            v-model="form.confirmPassword"
            type="password"
            placeholder="再次输入密码"
            required
            autocomplete="new-password"
          />
        </div>

        <div class="form-error" v-if="error">{{ error }}</div>
        <div class="form-success" v-if="success">{{ success }}</div>

        <button type="submit" class="btn-submit" :disabled="loading">
          <span v-if="loading">注册中...</span>
          <span v-else>注 册</span>
        </button>
      </form>

      <div class="auth-footer">
        已有账户？ <router-link to="/login">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const success = ref('')

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
})

async function handleRegister() {
  error.value = ''
  success.value = ''

  if (form.password !== form.confirmPassword) {
    error.value = '两次密码输入不一致'
    return
  }

  if (form.password.length < 6) {
    error.value = '密码至少需要6个字符'
    return
  }

  loading.value = true

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: form.username,
        password: form.password,
      }),
    })

    const data = await res.json()

    if (data.code === 400 || data.message?.includes('已存在')) {
      throw new Error('用户名已存在')
    }

    if (!res.ok) {
      throw new Error(data.detail || data.message || '注册失败')
    }

    // 注册成功，跳转到登录页
    success.value = '注册成功！正在跳转到登录页...'
    setTimeout(() => {
      router.push('/login')
    }, 1000)
  } catch (e) {
    error.value = e.message || '注册失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: calc(100vh - 56px - 64px);
  display: flex; align-items: center; justify-content: center;
  padding: 40px 16px;
  background: linear-gradient(135deg, #f0f0ff 0%, #f8f9fb 50%, #f0fff4 100%);
}

.auth-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 40px;
  width: 100%;
  max-width: 420px;
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
}

.auth-logo {
  display: inline-flex;
  align-items: center;
  font-size: 20px;
  font-weight: 700;
  color: var(--primary);
  margin-bottom: 20px;
}
.auth-logo:hover { text-decoration: none; }

.auth-header h1 {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 6px;
}
.auth-header p {
  font-size: 14px;
  color: var(--text-muted);
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.form-group input {
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color .15s, box-shadow .15s;
  min-height: 44px;
}
.form-group input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, .1);
}

.form-error {
  background: #fef2f2;
  color: var(--error);
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
}

.form-success {
  background: #ecfdf5;
  color: var(--success);
  border: 1px solid #a7f3d0;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
}

.btn-submit {
  padding: 12px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background .15s;
  min-height: 48px;
  margin-top: 4px;
}
.btn-submit:hover { background: var(--primary-light); }
.btn-submit:disabled { opacity: .6; cursor: not-allowed; }

.auth-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: var(--text-muted);
}
.auth-footer a { color: var(--primary); font-weight: 600; }

@media (max-width: 480px) {
  .auth-card { padding: 28px 20px; }
}
</style>

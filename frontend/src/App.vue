<template>
  <div class="app-shell">
    <header class="top-nav">
      <div class="nav-inner">
        <router-link to="/" class="logo">
          <span class="logo-icon">知</span> 知智
        </router-link>

        <button class="hamburger" @click="navOpen = !navOpen" :aria-label="navOpen ? '关闭菜单' : '打开菜单'">
          <span></span><span></span><span></span>
        </button>

        <nav :class="{ open: navOpen }">
          <router-link to="/" @click="navOpen = false">首页</router-link>
          <router-link to="/knowledge" @click="navOpen = false">知识库</router-link>
          <router-link to="/documents" @click="navOpen = false">文档管理</router-link>
          <router-link to="/docs" @click="navOpen = false">文档</router-link>
        </nav>

        <div class="nav-right">
          <!-- 未登录 -->
          <template v-if="!isLoggedIn">
            <router-link to="/login" class="btn-login" @click="navOpen = false">登录</router-link>
            <router-link to="/register" class="btn-register" @click="navOpen = false">免费注册</router-link>
          </template>
          <!-- 已登录 -->
          <template v-else>
            <div class="user-menu" ref="userMenuRef">
              <button class="user-avatar-btn" @click="userMenuOpen = !userMenuOpen">
                <span class="avatar">{{ userInitial }}</span>
                <span class="username">{{ username }}</span>
                <span class="arrow">▾</span>
              </button>
              <div class="user-dropdown" v-show="userMenuOpen">
                <router-link to="/dashboard" @click="userMenuOpen = false; navOpen = false">
                  <span class="menu-icon">📊</span> 控制台
                </router-link>
                <router-link to="/conversations" @click="userMenuOpen = false; navOpen = false">
                  <span class="menu-icon">💬</span> 对话历史
                </router-link>
                <router-link to="/subscriptions" @click="userMenuOpen = false; navOpen = false">
                  <span class="menu-icon">📬</span> 智能订阅
                </router-link>
                <router-link to="/admin" v-if="userRole === 'admin'" @click="userMenuOpen = false; navOpen = false">
                  <span class="menu-icon">⚙️</span> 管理后台
                </router-link>
                <div class="divider"></div>
                <button class="menu-item logout" @click="handleLogout">
                  <span class="menu-icon">🚪</span> 退出登录
                </button>
              </div>
            </div>
          </template>
        </div>
      </div>
    </header>

    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <AiAssistant />
    <Toast ref="toastRef" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import AiAssistant from './components/AiAssistant.vue'
import Toast from './components/Toast.vue'
import { setToastRef } from './composables/useRequest'
import { toastRef as sharedToastRef } from './composables/useToastRef'

const router = useRouter()
const navOpen = ref(false)
const userMenuOpen = ref(false)
const userMenuRef = ref(null)

// 路由切换时关闭移动端导航菜单
import { watch } from 'vue'
watch(() => router.currentRoute.value.path, () => { navOpen.value = false })
const toastRef = ref(null)

// 认证状态
const token = ref(localStorage.getItem('token') || '')
const username = ref(localStorage.getItem('username') || '')
const userRole = ref(localStorage.getItem('userRole') || 'viewer')

const isLoggedIn = computed(() => !!token.value)
const userInitial = computed(() => username.value ? username.value[0].toUpperCase() : '?')

function handleLogout() {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('userRole')
  localStorage.removeItem('userId')
  token.value = ''
  username.value = ''
  userRole.value = 'viewer'
  userMenuOpen.value = false
  router.push('/')
}

// 点击外部关闭用户菜单
function handleClickOutside(e) {
  if (userMenuRef.value && !userMenuRef.value.contains(e.target)) {
    userMenuOpen.value = false
  }
}

onMounted(() => {
  if (toastRef.value) {
    setToastRef(toastRef.value)
    sharedToastRef.value = toastRef.value
  }
  document.addEventListener('click', handleClickOutside)
  // 监听 storage 变化（跨标签页同步登录状态）
  window.addEventListener('storage', handleStorageChange)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  window.removeEventListener('storage', handleStorageChange)
})

// 跨标签页同步登录状态
function handleStorageChange(e) {
  if (e.key === 'token') {
    token.value = e.newValue || ''
    username.value = localStorage.getItem('username') || ''
    userRole.value = localStorage.getItem('userRole') || 'viewer'
  }
}
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --primary: #4F46E5;
  --primary-light: #6366f1;
  --primary-dark: #4338ca;
  --success: #10B981;
  --success-light: #34d399;
  --error: #ef4444;
  --warning: #f59e0b;
  --bg: #f8f9fb;
  --card: #ffffff;
  --text: #1e293b;
  --text-muted: #64748b;
  --border: #e2e8f0;
  --shadow: 0 1px 3px rgba(0,0,0,.08);
  --shadow-md: 0 4px 12px rgba(0,0,0,.08);
  --shadow-lg: 0 8px 40px rgba(0,0,0,.12);
  --radius: 10px;
  --radius-sm: 6px;
  --radius-lg: 16px;
  --code-bg: #1e293b;
  --code-fg: #e2e8f0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}

a { color: var(--primary); text-decoration: none; }
a:hover { text-decoration: underline; }

.app-shell { min-height: 100vh; display: flex; flex-direction: column; }

/* Top Navigation */
.top-nav {
  background: var(--card);
  border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 100;
  backdrop-filter: blur(8px);
}
.nav-inner {
  max-width: 1200px; margin: 0 auto; padding: 0 24px;
  height: 56px; display: flex; align-items: center; gap: 32px;
}
.logo { font-size: 18px; font-weight: 700; color: var(--primary); }
.logo:hover { text-decoration: none; }
.logo-icon {
  display: inline-block; background: var(--primary); color: #fff;
  width: 28px; height: 28px; border-radius: 6px; text-align: center; line-height: 28px; margin-right: 6px;
  font-size: 14px; font-weight: 800;
}

nav { display: flex; gap: 20px; }
nav a {
  color: var(--text-muted); font-size: 14px; font-weight: 500;
  transition: color .15s; padding: 4px 0;
}
nav a:hover, nav a.router-link-active { color: var(--primary); text-decoration: none; }

/* Nav Right */
.nav-right {
  margin-left: auto;
  display: flex; align-items: center; gap: 12px;
}
.btn-login {
  font-size: 14px; font-weight: 500; color: var(--text-muted);
  padding: 6px 14px; border-radius: 6px;
  transition: color .15s, background .15s;
  min-height: 36px; display: inline-flex; align-items: center;
}
.btn-login:hover { color: var(--primary); background: #f0f0ff; text-decoration: none; }

.btn-register {
  font-size: 14px; font-weight: 600; color: #fff;
  background: var(--primary); padding: 6px 16px; border-radius: 6px;
  transition: background .15s;
  min-height: 36px; display: inline-flex; align-items: center;
}
.btn-register:hover { background: var(--primary-light); text-decoration: none; }

/* User Menu */
.user-menu { position: relative; }
.user-avatar-btn {
  display: flex; align-items: center; gap: 8px;
  background: none; border: 1px solid var(--border); border-radius: 8px;
  padding: 4px 10px 4px 4px; cursor: pointer;
  transition: background .15s, border-color .15s;
  min-height: 40px;
}
.user-avatar-btn:hover { background: var(--bg); border-color: var(--primary); }
.avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--primary); color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700;
}
.username { font-size: 13px; font-weight: 500; color: var(--text); max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.arrow { font-size: 10px; color: var(--text-muted); }

.user-dropdown {
  position: absolute; top: calc(100% + 6px); right: 0;
  background: var(--card); border: 1px solid var(--border);
  border-radius: var(--radius); box-shadow: var(--shadow-lg);
  min-width: 180px; padding: 6px 0;
  z-index: 200;
}
.user-dropdown a, .user-dropdown button {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 16px; font-size: 14px; color: var(--text);
  width: 100%; border: none; background: none; cursor: pointer;
  text-align: left; transition: background .1s;
  min-height: 40px;
}
.user-dropdown a:hover, .user-dropdown button:hover { background: var(--bg); text-decoration: none; }
.user-dropdown .menu-icon { font-size: 15px; }
.user-dropdown .divider { height: 1px; background: var(--border); margin: 4px 0; }
.user-dropdown .logout { color: var(--error); }

/* Hamburger (Mobile) */
.hamburger {
  display: none;
  flex-direction: column;
  gap: 5px;
  background: none; border: none;
  cursor: pointer;
  padding: 10px;
  margin-left: auto;
  min-width: 44px; min-height: 44px;
  align-items: center; justify-content: center;
}
.hamburger span {
  display: block;
  width: 22px; height: 2px;
  background: var(--text);
  border-radius: 2px;
  transition: all .25s;
}

/* Page Transition */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity .2s ease, transform .2s ease;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Main Content */
.main-content { flex: 1; max-width: 1200px; width: 100%; margin: 0 auto; padding: 32px 24px; }

/* Shared Utility Classes */
.btn-primary {
  padding: 8px 18px; background: var(--primary); color: #fff; border: none; border-radius: 8px;
  cursor: pointer; font-size: 14px; font-weight: 600;
  min-height: 44px; min-width: 44px;
  display: inline-flex; align-items: center; justify-content: center;
  transition: background .15s;
}
.btn-primary:hover { background: var(--primary-light); }
.btn-primary:disabled { opacity: .4; cursor: not-allowed; }

.btn-cancel {
  padding: 8px 18px; background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
  cursor: pointer; font-size: 14px;
  min-height: 44px; min-width: 44px;
  display: inline-flex; align-items: center; justify-content: center;
}
.btn-cancel:hover { background: var(--border); }

/* Global Code Block Copy Button */
pre {
  position: relative;
}
pre .copy-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.18);
  color: rgba(255,255,255,.7);
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all .15s;
  min-width: 44px;
  min-height: 30px;
}
pre .copy-btn:hover {
  background: rgba(255,255,255,.2);
  color: #fff;
}
pre .copy-btn.copied {
  background: var(--success);
  border-color: var(--success);
  color: #fff;
}

/* Code Highlighting Theme (One Dark / GitHub Dark inspired) */
pre code.hljs,
.hljs {
  color: #e2e8f0;
}
.hljs-keyword    { color: #c792ea; }
.hljs-string     { color: #c3e88d; }
.hljs-number     { color: #f78c6c; }
.hljs-comment    { color: #546e7a; font-style: italic; }
.hljs-function   { color: #82aaff; }
.hljs-title      { color: #82aaff; }
.hljs-built_in   { color: #ffcb6b; }
.hljs-type       { color: #ffcb6b; }
.hljs-literal    { color: #f78c6c; }
.hljs-attr       { color: #ffcb6b; }
.hljs-selector   { color: #c792ea; }
.hljs-tag        { color: #f07178; }
.hljs-name       { color: #f07178; }
.hljs-attribute  { color: #ffcb6b; }
.hljs-meta       { color: #89ddff; }
.hljs-params     { color: #eeffff; }
.hljs-property   { color: #82aaff; }
.hljs-punctuation { color: #89ddff; }
.hljs-operator   { color: #89ddff; }
.hljs-regexp     { color: #c3e88d; }
.hljs-variable   { color: #eeffff; }

/* Responsive */
@media (max-width: 768px) {
  .hamburger { display: flex; }

  .nav-right {
    margin-left: 0;
  }

  nav {
    display: none;
    position: absolute;
    top: 56px;
    left: 0;
    right: 0;
    background: var(--card);
    flex-direction: column;
    gap: 0;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    box-shadow: var(--shadow-md);
  }
  nav.open { display: flex; }
  nav a {
    padding: 14px 24px;
    font-size: 15px;
    border-radius: 0;
    min-height: 44px;
    display: flex;
    align-items: center;
  }
  nav a:hover { background: var(--bg); }

  .main-content { padding: 20px 16px; }
}
@media (max-width: 480px) {
  .nav-inner { padding: 0 12px; }
  .main-content { padding: 16px 12px; }
  .btn-primary, .btn-cancel { width: 100%; justify-content: center; }
  .username { display: none; }
}
</style>

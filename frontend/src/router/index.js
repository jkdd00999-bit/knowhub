import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Home', component: () => import('../views/Home.vue') },
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { guest: true } },
  { path: '/register', name: 'Register', component: () => import('../views/Register.vue'), meta: { guest: true } },
  { path: '/dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { requiresAuth: true } },
  { path: '/conversations', name: 'Conversations', component: () => import('../views/Conversations.vue'), meta: { requiresAuth: true } },
  { path: '/subscriptions', name: 'Subscriptions', component: () => import('../views/Subscriptions.vue'), meta: { requiresAuth: true } },
  { path: '/knowledge', name: 'Knowledge', component: () => import('../views/Knowledge.vue') },
  { path: '/documents', name: 'Documents', component: () => import('../views/Documents.vue'), meta: { requiresAuth: true } },
  { path: '/docs/:id?', name: 'Docs', component: () => import('../views/Docs.vue') },
  { path: '/admin', name: 'Admin', component: () => import('../views/Admin.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('../views/NotFound.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const userRole = localStorage.getItem('userRole')

  if (to.meta.requiresAuth && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.meta.guest && token) {
    next({ name: 'Dashboard' })
  } else if (to.meta.requiresAdmin && userRole !== 'admin') {
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

export default router

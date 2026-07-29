/**
 * Unified fetch wrapper with timeout, error handling and toast integration.
 */
let toastRef = null

export function setToastRef(ref) { toastRef = ref }

const DEFAULT_TIMEOUT = 15000

function toast() {
  if (!toastRef) return { error: () => {}, success: () => {}, info: () => {} }
  return {
    error: (msg) => toastRef.add?.('error', msg),
    success: (msg) => toastRef.add?.('success', msg),
    info: (msg) => toastRef.add?.('info', msg),
  }
}

/**
 * 全局 401 处理：清除登录状态并跳转到登录页
 */
function handleUnauthorized() {
  // 清除所有登录相关信息
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('userRole')
  localStorage.removeItem('userId')
  localStorage.removeItem('email')

  // 避免在登录页重复跳转（项目使用 history 模式路由）
  if (window.location.pathname !== '/login') {
    toast().error('登录已过期，请重新登录')
    // 跳转到登录页
    window.location.href = '/login'
  }
}

/**
 * Fetch with timeout. Throws on timeout or network error.
 * @param {string} url
 * @param {object} options - standard fetch options plus { timeout?: number, silent?: boolean }
 * @returns {Promise<Response>}
 */
export async function request(url, options = {}) {
  const { timeout = DEFAULT_TIMEOUT, silent = false, ...fetchOptions } = options

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)

  try {
    const res = await fetch(url, { ...fetchOptions, signal: controller.signal })

    // 全局 401 拦截：Token 过期或无效
    if (res.status === 401) {
      handleUnauthorized()
      return res
    }

    if (!res.ok && !silent) {
      if (res.status === 404) {
        toast().error('请求的资源不存在 (404)')
      } else if (res.status >= 500) {
        toast().error('服务器内部错误，请稍后重试')
      } else {
        toast().error(`请求失败 (${res.status})`)
      }
    }

    return res
  } catch (err) {
    if (!silent) {
      if (err.name === 'AbortError') {
        toast().error('请求超时，请检查网络连接')
      } else {
        toast().error('网络连接失败，请检查网络')
      }
    }
    throw err
  } finally {
    clearTimeout(timer)
  }
}

/**
 * Convenience: fetch JSON with timeout.
 * Returns parsed JSON or null on failure (silent mode).
 */
export async function fetchJSON(url, options = {}) {
  const res = await request(url, options)
  if (res.ok) return res.json()
  return null
}


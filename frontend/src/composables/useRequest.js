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

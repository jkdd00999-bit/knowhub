/**
 * 获取认证请求头
 * @returns {object} 包含 Authorization 头的对象，未登录时返回空对象
 */
export function getAuthHeaders() {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

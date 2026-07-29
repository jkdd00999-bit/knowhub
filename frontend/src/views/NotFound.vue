<template>
  <div class="not-found">
    <div class="nf-code">404</div>
    <h1>页面未找到</h1>
    <p>你访问的页面不存在或已被移除</p>
    <router-link to="/" class="nf-link">返回首页</router-link>
  </div>
</template>

<style scoped>
.not-found {
  text-align: center;
  padding: 120px 24px;
}
.nf-code {
  font-size: 96px;
  font-weight: 800;
  color: var(--primary);
  line-height: 1;
  opacity: .3;
}
h1 {
  font-size: 24px;
  margin-top: 16px;
  margin-bottom: 8px;
}
p {
  color: var(--text-muted);
  margin-bottom: 32px;
}
.nf-link {
  display: inline-block;
  padding: 10px 28px;
  background: var(--primary);
  color: #fff;
  border-radius: 8px;
  font-weight: 600;
  text-decoration: none;
}
.nf-link:hover { background: var(--primary-light); text-decoration: none; }
</style>


<template>
  <div class="landing">
    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-content">
        <div class="hero-badge">🚀 企业级 AI 知识助手</div>
        <h1>让企业知识<span class="highlight">触手可及</span></h1>
        <p class="hero-desc">
          基于大语言模型与 RAG 技术，为企业打造智能知识管理中枢。<br />
          上传文档、构建知识库、AI 自动检索与问答，让知识创造价值。
        </p>
        <div class="hero-actions">
          <router-link to="/register" class="btn-hero-primary">免费开始使用</router-link>
          <router-link to="/knowledge" class="btn-hero-secondary">浏览知识库 →</router-link>
        </div>
        <div class="hero-stats">
          <div class="hero-stat">
            <span class="stat-num">3+</span>
            <span class="stat-label">支持文档格式</span>
          </div>
          <div class="hero-stat">
            <span class="stat-num">RAG</span>
            <span class="stat-label">智能检索引擎</span>
          </div>
          <div class="hero-stat">
            <span class="stat-num">7×24</span>
            <span class="stat-label">AI 在线服务</span>
          </div>
        </div>
      </div>
      <div class="hero-visual">
        <div class="chat-demo">
          <div class="chat-header">
            <span class="chat-dot green"></span>
            AI 知识助手
          </div>
          <div class="chat-messages">
            <div class="chat-msg user">高新技术企业认定需要哪些条件？</div>
            <div class="chat-msg assistant">
              根据《高新技术企业认定管理办法》，主要条件包括：<br />
              1. 企业申请认定时须注册成立一年以上<br />
              2. 拥有核心自主知识产权<br />
              3. 产品属于国家重点支持的高新技术领域<br />
              4. 研发人员占比不低于10%<br />
              <span class="chat-source">📎 来源：科技政策库</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 核心功能 -->
    <section class="section features">
      <div class="section-header">
        <h2>核心功能</h2>
        <p>从知识入库到智能问答，一站式解决</p>
      </div>
      <div class="feature-grid">
        <div class="feature-card">
          <div class="feature-icon">📤</div>
          <h3>智能文档解析</h3>
          <p>支持 PDF、Word、Markdown、TXT 等多种格式，自动提取文本、语义分块、向量化存储</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🔍</div>
          <h3>混合检索引擎</h3>
          <p>向量语义检索 + BM25 关键词检索，混合加权排序，精准命中所需知识</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">💬</div>
          <h3>多轮对话</h3>
          <p>基于 RAG 的智能问答，支持多轮上下文、流式输出、引用来源追溯</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🧠</div>
          <h3>长期记忆</h3>
          <p>AI 自动记住你的偏好与上下文，越用越懂你，提供个性化知识服务</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">📚</div>
          <h3>多知识库管理</h3>
          <p>按业务、部门、主题构建独立知识库，权限隔离，结构化管理</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🔔</div>
          <h3>智能订阅推送</h3>
          <p>设置关键词与分类订阅，新政策、新知识自动推送，不再错过重要信息</p>
        </div>
      </div>
    </section>

    <!-- 使用场景 -->
    <section class="section scenarios">
      <div class="section-header">
        <h2>适用场景</h2>
        <p>覆盖企业知识管理全场景</p>
      </div>
      <div class="scenario-grid">
        <div class="scenario-card">
          <div class="scenario-tag">政策合规</div>
          <h3>政策法规智能检索</h3>
          <p>快速查找科技、财税、环保等领域政策文件，AI 解读关键条款，辅助合规决策</p>
        </div>
        <div class="scenario-card">
          <div class="scenario-tag">客户服务</div>
          <h3>智能客服知识底座</h3>
          <p>构建产品知识库，AI 自动回答客户常见问题，减轻客服压力，提升响应速度</p>
        </div>
        <div class="scenario-card">
          <div class="scenario-tag">内部培训</div>
          <h3>企业培训知识库</h3>
          <p>沉淀内部经验与培训资料，新员工快速获取所需知识，加速入职上手</p>
        </div>
        <div class="scenario-card">
          <div class="scenario-tag">研发支持</div>
          <h3>技术文档管理</h3>
          <p>API 文档、技术方案、设计规范集中管理，研发团队高效协作</p>
        </div>
      </div>
    </section>

    <!-- 工作原理 -->
    <section class="section workflow">
      <div class="section-header">
        <h2>三步开始</h2>
        <p>简单三步，即可拥有你的智能知识助手</p>
      </div>
      <div class="workflow-steps">
        <router-link to="/register" class="workflow-step">
          <div class="step-number">1</div>
          <h3>注册账户</h3>
          <p>免费注册，立即获得你的智能知识助手空间</p>
        </router-link>
        <div class="workflow-connector">→</div>
        <router-link to="/dashboard" class="workflow-step">
          <div class="step-number">2</div>
          <h3>上传知识</h3>
          <p>上传文档，系统自动解析、分块、向量化</p>
        </router-link>
        <div class="workflow-connector">→</div>
        <a href="#" class="workflow-step" @click.prevent="openAiChat">
          <div class="step-number">3</div>
          <h3>智能问答</h3>
          <p>向 AI 提问，即刻获得精准答案与来源引用</p>
        </a>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta-section">
      <h2>开始构建你的企业知识库</h2>
      <p>免费试用，无需信用卡</p>
      <router-link to="/register" class="btn-cta">立即注册 →</router-link>
    </section>

    <!-- Footer -->
    <footer class="landing-footer">
      <div class="footer-inner">
        <div class="footer-brand">
          <span class="logo-icon">知</span> 知智 KnowHub
        </div>
        <div class="footer-links">
          <router-link to="/docs">文档</router-link>
        </div>
        <div class="footer-copy">© 2026 知智 KnowHub. All rights reserved.</div>
      </div>
    </footer>
  </div>
</template>

<script setup>
function openAiChat() {
  // 触发 AI 助手悬浮窗打开
  window.dispatchEvent(new CustomEvent('open-ai-assistant'))
}
</script>

<style scoped>
.landing { max-width: 1100px; margin: 0 auto; }

/* Hero */
.hero {
  display: grid; grid-template-columns: 1fr 1fr; gap: 48px;
  align-items: center; padding: 48px 0 60px;
}
.hero-badge {
  display: inline-block; background: #eef2ff; color: var(--primary);
  padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 600;
  margin-bottom: 16px;
}
.hero h1 {
  font-size: 40px; font-weight: 900; line-height: 1.2; margin-bottom: 16px;
}
.highlight {
  background: linear-gradient(120deg, var(--primary), #8b5cf6);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-desc {
  font-size: 16px; color: var(--text-muted); line-height: 1.7; margin-bottom: 28px;
}
.hero-actions { display: flex; gap: 12px; margin-bottom: 36px; flex-wrap: wrap; }
.btn-hero-primary {
  padding: 12px 28px; background: var(--primary); color: #fff;
  border-radius: 8px; font-size: 15px; font-weight: 600;
  transition: background .15s, transform .15s;
  min-height: 48px; display: inline-flex; align-items: center;
}
.btn-hero-primary:hover { background: var(--primary-light); transform: translateY(-1px); text-decoration: none; }
.btn-hero-secondary {
  padding: 12px 24px; background: var(--card); color: var(--primary);
  border: 1px solid var(--border); border-radius: 8px; font-size: 15px; font-weight: 600;
  transition: border-color .15s, background .15s;
  min-height: 48px; display: inline-flex; align-items: center;
}
.btn-hero-secondary:hover { border-color: var(--primary); background: #f8f8ff; text-decoration: none; }

.hero-stats { display: flex; gap: 32px; }
.hero-stat { display: flex; flex-direction: column; }
.stat-num { font-size: 22px; font-weight: 800; color: var(--primary); }
.stat-label { font-size: 12px; color: var(--text-muted); }

/* Chat Demo */
.hero-visual { display: flex; justify-content: center; }
.chat-demo {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg); width: 100%; max-width: 400px; overflow: hidden;
}
.chat-header {
  padding: 12px 16px; border-bottom: 1px solid var(--border);
  font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 8px;
}
.chat-dot { width: 8px; height: 8px; border-radius: 50%; }
.chat-dot.green { background: var(--success); }
.chat-messages { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.chat-msg {
  padding: 10px 14px; border-radius: 10px; font-size: 13px; line-height: 1.6; max-width: 90%;
}
.chat-msg.user {
  background: var(--primary); color: #fff; align-self: flex-end;
  border-bottom-right-radius: 4px;
}
.chat-msg.assistant {
  background: var(--bg); border: 1px solid var(--border); align-self: flex-start;
  border-bottom-left-radius: 4px;
}
.chat-source {
  display: block; margin-top: 8px; font-size: 11px; color: var(--primary);
  font-weight: 500;
}

/* Sections */
.section { padding: 60px 0; }
.section-header { text-align: center; margin-bottom: 40px; }
.section-header h2 { font-size: 28px; font-weight: 800; margin-bottom: 8px; }
.section-header p { font-size: 15px; color: var(--text-muted); }

/* Features */
.feature-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;
}
.feature-card {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 28px 24px; transition: box-shadow .2s, transform .2s;
  cursor: pointer; text-decoration: none; color: inherit; display: block;
}
.feature-card:hover { box-shadow: var(--shadow-md); transform: translateY(-3px); text-decoration: none; border-color: var(--primary); }
.feature-icon { font-size: 28px; margin-bottom: 14px; }
.feature-card h3 { font-size: 16px; font-weight: 700; margin-bottom: 8px; }
.feature-card p { font-size: 13px; color: var(--text-muted); line-height: 1.6; }

/* Scenarios */
.scenario-grid {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;
}
.scenario-card {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 24px; transition: box-shadow .2s, border-color .2s;
  cursor: pointer; text-decoration: none; color: inherit; display: block;
}
.scenario-card:hover { box-shadow: var(--shadow-md); border-color: var(--primary); text-decoration: none; }
.scenario-tag {
  display: inline-block; background: #eef2ff; color: var(--primary);
  padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;
  margin-bottom: 10px;
}
.scenario-card h3 { font-size: 16px; font-weight: 700; margin-bottom: 6px; }
.scenario-card p { font-size: 13px; color: var(--text-muted); line-height: 1.6; }

/* Workflow */
.workflow-steps {
  display: flex; align-items: flex-start; justify-content: center; gap: 16px;
}
.workflow-step {
  text-align: center; background: var(--card); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 28px 24px; flex: 1; max-width: 260px;
  cursor: pointer; text-decoration: none; color: inherit; display: block;
  transition: box-shadow .2s, border-color .2s;
}
.workflow-step:hover { box-shadow: var(--shadow-md); border-color: var(--primary); text-decoration: none; }
.step-number {
  width: 40px; height: 40px; border-radius: 50%; background: var(--primary); color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 18px; font-weight: 800; margin-bottom: 14px;
}
.workflow-step h3 { font-size: 16px; font-weight: 700; margin-bottom: 6px; }
.workflow-step p { font-size: 13px; color: var(--text-muted); }
.workflow-connector {
  font-size: 24px; color: var(--text-muted); padding-top: 36px;
}

/* CTA */
.cta-section {
  text-align: center; padding: 60px 24px;
  background: linear-gradient(135deg, #4F46E5, #7c3aed);
  border-radius: var(--radius-lg); color: #fff; margin: 20px 0 40px;
}
.cta-section h2 { font-size: 26px; font-weight: 800; margin-bottom: 8px; }
.cta-section p { font-size: 15px; opacity: .85; margin-bottom: 24px; }
.btn-cta {
  display: inline-block; padding: 12px 32px;
  background: #fff; color: var(--primary); border-radius: 8px;
  font-size: 15px; font-weight: 700;
  transition: transform .15s, box-shadow .15s;
  min-height: 48px;
}
.btn-cta:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,.2); text-decoration: none; }

/* Footer */
.landing-footer {
  border-top: 1px solid var(--border); padding: 24px 0; margin-top: 20px;
}
.footer-inner {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 16px;
}
.footer-brand {
  font-size: 15px; font-weight: 700; color: var(--primary);
  display: flex; align-items: center; gap: 6px;
}
.footer-links { display: flex; gap: 20px; }
.footer-links a { font-size: 13px; color: var(--text-muted); }
.footer-copy { font-size: 12px; color: var(--text-muted); }

/* Responsive */
@media (max-width: 900px) {
  .hero { grid-template-columns: 1fr; text-align: center; }
  .hero-actions { justify-content: center; }
  .hero-stats { justify-content: center; }
  .hero-visual { margin-top: 24px; }
  .feature-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
  .hero h1 { font-size: 30px; }
  .feature-grid { grid-template-columns: 1fr; }
  .scenario-grid { grid-template-columns: 1fr; }
  .workflow-steps { flex-direction: column; align-items: center; }
  .workflow-connector { display: none; }
  .footer-inner { flex-direction: column; text-align: center; }
}
</style>

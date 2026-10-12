<template>
  <div class="site-shell">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <header class="site-header">
      <RouterLink class="brand" to="/" aria-label="机车博士首页">
        <img class="brand-logo" src="/brand-logo.jpg" alt="DrMoto" width="1024" height="1024" decoding="async" />
        <span>机车博士</span>
      </RouterLink>

      <nav class="nav-links" aria-label="官网导航">
        <RouterLink to="/#riders">车主服务</RouterLink>
        <RouterLink to="/#business">门店方案</RouterLink>
        <RouterLink to="/#values">服务理念</RouterLink>
        <RouterLink to="/contact">联系预约</RouterLink>
      </nav>

      <a class="login-link" :href="loginUrl">门店后台</a>
    </header>

    <div id="main-content" tabindex="-1"><RouterView /></div>

    <footer class="site-footer">
      <div>
        <strong>机车博士 DrMoto</strong>
        <p>让每一次机车维修，都清楚可见。</p>
      </div>
      <div class="footer-links">
        <a href="/#riders">车主服务</a>
        <a href="/#business">门店解决方案</a>
        <a :href="loginUrl">登录系统</a>
      </div>
    </footer>
  </div>
</template>

<script setup>
const loginUrl = import.meta.env.VITE_APP_LOGIN_URL || '/app'
</script>

<template>
  <div class="page-container login-view">
    <div class="logo-area">
      <h1>DrMoto</h1>
      <p>Technician Console</p>
    </div>
    
    <div class="login-card card">
      <van-field v-model="form.username" label="ID" placeholder="Staff ID" />
      <van-field v-model="form.password" type="password" label="PIN" placeholder="Access PIN" />
      <van-button type="primary" block @click="login" :loading="loading" color="#ff9f0a" style="margin-top:20px;">
        Start Shift
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { showSuccessToast } from 'vant'

const router = useRouter()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const login = () => {
  loading.value = true
  setTimeout(() => {
    // Mock Login
    localStorage.setItem('drmoto_staff', JSON.stringify({ id: 999, name: 'Tech Mike' }))
    showSuccessToast('Welcome back, Mike')
    router.push('/')
  }, 1000)
}
</script>

<style scoped>
.login-view { display: flex; flex-direction: column; justify-content: center; padding: 20px; background: #fff; }
.logo-area { text-align: center; margin-bottom: 40px; }
.logo-area h1 { font-size: 32px; margin: 0; color: #ff9f0a; }
.logo-area p { color: #8e8e93; }
</style>

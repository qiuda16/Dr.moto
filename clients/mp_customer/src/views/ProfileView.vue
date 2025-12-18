<template>
  <div class="page-container profile-view">
    <van-nav-bar title="Account" class="nav-transparent" />

    <div class="profile-header">
      <div class="avatar-placeholder">
        {{ currentUser ? currentUser.name[0] : 'G' }}
      </div>
      <div class="user-info" v-if="currentUser">
        <h2>{{ currentUser.name }}</h2>
        <p>{{ currentUser.phone || 'No Phone Linked' }}</p>
      </div>
      <div class="user-info" v-else>
        <h2>Guest</h2>
        <p>Sign in to access garage</p>
      </div>
    </div>

    <div v-if="!currentUser" class="auth-section">
      <div class="card">
        <van-tabs v-model:active="activeTab" background="transparent" title-active-color="#fff" title-inactive-color="#666" line-width="20px">
          <van-tab title="Login">
            <div class="form-body">
              <van-field
                v-model="searchQuery"
                placeholder="Enter Phone Number"
                class="dark-field"
                :border="false"
              />
              <van-button block color="#3e64ff" style="margin-top:20px;" @click="search">Find Account</van-button>
            </div>
          </van-tab>
          
          <van-tab title="Register">
            <div class="form-body">
              <van-field v-model="regForm.name" placeholder="Your Name" class="dark-field" :border="false" />
              <van-field v-model="regForm.phone" placeholder="Mobile Number" class="dark-field" :border="false" />
              <van-field v-model="regForm.email" placeholder="Email (Optional)" class="dark-field" :border="false" />
              <van-button block color="#30d158" style="margin-top:20px;" @click="register">Create Account</van-button>
            </div>
          </van-tab>
        </van-tabs>
      </div>
      
      <div v-if="searchResults.length && activeTab === 0" class="search-results card">
        <div 
          v-for="u in searchResults" 
          :key="u.id" 
          class="result-item"
          @click="login(u)"
        >
          <div class="u-left">
            <span class="u-name">{{ u.name }}</span>
            <span class="u-phone">{{ u.phone }}</span>
          </div>
          <van-icon name="arrow" />
        </div>
      </div>
    </div>

    <div v-else class="dashboard-section">
      <div class="stats-grid">
        <div class="stat-box">
          <div class="num">850</div>
          <div class="lbl">Points</div>
        </div>
        <div class="stat-box">
          <div class="num">Gold</div>
          <div class="lbl">Tier</div>
        </div>
      </div>

      <div class="menu-list">
        <div class="menu-item">
          <div class="left"><van-icon name="credit-pay" /> Payment Methods</div>
          <van-icon name="arrow" />
        </div>
        <div class="menu-item">
          <div class="left"><van-icon name="setting-o" /> Settings</div>
          <van-icon name="arrow" />
        </div>
        <div class="menu-item danger" @click="logout">
          <div class="left"><van-icon name="revoke" /> Sign Out</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import request from '../utils/request'
import { showToast, showSuccessToast } from 'vant'
import { useRouter } from 'vue-router'

const router = useRouter()
const activeTab = ref(0)
const searchQuery = ref('')
const searchResults = ref([])
const currentUser = ref(null)
const regForm = reactive({ name: '', phone: '', email: '' })

onMounted(() => {
  const stored = localStorage.getItem('drmoto_user')
  if (stored) {
    currentUser.value = JSON.parse(stored)
  }
})

const search = async () => {
  if (!searchQuery.value) return
  try {
    const res = await request.get(`/mp/workorders/customers/search?query=${searchQuery.value}`)
    searchResults.value = res
    if (res.length === 0) showToast('User not found')
  } catch (err) {
    // handled by request.js
  }
}

const register = async () => {
  if (!regForm.name || !regForm.phone) {
    showToast('Name and Phone required')
    return
  }
  try {
    const res = await request.post('/mp/workorders/customers', regForm)
    showSuccessToast('Account Created!')
    login(res)
  } catch (err) {
  }
}

const login = (user) => {
  currentUser.value = user
  localStorage.setItem('drmoto_user', JSON.stringify(user))
  searchResults.value = []
  showSuccessToast(`Welcome ${user.name}`)
  setTimeout(() => router.push('/'), 500)
}

const logout = () => {
  currentUser.value = null
  localStorage.removeItem('drmoto_user')
  router.push('/')
}
</script>

<style scoped>
.nav-transparent { background: transparent !important; }
.profile-view { padding-top: 40px; }

.profile-header { display: flex; flex-direction: column; align-items: center; margin-bottom: 40px; }
.avatar-placeholder {
  width: 100px; height: 100px; border-radius: 50%; background: #1c1c1e;
  color: white; font-size: 40px; font-weight: bold;
  display: flex; justify-content: center; align-items: center;
  margin-bottom: 15px;
  border: 2px solid #3e64ff;
}
.user-info { text-align: center; }
.user-info h2 { font-size: 24px; margin: 0 0 5px 0; }
.user-info p { color: #8e8e93; margin: 0; }

.form-body { padding: 20px 0; }
.dark-field { background: #2c2c2e; border-radius: 10px; margin-bottom: 15px; padding: 15px; color: white; }
:deep(.van-field__control) { color: white; }

.result-item { 
  padding: 15px; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center; cursor: pointer;
}
.u-name { font-weight: bold; display: block; }
.u-phone { font-size: 12px; color: #8e8e93; }

.stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 0 20px 40px; }
.stat-box { background: #1c1c1e; padding: 20px; border-radius: 16px; text-align: center; border: 1px solid rgba(255,255,255,0.05); }
.stat-box .num { font-size: 24px; font-weight: 800; color: #3e64ff; margin-bottom: 5px; }
.stat-box .lbl { font-size: 12px; color: #8e8e93; text-transform: uppercase; }

.menu-list { margin: 0 20px; background: #1c1c1e; border-radius: 16px; overflow: hidden; }
.menu-item { 
  padding: 20px; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: space-between;
  font-size: 16px; color: #fff; cursor: pointer;
}
.menu-item .left { display: flex; align-items: center; gap: 10px; }
.menu-item.danger { color: #ff453a; }
</style>

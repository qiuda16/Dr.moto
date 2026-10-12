<template>
  <router-view v-if="!showShell" />
  <div v-else class="app-layout" :style="layoutVars">
    <el-container>
      <el-aside width="220px" class="sidebar">
        <div class="logo">
          <span class="logo-mark">{{ appSettings.brand_name }}</span>
          <span v-if="!isCompactLayout" class="badge">{{ appSettings.sidebar_badge_text }}</span>
        </div>
        <el-menu
          router
          :default-active="$route.path"
          background-color="#001529"
          text-color="#fff"
          :active-text-color="appSettings.primary_color"
          :collapse="isCompactLayout"
          :collapse-transition="false"
        >
          <el-menu-item index="/">
            <el-icon><Odometer /></el-icon>
            <span>总览看板</span>
          </el-menu-item>
          <el-menu-item index="/orders">
            <el-icon><List /></el-icon>
            <span>工单中心</span>
          </el-menu-item>
          <el-menu-item index="/customers">
            <el-icon><User /></el-icon>
            <span>客户库</span>
          </el-menu-item>
          <el-menu-item index="/inventory">
            <el-icon><Box /></el-icon>
            <span>库存中心</span>
          </el-menu-item>
          <el-menu-item index="/shop">
            <el-icon><ShoppingCart /></el-icon>
            <span>商城中心</span>
          </el-menu-item>
          <el-menu-item index="/trial-inbox">
            <el-icon><Tickets /></el-icon>
            <span>试运营待办</span>
          </el-menu-item>
          <el-menu-item index="/settings">
            <el-icon><Setting /></el-icon>
            <span>门店设置</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-container>
        <el-header :class="['page-header', { compact: isCompactLayout }]">
          <div class="header-info">
            <div class="breadcrumb">{{ pageTitle }}</div>
            <div v-if="!isCompactLayout" class="store-name">{{ appSettings.store_name }}</div>
          </div>
          <div class="user-profile">
            <el-avatar
              size="small"
              src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png"
            />
            <span v-if="!isCompactLayout" class="user-label">系统管理员</span>
            <el-button text class="logout-button" @click="handleLogout">退出</el-button>
          </div>
        </el-header>

        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Odometer, List, User, Box, Setting, ShoppingCart, Tickets } from '@element-plus/icons-vue'

import request from './utils/request'
import { clearAuthToken, getAuthToken } from './utils/auth'
import { applyAppSettings, createAppSettingsState } from './composables/appSettings'

const route = useRoute()
const router = useRouter()

const titleMap = {
  '/': '总览看板',
  '/orders': '工单中心',
  '/customers': '客户库',
  '/inventory': '库存中心',
  '/shop': '商城中心',
  '/trial-inbox': '试运营待办',
  '/settings': '门店设置',
}

const appSettings = reactive(createAppSettingsState())
const showShell = computed(() => route.name !== 'login')
const pageTitle = computed(() => titleMap[route.path] || '门店管理后台')
const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1280)
const isCompactLayout = computed(() => windowWidth.value < 1200)
const layoutVars = computed(() => ({
  '--brand-primary': appSettings.primary_color || '#409EFF',
}))

const loadAppSettings = async () => {
  if (!getAuthToken()) return
  try {
    const data = await request.get('/mp/settings')
    applyAppSettings(appSettings, data)
  } catch {
    applyAppSettings(appSettings)
  }
}

const handleStoreChanged = () => {
  loadAppSettings()
}

const handleLogout = async () => {
  clearAuthToken()
  await router.push({ name: 'login' })
}

const handleResize = () => {
  windowWidth.value = window.innerWidth
}

watch(
  showShell,
  (active, previous) => {
    if (active) {
      loadAppSettings()
      window.addEventListener('drmoto-store-changed', handleStoreChanged)
      return
    }
    if (previous) {
      window.removeEventListener('drmoto-store-changed', handleStoreChanged)
    }
  },
  { immediate: true },
)

onMounted(() => {
  if (typeof window === 'undefined') return
  window.addEventListener('resize', handleResize, { passive: true })
  handleResize()
})

onBeforeUnmount(() => {
  window.removeEventListener('drmoto-store-changed', handleStoreChanged)
})

onUnmounted(() => {
  if (typeof window === 'undefined') return
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.app-layout {
  height: 100vh;
  display: flex;
}

.sidebar {
  background-color: #001529;
  color: white;
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  font-size: 20px;
  font-weight: bold;
  background: #002140;
  white-space: nowrap;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 10px;
}

.logo-mark {
  color: #fff;
  letter-spacing: 0.02em;
}

.badge {
  font-size: 10px;
  background: var(--brand-primary, #409EFF);
  padding: 2px 6px;
  border-radius: 4px;
  vertical-align: top;
  margin-left: 6px;
}

.el-menu {
  border: none;
  flex: 1;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  gap: 12px;
  min-width: 0;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.breadcrumb {
  font-size: 16px;
  font-weight: 600;
  color: #1f2d3d;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.store-name {
  font-size: 12px;
  color: #7a8599;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.user-label {
  margin-left: 10px;
}

.logout-button {
  margin-left: 8px;
  color: #ef4444;
}

.main-content {
  background: #f5f7fa;
}

.app-layout.compact .sidebar {
  width: 72px !important;
}

.app-layout.compact .logo {
  justify-content: center;
  padding: 0 6px;
  font-size: 15px;
}

.app-layout.compact .badge,
.app-layout.compact .store-name,
.app-layout.compact .user-label {
  display: none;
}

.app-layout.compact .page-header {
  padding: 0 12px;
}

.app-layout.compact .breadcrumb {
  font-size: 14px;
}

.app-layout.compact .main-content {
  padding-left: 14px;
  padding-right: 14px;
}

@media (max-width: 900px) {
  .page-header {
    flex-wrap: wrap;
    align-items: flex-start;
    padding: 10px 12px;
  }

  .user-profile {
    margin-left: auto;
  }
}
</style>

<template>
  <router-view v-if="!showShell" />
  <div v-else class="app-layout" :style="layoutVars">
    <el-container>
      <el-aside width="220px" class="sidebar">
        <div class="logo">
          {{ appSettings.brand_name }}
          <span class="badge">{{ appSettings.sidebar_badge_text }}</span>
        </div>
        <el-menu
          router
          :default-active="$route.path"
          background-color="#001529"
          text-color="#fff"
          :active-text-color="appSettings.primary_color"
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
          <el-menu-item index="/settings">
            <el-icon><Setting /></el-icon>
            <span>门店设置</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-container>
        <el-header class="page-header">
          <div class="header-info">
            <div class="breadcrumb">{{ pageTitle }}</div>
            <div class="store-name">{{ appSettings.store_name }}</div>
          </div>
          <div class="user-profile">
            <el-avatar
              size="small"
              src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png"
            />
            <span class="user-label">系统管理员</span>
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
import { computed, onBeforeUnmount, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Odometer, List, User, Box, Setting } from '@element-plus/icons-vue'

import request from './utils/request'
import { clearAuthToken } from './utils/auth'
import { applyAppSettings, createAppSettingsState } from './composables/appSettings'

const route = useRoute()
const router = useRouter()

const titleMap = {
  '/': '总览看板',
  '/orders': '工单中心',
  '/customers': '客户库',
  '/inventory': '库存中心',
  '/settings': '门店设置',
}

const appSettings = reactive(createAppSettingsState())
const showShell = computed(() => route.name !== 'login')
const pageTitle = computed(() => titleMap[route.path] || '门店管理后台')
const layoutVars = computed(() => ({
  '--brand-primary': appSettings.primary_color || '#409EFF',
}))

const loadAppSettings = async () => {
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

onBeforeUnmount(() => {
  window.removeEventListener('drmoto-store-changed', handleStoreChanged)
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
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.breadcrumb {
  font-size: 16px;
  font-weight: 600;
  color: #1f2d3d;
}

.store-name {
  font-size: 12px;
  color: #7a8599;
}

.user-profile {
  display: flex;
  align-items: center;
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
</style>

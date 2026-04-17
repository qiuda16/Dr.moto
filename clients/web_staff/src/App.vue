<template>
  <div class="app-layout" :style="layoutVars">
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
            <span>主数据中心</span>
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
            <el-avatar size="small" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
            <span class="user-label">系统管理员</span>
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
import { computed, onBeforeUnmount, onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { Odometer, List, User, Box } from '@element-plus/icons-vue'

import request from './utils/request'
import { applyAppSettings, createAppSettingsState } from './composables/appSettings'

const route = useRoute()

const titleMap = {
  '/': '总览看板',
  '/orders': '工单中心',
  '/customers': '客户库',
  '/inventory': '主数据中心',
  '/settings': '门店设置',
}

const appSettings = reactive(createAppSettingsState())

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

onMounted(() => {
  loadAppSettings()
  window.addEventListener('drmoto-store-changed', loadAppSettings)
})

onBeforeUnmount(() => {
  window.removeEventListener('drmoto-store-changed', loadAppSettings)
})
</script>

<style scoped>
.app-layout { height: 100vh; display: flex; }
.sidebar { background-color: #001529; color: white; display: flex; flex-direction: column; }
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
.el-menu { border: none; flex: 1; }
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
.user-profile { display: flex; align-items: center; }
.user-label { margin-left: 10px; }
.main-content { background: #f5f7fa; }
</style>

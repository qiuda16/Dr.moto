<template>
  <div class="shell-page">
    <router-view v-slot="{ Component }">
      <transition name="fade-up" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>

    <div class="tabbar-wrap">
      <van-tabbar route :border="false" class="shell-tabbar">
        <van-tabbar-item
          v-for="item in tabs"
          :key="item.to"
          :to="item.to"
          :icon="item.icon"
        >
          {{ item.label }}
        </van-tabbar-item>
      </van-tabbar>
    </div>
  </div>
</template>

<script setup>
import { APP_TABS } from '../constants/nav'

const tabs = APP_TABS
</script>

<style scoped>
.shell-page {
  min-height: 100vh;
}

.tabbar-wrap {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 16px;
  display: flex;
  justify-content: center;
  pointer-events: none;
  z-index: 20;
}

.shell-tabbar {
  width: min(92vw, 500px);
  border: 1px solid rgba(223, 228, 236, 0.95);
  border-radius: 20px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  overflow: hidden;
  pointer-events: all;
  background: rgba(255, 255, 255, 0.88);
}

.fade-up-enter-active,
.fade-up-leave-active {
  transition: all var(--motion-fast) var(--motion-curve);
}

.fade-up-enter-from,
.fade-up-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>

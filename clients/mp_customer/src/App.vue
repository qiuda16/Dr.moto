<template>
  <div class="app-container">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
    
    <van-tabbar v-model="active" route :border="false" class="glass-tabbar">
      <van-tabbar-item to="/" icon="apps-o">Garage</van-tabbar-item>
      <van-tabbar-item to="/orders" icon="notes-o">Activity</van-tabbar-item>
      <van-tabbar-item to="/profile" icon="user-o">Account</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const active = ref(0)
</script>

<style>
/* Import global styles */
@import './assets/main.css';

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.glass-tabbar {
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-top: 1px solid rgba(255,255,255,0.1);
}
</style>

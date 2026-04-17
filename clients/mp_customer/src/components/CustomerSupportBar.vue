<template>
  <div class="support-wrap">
    <div class="support-card">
      <div class="text">
        <div class="title">需要帮助？</div>
        <div class="desc">联系门店顾问，避免盲目保养</div>
      </div>
      <div class="actions">
        <van-button size="small" plain @click="onCall">电话</van-button>
        <van-button size="small" type="primary" @click="onChat">咨询</van-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { showToast } from 'vant'

function onCall() {
  window.location.href = 'tel:400-000-0000'
}

function onChat() {
  showToast('请在“我的”页面查看门店联系方式')
}
</script>

<style scoped>
.support-wrap {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 94px;
  display: flex;
  justify-content: center;
  z-index: 15;
  pointer-events: none;
}

.support-card {
  width: min(92vw, 500px);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: var(--shadow-soft);
  padding: 10px 12px;
  pointer-events: all;
}

.title {
  font-size: 14px;
  font-weight: 600;
}

.desc {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 12px;
}

.actions {
  display: flex;
  gap: 8px;
}
</style>

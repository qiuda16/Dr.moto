<template>
  <div class="page-container">
    <van-nav-bar title="Task Board">
      <template #right>
        <van-icon name="replay" @click="loadTasks" />
      </template>
    </van-nav-bar>

    <van-tabs v-model:active="activeTab" sticky color="#ff9f0a">
      <van-tab title="Todo" :badge="todoList.length || ''">
        <div class="task-list">
          <div class="task-card card" v-for="t in todoList" :key="t.id" @click="openTask(t)">
            <div class="header">
              <span class="plate">{{ t.vehicle_plate }}</span>
              <van-tag type="warning">{{ t.state }}</van-tag>
            </div>
            <div class="desc">{{ t.name }}</div>
            <div class="footer">
              <span>{{ t.date_planned }}</span>
              <van-button size="mini" type="primary" plain>Start</van-button>
            </div>
          </div>
        </div>
      </van-tab>
      
      <van-tab title="In Progress" :badge="progressList.length || ''">
        <div class="task-list">
          <div class="task-card card" v-for="t in progressList" :key="t.id" @click="openTask(t)">
            <div class="header">
              <span class="plate">{{ t.vehicle_plate }}</span>
              <van-tag type="primary">Working</van-tag>
            </div>
            <div class="desc">{{ t.name }}</div>
          </div>
        </div>
      </van-tab>

      <van-tab title="Done">
        <!-- History list -->
      </van-tab>
    </van-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import request from '../utils/request'
import { useRouter } from 'vue-router'

const router = useRouter()
const activeTab = ref(0)
const tasks = ref([])

onMounted(() => loadTasks())

const loadTasks = async () => {
  try {
    // Reuse the active list API for now, later filter by staff
    const res = await request.get('/mp/workorders/active/list')
    tasks.value = res
  } catch (e) {}
}

const todoList = computed(() => tasks.value.filter(t => ['confirmed', 'diagnosing', 'quoted'].includes(t.state)))
const progressList = computed(() => tasks.value.filter(t => ['in_progress', 'ready'].includes(t.state)))

const openTask = (task) => {
  router.push(`/workorder/${task.bff_uuid || task.id}`)
}
</script>

<style scoped>
.task-list { padding: 10px 0; }
.task-card { padding: 15px; border-left: 4px solid #ff9f0a; }
.header { display: flex; justify-content: space-between; margin-bottom: 8px; }
.plate { font-weight: bold; font-size: 16px; }
.desc { color: #333; margin-bottom: 10px; }
.footer { display: flex; justify-content: space-between; align-items: center; color: #999; font-size: 12px; }
</style>

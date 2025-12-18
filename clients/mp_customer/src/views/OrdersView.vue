<template>
  <div class="page-container">
    <van-nav-bar title="Activity" class="nav-transparent" />
    
    <van-tabs v-model:active="activeTab" background="transparent" title-active-color="#fff" title-inactive-color="#666" line-width="20px">
      <van-tab title="Active">
        <div class="list">
          <div class="order-item" v-for="o in activeList" :key="o.id" @click="goDetail(o)">
            <div class="top">
              <span class="plate">{{ o.vehicle_plate }}</span>
              <span class="time">{{ o.date_planned }}</span>
            </div>
            <div class="mid">
              <h3>{{ o.name }}</h3>
              <p>Service Request</p>
            </div>
            <div class="bot">
              <span class="status-text">{{ o.state }}</span>
              <van-icon name="arrow" />
            </div>
          </div>
        </div>
      </van-tab>
      
      <van-tab title="History">
        <div class="list">
          <div class="order-item history" v-for="o in historyList" :key="o.id" @click="goDetail(o)">
             <div class="top">
              <span class="plate">{{ o.vehicle_plate }}</span>
              <span class="price">${{ o.amount_total }}</span>
            </div>
            <div class="mid">
              <h3>{{ o.name }}</h3>
              <p>Completed</p>
            </div>
          </div>
        </div>
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
const orders = ref([])

onMounted(async () => {
  const user = JSON.parse(localStorage.getItem('drmoto_user'))
  if(user) orders.value = await request.get(`/mp/workorders/customers/${user.id}/orders`)
})

const activeList = computed(() => orders.value.filter(o => !['done', 'cancel'].includes(o.state)))
const historyList = computed(() => orders.value.filter(o => ['done', 'cancel'].includes(o.state)))

const goDetail = (o) => router.push(`/orders/${o.bff_uuid || o.id}`)
</script>

<style scoped>
.nav-transparent { background: transparent !important; }
.list { padding: 20px; }
.order-item {
  background: #1c1c1e; border-radius: 12px; padding: 20px; margin-bottom: 15px;
  border: 1px solid rgba(255,255,255,0.05);
}
.top { display: flex; justify-content: space-between; font-size: 12px; color: #8e8e93; margin-bottom: 10px; }
.mid h3 { margin: 0 0 5px 0; font-size: 18px; }
.mid p { margin: 0; color: #8e8e93; font-size: 14px; }
.bot { margin-top: 15px; display: flex; justify-content: space-between; align-items: center; color: #3e64ff; font-weight: 500; font-size: 14px; text-transform: uppercase; }
.price { color: #fff; font-weight: bold; }
.history { opacity: 0.6; }
</style>

<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <div class="stat-card card">
          <div class="label">Active Orders</div>
          <div class="value">{{ stats.active }}</div>
          <div class="trend up">+12%</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card card">
          <div class="label">Revenue (Today)</div>
          <div class="value">${{ stats.revenue }}</div>
          <div class="trend up">+5%</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card card">
          <div class="label">Technicians</div>
          <div class="value">4 / 6</div>
          <div class="trend">Online</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card card">
          <div class="label">Parts Alert</div>
          <div class="value warning">2</div>
          <div class="trend down">Low Stock</div>
        </div>
      </el-col>
    </el-row>

    <div class="card recent-section" style="margin-top:20px;">
      <h3>Live Shop Floor</h3>
      <el-table :data="recentOrders" style="width: 100%">
        <el-table-column prop="vehicle_plate" label="Vehicle" width="180" />
        <el-table-column prop="name" label="Order Ref" width="180" />
        <el-table-column prop="state" label="Status">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.state)">{{ scope.row.state }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="customer_id" label="Customer" />
        <el-table-column prop="date_planned" label="Due Date" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import request from '../utils/request'

const stats = reactive({
  active: 0,
  revenue: 0
})

const recentOrders = ref([])

onMounted(async () => {
  // Mock Stats
  stats.active = 12
  stats.revenue = 4500
  
  // Real Data
  const res = await request.get('/mp/workorders/active/list')
  recentOrders.value = res
})

const getStatusType = (state) => {
  const map = { draft: 'info', confirmed: 'warning', in_progress: 'primary', done: 'success' }
  return map[state] || ''
}
</script>

<style scoped>
.stat-card { text-align: center; padding: 30px 20px; }
.stat-card .label { color: #999; font-size: 14px; text-transform: uppercase; }
.stat-card .value { font-size: 32px; font-weight: bold; margin: 10px 0; color: #333; }
.stat-card .value.warning { color: #e6a23c; }
.stat-card .trend { font-size: 12px; color: #999; }
.stat-card .trend.up { color: #67c23a; }
.stat-card .trend.down { color: #f56c6c; }
</style>

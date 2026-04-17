<template>
  <div class="card switcher" v-if="vehicleStore.vehicles.length">
    <div class="label">当前车辆</div>
    <van-dropdown-menu active-color="#de3d2b">
      <van-dropdown-item :options="options" :model-value="vehicleStore.activeVehicleId" @change="onChange" />
    </van-dropdown-menu>
  </div>
  <div v-else class="card switcher empty">暂无车辆，请先绑定车辆信息</div>
</template>

<script setup>
import { computed } from 'vue'
import { useVehicleStore } from '../stores/vehicle'

const vehicleStore = useVehicleStore()

const options = computed(() =>
  vehicleStore.vehicles.map((item) => ({
    text: `${item.license_plate || '未命名车辆'}${item.model ? ` · ${item.model}` : ''}`,
    value: item.id,
  }))
)

function onChange(value) {
  vehicleStore.setActiveVehicle(value)
}
</script>

<style scoped>
.switcher {
  padding: 12px;
  margin-bottom: 12px;
}

.label {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0 0 8px 2px;
}

.empty {
  color: var(--text-muted);
  font-size: 13px;
}

:deep(.van-dropdown-menu) {
  border-radius: 14px;
  overflow: hidden;
}
</style>

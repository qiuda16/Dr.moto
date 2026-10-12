<template>
  <view class="page-shell">
    <view class="page-body">
      <view v-if="error" class="notice-banner notice-banner--soft notice-banner--compact">
        <view class="notice-banner__text">
          <view class="notice-banner__title">补录提示</view>
          <view class="notice-banner__desc">{{ error }}</view>
        </view>
      </view>

      <view class="hero-card">
        <view class="hero-kicker">手动体检补录</view>
        <view class="hero-title">填写车辆体检数据</view>
        <view class="hero-subtitle">{{ vehicleLabel || '当前车辆' }} · 提交后会自动记录时间</view>
        <view class="summary-band">
          <view class="summary-band__item">
            <view class="summary-band__value">{{ summaryVehicleLabel }}</view>
            <view class="summary-band__label">当前车辆</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">{{ measuredAtLabel }}</view>
            <view class="summary-band__label">检测时间</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">自动</view>
            <view class="summary-band__label">录入时间</view>
          </view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">记录信息</view>
          <view class="section-head__sub">体检时间可手动选，提交时间由系统自动记录</view>
        </view>
        <view class="record-panel">
          <view class="record-row">
            <view class="field-label">体检时间</view>
            <view class="record-pickers">
              <picker mode="date" :value="form.measured_date" @change="onMeasuredDateChange">
                <view class="record-picker">{{ form.measured_date || '选择日期' }}</view>
              </picker>
              <picker mode="time" :value="form.measured_time" @change="onMeasuredTimeChange">
                <view class="record-picker">{{ form.measured_time || '选择时间' }}</view>
              </picker>
            </view>
            <view class="field-help">如果不选，系统会默认按当前时间记录。</view>
          </view>
          <view class="record-row">
            <view class="field-label">里程 km</view>
            <input v-model="form.odometer_km" type="number" class="field-input" placeholder="例如：8418" />
            <view class="field-help">必填，用于判断保养间隔和里程变化。</view>
          </view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">检测数据</view>
          <view class="section-head__sub">按项目填写，没填会显示无数据</view>
        </view>
        <view class="inspection-form-grid">
          <view v-for="group in inspectionInputGroups" :key="group.key" class="inspection-form-card">
            <view class="inspection-form-card__head">
              <view>
                <view class="inspection-form-card__title">{{ group.label }}</view>
                <view class="inspection-form-card__sub">{{ group.description }}</view>
              </view>
            </view>
            <view class="inspection-form-card__body">
              <view v-for="field in group.items" :key="field.key" class="field-group inspection-field">
                <text class="field-label">{{ field.label }}</text>
                <input
                  v-model="form[field.key]"
                  type="digit"
                  class="field-input"
                  :placeholder="field.placeholder"
                />
                <view class="field-help">{{ field.help }}</view>
              </view>
            </view>
          </view>
          <view class="inspection-form-card inspection-form-card--wide">
            <view class="inspection-form-card__head">
              <view>
                <view class="inspection-form-card__title">备注</view>
                <view class="inspection-form-card__sub">记录现场发现、异常说明或补录原因</view>
              </view>
            </view>
            <textarea v-model="form.notes" class="field-textarea" placeholder="例如：前胎偏低，已补压；电瓶电压略低，建议复检。"></textarea>
          </view>
          <view class="btn-row btn-row--stacked">
            <button class="btn-primary btn-primary--large" :disabled="saving" @tap="submit">
              {{ saving ? '提交中' : '提交补录' }}
            </button>
            <button class="btn-secondary btn-secondary--large" @tap="goBack">返回</button>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../utils/api'

function toNumberOrNull(value) {
  const text = String(value ?? '').trim()
  if (!text) {
    return null
  }
  const num = Number(text)
  return Number.isFinite(num) ? num : null
}

export default {
  data() {
    return {
      error: '',
      saving: false,
      vehicleId: '',
      vehicleLabel: '',
      form: {
        measured_date: '',
        measured_time: '',
        odometer_km: '',
        engine_rpm: '',
        battery_voltage: '',
        tire_front_psi: '',
        tire_rear_psi: '',
        coolant_temp_c: '',
        oil_life_percent: '',
        notes: '',
      },
      inspectionInputGroups: [
        {
          key: 'power',
          label: '动力系统',
          description: '发动机与运转状态',
          items: [
            { key: 'engine_rpm', label: '发动机转速 rpm', placeholder: '例如：1200', help: '可选，记录怠速或测试时数据。' },
          ],
        },
        {
          key: 'battery',
          label: '电瓶系统',
          description: '电源与启动状态',
          items: [
            { key: 'battery_voltage', label: '电瓶电压 V', placeholder: '例如：12.2', help: '可选，电压偏低时建议重点关注。' },
          ],
        },
        {
          key: 'tires',
          label: '胎压系统',
          description: '前后轮胎压',
          items: [
            { key: 'tire_front_psi', label: '前胎压 psi', placeholder: '例如：28', help: '可选，前后轮建议分别填写。' },
            { key: 'tire_rear_psi', label: '后胎压 psi', placeholder: '例如：30', help: '可选，前后轮建议分别填写。' },
          ],
        },
        {
          key: 'cooling',
          label: '冷却与润滑',
          description: '温度与机油状态',
          items: [
            { key: 'coolant_temp_c', label: '冷却液温度 °C', placeholder: '例如：92', help: '可选，温度异常可提示过热风险。' },
            { key: 'oil_life_percent', label: '机油寿命 %', placeholder: '例如：66', help: '可选，用于判断保养周期。' },
          ],
        },
      ],
    }
  },
  computed: {
    summaryVehicleLabel() {
      return this.vehicleLabel || '当前车辆'
    },
    measuredAtLabel() {
      if (!this.form.measured_date) {
        return '当前时间'
      }
      return `${this.form.measured_date}${this.form.measured_time ? ` ${this.form.measured_time}` : ''}`
    },
  },
  onLoad(options) {
    if (options?.vehicle_id) {
      this.vehicleId = String(options.vehicle_id)
    }
  },
  onShow() {
    this.ensureDefaultMeasuredAt()
    if (!this.vehicleId) {
      this.vehicleId = api.getSelectedVehicleId()
    }
    this.loadVehicleLabel()
  },
  methods: {
    ensureDefaultMeasuredAt() {
      if (this.form.measured_date && this.form.measured_time) {
        return
      }
      const now = new Date()
      const pad = (value) => String(value).padStart(2, '0')
      this.form.measured_date = this.form.measured_date || `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
      this.form.measured_time = this.form.measured_time || `${pad(now.getHours())}:${pad(now.getMinutes())}`
    },
    onMeasuredDateChange(event) {
      this.form.measured_date = event?.detail?.value || ''
    },
    onMeasuredTimeChange(event) {
      this.form.measured_time = event?.detail?.value || ''
    },
    async loadVehicleLabel() {
      try {
        const vehicles = await api.getVehicles()
        const matched = (vehicles || []).find((item) => String(item.id) === String(this.vehicleId))
        this.vehicleLabel = matched?.vehicle_line || matched?.license_plate || '当前车辆'
      } catch (_error) {
        this.vehicleLabel = '当前车辆'
      }
    },
    goBack() {
      uni.navigateBack({ delta: 1 })
    },
    async submit() {
      if (this.saving) {
        return
      }
      if (!this.vehicleId) {
        this.error = '请先选择一台车辆'
        return
      }
      const odometer = toNumberOrNull(this.form.odometer_km)
      if (odometer === null) {
        this.error = '请填写里程'
        return
      }
      let measuredAt = null
      if (this.form.measured_date) {
        const timePart = this.form.measured_time || '00:00'
        measuredAt = `${this.form.measured_date}T${timePart}:00+08:00`
      }
      this.saving = true
      this.error = ''
      try {
        await api.createVehicleHealthRecord(this.vehicleId, {
          measured_at: measuredAt,
          odometer_km: odometer,
          engine_rpm: toNumberOrNull(this.form.engine_rpm),
          battery_voltage: toNumberOrNull(this.form.battery_voltage),
          tire_front_psi: toNumberOrNull(this.form.tire_front_psi),
          tire_rear_psi: toNumberOrNull(this.form.tire_rear_psi),
          coolant_temp_c: toNumberOrNull(this.form.coolant_temp_c),
          oil_life_percent: toNumberOrNull(this.form.oil_life_percent),
          notes: this.form.notes || null,
        })
        uni.showToast({ title: '补录已保存', icon: 'success' })
        setTimeout(() => {
          uni.navigateBack({ delta: 1 })
        }, 500)
      } catch (error) {
        this.error = error?.message || '保存体检记录失败'
      } finally {
        this.saving = false
      }
    },
  },
}
</script>

<style lang="scss">
@import '../../styles/mp-customer.scss';
</style>

<template>
  <view class="page-shell">
    <view class="page-body">
      <view v-if="error" class="error-state">{{ error }}</view>

      <view class="hero-card">
        <view class="hero-title">预约草稿</view>
        <view class="hero-subtitle">{{ vehicle.license_plate || '当前车辆' }} {{ serviceKindText }}</view>
      </view>

      <view class="light-card">
        <view class="section-title">预约信息</view>
        <view class="field-label">主题</view>
        <input v-model="subject" class="field-input" placeholder="预约主题" />
        <view class="field-label">服务类型</view>
        <picker :range="serviceKindOptions" range-key="label" :value="serviceKindIndex" @change="handleServiceKind">
          <view class="field-picker">{{ serviceKindText }}</view>
        </picker>
        <view class="field-label">期望时间</view>
        <input v-model="preferredDate" class="field-input" placeholder="2026-04-27T10:00" />
        <view class="field-label">备注</view>
        <textarea v-model="notes" class="field-textarea" placeholder="补充车型、故障或服务诉求" />
        <view class="btn-row">
          <button class="btn-primary" :disabled="submitting" @click="submit">{{ submitting ? '提交中...' : '创建草稿' }}</button>
          <button class="btn-secondary" @click="goAI">回到 AI</button>
        </view>
      </view>

      <view v-if="createdDraft" class="light-card">
        <view class="section-title">已创建</view>
        <view class="list-item">
          <view class="item-title">草稿 #{{ createdDraft.id }}</view>
          <view class="item-desc">{{ createdDraft.subject }}</view>
          <view class="item-meta">{{ createdDraft.preferred_date_text }}</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../utils/api'
import { addHistory, clearJourney, getJourney } from '../../utils/journey'
import { formatDateTime } from '../../utils/format'
import { normalizeErrorMessage, normalizeServiceKind, serviceKindLabel } from '../../utils/i18n'
import { getBindTicket } from '../../utils/session'

function defaultPreferredDate() {
  const now = new Date()
  now.setDate(now.getDate() + 3)
  now.setHours(10, 0, 0, 0)
  const pad = (value) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`
}

export default {
  data() {
    return {
      error: '',
      submitting: false,
      draftId: '',
      vehicleId: '',
      vehicle: {},
      subject: '保养预约',
      serviceKind: 'maintenance',
      preferredDate: defaultPreferredDate(),
      notes: '',
      createdDraft: null,
      serviceKindOptions: [
        { value: 'maintenance', label: '保养' },
        { value: 'repair', label: '维修' },
        { value: 'inspection', label: '检测' },
        { value: 'package', label: '套餐' },
      ],
    }
  },
  computed: {
    serviceKindText() {
      return serviceKindLabel(this.serviceKind)
    },
    serviceKindIndex() {
      return this.serviceKindOptions.findIndex((item) => item.value === this.serviceKind)
    },
  },
  onLoad(options) {
    if (options?.vehicle_id) this.vehicleId = Number(options.vehicle_id)
    if (options?.draft_id) this.draftId = Number(options.draft_id)
    if (options?.subject) this.subject = decodeURIComponent(options.subject)
    if (options?.service_kind) this.serviceKind = normalizeServiceKind(decodeURIComponent(options.service_kind))
    if (options?.notes) this.notes = decodeURIComponent(options.notes)
  },
  onShow() {
    this.bootstrap()
  },
  methods: {
    async bootstrap() {
      this.error = ''
      try {
        const session = await api.ensureCustomerSession()
        if (!session.bound) {
          uni.redirectTo({ url: `/pages/bind/index?bind_ticket=${encodeURIComponent(session.bindTicket || getBindTicket() || '')}` })
          return
        }
        const cockpit = await api.getCockpit(this.vehicleId || api.getSelectedVehicleId() || '')
        this.vehicleId = cockpit.selected_vehicle_id || this.vehicleId || ''
        this.vehicle = cockpit.vehicle || {}
        const activeJourney = getJourney()
        if (activeJourney?.appointmentSubject && this.subject === '保养预约') {
          this.subject = activeJourney.appointmentSubject
        }
        if (activeJourney?.serviceKind && this.serviceKind === 'maintenance') {
          this.serviceKind = normalizeServiceKind(activeJourney.serviceKind)
        }
        if (activeJourney?.notes && !this.notes) {
          this.notes = activeJourney.notes
        }
        if (this.draftId) {
          const draft = await api.getAppointmentDraft(this.draftId)
          this.createdDraft = {
            ...draft,
            preferred_date_text: formatDateTime(draft?.preferred_date),
          }
          this.subject = draft?.subject || this.subject
          this.serviceKind = normalizeServiceKind(draft?.service_kind || this.serviceKind)
          this.notes = draft?.notes || this.notes
          this.preferredDate = draft?.preferred_date || this.preferredDate
        }
      } catch (error) {
        this.error = error?.message || '预约页加载失败'
      }
    },
    handleServiceKind(event) {
      const index = Number(event.detail.value || 0)
      this.serviceKind = this.serviceKindOptions[index]?.value || 'maintenance'
    },
    async submit() {
      if (!String(this.subject || '').trim()) {
        uni.showToast({ title: '请填写预约主题', icon: 'none' })
        return
      }
      this.submitting = true
      this.error = ''
      try {
        const resp = await api.createAppointmentDraft({
          vehicle_id: this.vehicleId || api.getSelectedVehicleId() || null,
          subject: this.subject,
          service_kind: normalizeServiceKind(this.serviceKind),
          source: 'mini_program',
          preferred_date: this.preferredDate || null,
          notes: this.notes,
          payload: { app: 'mp_customer_uni', store_id: 'default' },
        })
        this.createdDraft = {
          ...resp,
          preferred_date_text: formatDateTime(resp?.preferred_date),
        }
        addHistory({
          id: 'appointment_created',
          title: '预约草稿已创建',
          desc: `${resp?.subject || this.subject} · #${resp?.id}`,
          source: 'appointment',
          vehicleId: this.vehicleId || null,
          draftId: resp?.id,
        })
        clearJourney()
        uni.showToast({ title: '已创建预约草稿', icon: 'success' })
      } catch (error) {
        this.error = normalizeErrorMessage(error?.message || '', '创建预约草稿失败')
      } finally {
        this.submitting = false
      }
    },
    goAI() {
      uni.switchTab({ url: '/pages/ai/index' })
    },
  },
}
</script>

<style lang="scss">
@import '../../styles/mp-customer.scss';
</style>

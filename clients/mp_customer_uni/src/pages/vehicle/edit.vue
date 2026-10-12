<template>
  <view class="page-shell">
    <view class="page-body">
      <view v-if="error" class="notice-banner notice-banner--soft notice-banner--compact">
        <view class="notice-banner__text">
          <view class="notice-banner__title">新增车辆提示</view>
          <view class="notice-banner__desc">{{ error }}</view>
        </view>
      </view>

      <view class="hero-card">
        <view class="hero-kicker">新增车辆</view>
        <view class="hero-title">添加一台新车</view>
        <view class="hero-subtitle">填车牌、车型、年份和发动机号，后续就能进驾驶舱和商城适配。</view>
        <view class="summary-band">
          <view class="summary-band__item">
            <view class="summary-band__value">4</view>
            <view class="summary-band__label">必填项</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">3</view>
            <view class="summary-band__label">可选项</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">自动</view>
            <view class="summary-band__label">进入驾驶舱</view>
          </view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">基础信息</view>
          <view class="section-head__sub">先把最关键的车牌、品牌、车型和年份填完整</view>
        </view>
        <view class="record-panel">
          <view class="record-row">
            <view class="field-label">车牌号</view>
            <input v-model="form.license_plate" class="field-input" placeholder="例如：沪A12345" />
            <view class="field-help">必填。进入驾驶舱、预约和补录都会用到。</view>
          </view>
          <view class="record-row">
            <view class="field-label">品牌</view>
            <input v-model="form.make" class="field-input" placeholder="例如：Yamaha" />
            <view class="field-help">必填。用于匹配商城和服务模板。</view>
          </view>
          <view class="record-row">
            <view class="field-label">车型</view>
            <input v-model="form.model" class="field-input" placeholder="例如：NMAX" />
            <view class="field-help">必填。尽量写准确的车型名称。</view>
          </view>
          <view class="record-row">
            <view class="field-label">年份</view>
            <input v-model="form.year" type="number" class="field-input" placeholder="例如：2023" />
            <view class="field-help">必填。后续会参与适配推荐判断。</view>
          </view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">车辆档案</view>
          <view class="section-head__sub">这些信息可选，但越完整越利于匹配</view>
        </view>
        <view class="inspection-form-grid">
          <view class="inspection-form-card">
            <view class="inspection-form-card__head">
              <view class="inspection-form-card__title">识别信息</view>
              <view class="inspection-form-card__sub">用于后台区分同车型、同品牌车辆</view>
            </view>
            <view class="inspection-form-card__body">
              <view class="field-group inspection-field">
                <text class="field-label">发动机号</text>
                <input v-model="form.engine_code" class="field-input" placeholder="可选，例如：E-155" />
                <view class="field-help">可选。用于更细的车型识别。</view>
              </view>
              <view class="field-group inspection-field">
                <text class="field-label">VIN</text>
                <input v-model="form.vin" class="field-input" placeholder="可选，例如：VIN-YAM-NMAX-0001" />
                <view class="field-help">可选。车辆识别码，适合做精确匹配。</view>
              </view>
            </view>
          </view>
          <view class="inspection-form-card">
            <view class="inspection-form-card__head">
              <view class="inspection-form-card__title">外观信息</view>
              <view class="inspection-form-card__sub">用于辅助识别和车辆展示</view>
            </view>
            <view class="inspection-form-card__body">
              <view class="field-group inspection-field">
                <text class="field-label">颜色</text>
                <input v-model="form.color" class="field-input" placeholder="可选，例如：白色 / 黑色" />
                <view class="field-help">可选。主要用于展示和人工识别。</view>
              </view>
            </view>
          </view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">提交动作</view>
          <view class="section-head__sub">保存后可直接进入驾驶舱继续使用</view>
        </view>
        <view class="btn-row btn-row--stacked">
          <button class="btn-primary btn-primary--large" :disabled="saving" @tap="submit">
            {{ saving ? '保存中' : '保存车辆' }}
          </button>
          <button class="btn-secondary btn-secondary--large" @tap="goBack">返回</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../utils/api'

export default {
  data() {
    return {
      error: '',
      saving: false,
      form: {
        license_plate: '',
        make: '',
        model: '',
        year: '',
        engine_code: '',
        vin: '',
        color: '',
      },
    }
  },
  methods: {
    goBack() {
      uni.navigateBack({ delta: 1 })
    },
    async submit() {
      if (this.saving) {
        return
      }
      const year = Number(this.form.year)
      if (!this.form.license_plate || !this.form.make || !this.form.model || !year) {
        this.error = '请至少填写车牌、品牌、车型和年份'
        return
      }
      this.saving = true
      this.error = ''
      try {
        await api.createVehicle({
          license_plate: this.form.license_plate,
          make: this.form.make,
          model: this.form.model,
          year,
          engine_code: this.form.engine_code || null,
          vin: this.form.vin || null,
          color: this.form.color || null,
        })
        uni.showToast({ title: '车辆已添加', icon: 'success' })
        setTimeout(() => {
          uni.navigateBack({ delta: 1 })
        }, 500)
      } catch (error) {
        this.error = error?.message || '新增车辆失败'
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

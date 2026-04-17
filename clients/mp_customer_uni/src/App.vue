﻿﻿﻿<script>
import { TCB_ENV } from './config/env'
import { onUnauthorized } from './utils/request'
import { redirectToLoginOnce } from './utils/session'
import { recordErrorLog } from './utils/monitor'

function extractErrorMessage(payload) {
  if (!payload) return ''
  const reason = payload.reason || payload.error || payload.message
  if (reason instanceof Error) return reason.message
  if (typeof reason === 'string') return reason
  if (reason && typeof reason === 'object' && typeof reason.message === 'string') return reason.message
  return ''
}

export default {
  onLaunch() {
    // #ifdef MP-WEIXIN
    if (typeof wx !== 'undefined' && wx.cloud) {
      wx.cloud.init({
        env: TCB_ENV,
        traceUser: true,
      })
    }

    if (typeof wx !== 'undefined' && typeof wx.onUnhandledRejection === 'function') {
      wx.onUnhandledRejection((payload) => {
        const msg = extractErrorMessage(payload) || '请求失败，请稍后重试'
        recordErrorLog({ message: msg, code: 'UNHANDLED_REJECTION' })
        uni.showToast({ title: msg, icon: 'none' })
      })
    }
    // #endif

    if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
      window.addEventListener('unhandledrejection', (event) => {
        const msg = event?.reason?.message || extractErrorMessage(event) || '请求失败，请稍后重试'
        recordErrorLog({ message: msg, code: 'UNHANDLED_REJECTION' })
        uni.showToast({ title: msg, icon: 'none' })
      })
    }

    onUnauthorized(() => {
      redirectToLoginOnce()
    })

    if (typeof uni !== 'undefined' && typeof uni.onNetworkStatusChange === 'function') {
      uni.onNetworkStatusChange((res) => {
        if (!res?.isConnected) {
          uni.showToast({ title: '网络已断开，请检查网络', icon: 'none' })
        }
      })
    }
  },
}
</script>

<style lang="scss">
@import './styles/app.scss';
</style>

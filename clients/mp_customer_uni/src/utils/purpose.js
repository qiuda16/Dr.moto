export function buildPurposeFlow(cockpit) {
  const flags = cockpit?.health_summary?.flags || []
  const pending = cockpit?.health_summary?.pending_recommendations || 0
  const active = flags.length ? 'detect' : 'review'

  return {
    title: '服务流程',
    desc: pending > 0 ? '先确认体检风险，再和门店约定处理时间。' : '体检状态稳定时，可以按里程计划安排保养。',
    active,
    steps: [
      {
        key: 'detect',
        label: '读取体检',
        desc: '查看异常、提醒和关键数值',
        active: active === 'detect',
      },
      {
        key: 'review',
        label: '确认方案',
        desc: '判断是否需要立即处理',
        active: active === 'review',
      },
      {
        key: 'act',
        label: '门店处理',
        desc: '预约后由服务顾问确认',
        active: active === 'act',
      },
    ],
  }
}

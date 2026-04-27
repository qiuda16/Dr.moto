export function buildPurposeFlow(cockpit) {
  const flags = cockpit?.health_summary?.flags || []
  const pending = cockpit?.health_summary?.pending_recommendations || 0
  const active = flags.length ? 'detect' : 'understand'

  return {
    title: '服务主线',
    desc: pending > 0 ? '先判断，再执行。商城只做辅助参考。' : '先用 AI 看懂车况，再决定预约还是购买。',
    active,
    steps: [
      {
        key: 'detect',
        label: '发现问题',
        desc: '先看异常和提醒',
        active: active === 'detect',
      },
      {
        key: 'understand',
        label: 'AI 解读',
        desc: '先弄清风险与优先级',
        active: active === 'understand',
      },
      {
        key: 'act',
        label: '预约执行',
        desc: '生成草稿后再去门店',
        active: active === 'act',
      },
    ],
  }
}

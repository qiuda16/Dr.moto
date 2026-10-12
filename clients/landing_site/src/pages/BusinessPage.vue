<template>
  <main>
    <section class="page-hero compact-hero">
      <p class="eyebrow">Business</p>
      <h1>
        <span>用 DrMoto 建立</span>
        <span>可记录、可复盘、可复制的售后流程。</span>
      </h1>
      <p>
        面向摩托车维修门店、改装店和连锁售后团队，DrMoto 将工单、客户车辆档案、资料库和 AI 查询连接成一套完整系统。
      </p>
      <RouterLink class="primary-action" to="/contact?type=workshop">预约门店演示</RouterLink>
    </section>

    <section class="capability-grid">
      <article v-for="item in capabilities" :key="item.title">
        <span>{{ item.kicker }}</span>
        <h2>{{ item.title }}</h2>
        <p>{{ item.description }}</p>
      </article>
    </section>

    <section class="split-section">
      <div class="section-copy">
        <p class="eyebrow">AI Manual Library</p>
        <h2>把维修手册变成门店可用的知识资产。</h2>
        <p>
          支持维修资料上传、OCR 识别、人工审核、车型挂接和标准作业卡回写。
          技师查询时，可以围绕车型、项目、症状和标准规格快速找到可靠资料。
        </p>
      </div>
      <div class="system-board">
        <span>资料上传</span>
        <span>结构化识别</span>
        <span>车型挂接</span>
        <span>AI 查询</span>
      </div>
    </section>
  </main>
</template>

<script setup>
const capabilities = [
  {
    kicker: 'Workflow',
    title: '接车到交车的工单流程',
    description: '客户车辆建档、项目选择、报价确认、施工记录和完工体检完整串联。',
  },
  {
    kicker: 'Archive',
    title: '客户与车辆档案',
    description: '车主、车辆、历史工单、保养建议和服务记录沉淀下来，复购不再靠记忆。',
  },
  {
    kicker: 'Library',
    title: '标准车型与配件库',
    description: '管理车型、标准规格、服务套餐、配件型号和兼容关系，减少不确定性。',
  },
  {
    kicker: 'Client',
    title: '客户小程序服务',
    description: '客户可查询车辆、工单、健康记录和保养建议，让售后沟通更透明。',
  },
]
</script>

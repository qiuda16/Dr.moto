<template>
  <main>
    <section class="page-hero compact-hero">
      <p class="eyebrow">For Riders</p>
      <h1>你不需要懂每一个零件，但你应该知道你的车经历了什么。</h1>
      <p>
        机车博士用清晰记录连接车主和维修服务，让检测、报价、施工、交车不再散落在聊天记录和口头承诺里。
      </p>
    </section>

    <section class="service-flow">
      <article v-for="item in riderFlow" :key="item.title">
        <span>{{ item.step }}</span>
        <h2>{{ item.title }}</h2>
        <p>{{ item.description }}</p>
      </article>
    </section>

    <section class="split-section dark">
      <div class="section-copy">
        <p class="eyebrow">Your Bike Archive</p>
        <h2>每一台车，都应该被认真记录。</h2>
        <p>
          从基础信息到维修历史，从保养建议到健康记录，车辆档案让车主和门店都能更准确地理解这台车。
        </p>
      </div>
      <div class="minimal-list">
        <span>车辆基础信息</span>
        <span>历史工单</span>
        <span>保养建议</span>
        <span>完工检查</span>
      </div>
    </section>
  </main>
</template>

<script setup>
const riderFlow = [
  {
    step: '01',
    title: '检测有记录',
    description: '问题不是一句“需要修”，而是可以被说明、被保存、被回看。',
  },
  {
    step: '02',
    title: '报价更清楚',
    description: '项目、配件、工时和建议分开呈现，车主知道钱花在哪里。',
  },
  {
    step: '03',
    title: '施工可追踪',
    description: '关键施工节点留下记录，避免取车时只剩一句“已经好了”。',
  },
  {
    step: '04',
    title: '保养有依据',
    description: '基于车辆状态和历史记录给建议，把钱花在真正需要的地方。',
  },
]
</script>

<template>
  <RouterView v-slot="{ Component }">
    <keep-alive include="RealTimePremium">
      <component :is="Component" />
    </keep-alive>
  </RouterView>
</template>
<script setup name="myApp"></script>

<style scoped>
.lof-app {
  padding: 24px;
  box-sizing: border-box;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  overflow-x: auto;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.update-time {
  font-size: 13px;
  color: #999;
  text-align: left;
}
.tool-bar {
  display: flex;
  gap: 12px;
}
button {
  padding: 4px 10px;
  cursor: pointer;
  border-radius: 4px;
  border: 1px solid #ccc;
}
.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  align-items: center;
}
.rate-up {
  color: #f53f3f;
  font-weight: bold;
}
.rate-down {
  color: #009944;
  font-weight: bold;
}
.rate-zero {
  color: #666;
}
.fund-code-link {
  color: #409eff;
  cursor: pointer;
  text-decoration: none;
}
.fund-code-link:hover {
  text-decoration: underline;
}
</style>
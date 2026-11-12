<template>
  <div class="header">
    <div class="mainNav" id="mainNav">
      <div class="box_center cf" style="position: relative; text-align: center; height: 44px; line-height: 48px; color: var(--nv-text-inverse); font-size: 16px;">
        <a class="back_link" href="javascript:void(0)" @click="goBack">&#8249; 返回上一页</a>
        小说精品屋作家管理
      </div>
    </div>
  </div>
</template>

<script>
import { useRouter } from "vue-router";

export default {
  name: "AuthorHeader",
  setup() {
    const router = useRouter();
    const goBack = () => {
      if (window.history.length > 1) {
        router.back();
      } else {
        router.push({ name: "home" });
      }
    };
    return { goBack };
  },
};
</script>

<style scoped>
.back_link {
  position: absolute;
  left: 20px;
  top: 0;
  height: 44px;
  line-height: 44px;
  color: var(--nv-text-inverse);
  font-size: 14px;
  text-decoration: none;
}
.back_link:hover {
  color: var(--nv-nav-back-hover);
}
</style>
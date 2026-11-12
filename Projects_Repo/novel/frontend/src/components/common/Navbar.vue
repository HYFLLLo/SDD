 <template>
  <div class="mainNav" id="mainNav">
    <div class="box_center cf">
      <ul class="nav" id="navModule">
        <li><router-link :to="{ name: 'home' }">首页</router-link></li>
        <li>
          <router-link :to="{ name: 'bookclass' }"> 全部作品 </router-link>
        </li>
        <li><router-link :to="{ name: 'bookRank' }">排行榜</router-link></li>
        <li><router-link :to="{ name: 'bookUpload' }">上传图书</router-link></li>
        <li v-if="isAdmin"><router-link :to="{ name: 'bookManage' }">书籍管理</router-link></li>
        <li v-if="isAdmin"><router-link :to="{ name: 'myUpload' }">我的上传</router-link></li>
        <!--<li class=""><a href="/pay/index.html">充值</a></li>-->
        <li><a @click="goAuthor" href="javascript:void(0)">作家专区</a></li>
      </ul>
    </div>
  </div>
</template>

<script>
import { reactive, toRefs, onMounted, ref, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { getToken, getAdmin} from "@/utils/auth";
import {getAuthorStatus} from "@/api/author"
export default {
  name: "Navbar",
  setup() {
    const route = useRoute();
    const router = useRouter();
    const checkAdmin = () => Boolean(getToken()) && String(getAdmin()).toLowerCase() === 'true';
    const isAdmin = ref(checkAdmin());
    watch(() => route.fullPath, () => {
      isAdmin.value = checkAdmin();
    });
    const goAuthor = async () => {
      if (!getToken()) {
        router.push({
          name: "login",
        });
        return;
      }

      const {data} = await getAuthorStatus();
      if(data === null){
          router.push({
          name: "authorRegister",
        });
        return;
      }

      router.push({
        name: "authorBookList",
      });
    };
    return {
      goAuthor,
      isAdmin,
    };
  },
};
</script>

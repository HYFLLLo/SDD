<template>
  <Header />
  <div class="main box_center cf">
    <div class="userBox cf">
      <div class="uploadBox">
        <div class="uploadTitle">上传图书</div>
        <el-form
          :model="form"
          label-width="90px"
          class="uploadForm"
          status-icon
        >
          <el-form-item label="选择文件" prop="file">
            <el-upload
              class="upload-demo"
              :auto-upload="false"
              :limit="1"
              accept=".txt,.epub"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :on-exceed="handleExceed"
            >
              <el-button type="primary">
                <el-icon class="el-icon--right"><Loading /></el-icon>
                选择文件
              </el-button>
              <template #tip>
                <div class="el-upload__tip">支持 .txt / .epub 文件，大小不超过 100MB</div>
              </template>
            </el-upload>
          </el-form-item>

          <el-form-item label="书名" prop="bookName">
            <el-input v-model="form.bookName" placeholder="请输入书名" maxlength="50" />
          </el-form-item>

          <el-form-item label="作者" prop="authorName">
            <el-input v-model="form.authorName" placeholder="作者名（选填）" maxlength="50" />
          </el-form-item>

          <el-form-item label="作品方向" prop="workDirection">
            <el-select v-model="form.workDirection" placeholder="请选择作品方向" @change="loadCategory">
              <el-option label="男频" :value="0" />
              <el-option label="女频" :value="1" />
            </el-select>
          </el-form-item>

          <el-form-item label="分类" prop="categoryId">
            <el-select v-model="form.categoryId" placeholder="请选择分类" style="width: 200px" filterable>
              <el-option
                v-for="item in categoryList"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="简介" prop="bookDesc">
            <el-input
              v-model="form.bookDesc"
              type="textarea"
              :rows="5"
              maxlength="500"
              show-word-limit
              placeholder="书籍简介（选填）"
            />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="submitting" @click="submitUpload">上传</el-button>
            <el-button @click="resetForm">重置</el-button>
          </el-form-item>
        </el-form>

        <div v-if="submitting" class="uploadProgress">
          <el-progress :percentage="uploadPercent" :stroke-width="12" striped />
          <div class="uploadProgressText">
            {{ uploadPercent >= 100 ? '文件已上传，正在解析...' : '正在上传 ' + uploadPercent + '%' }}
          </div>
        </div>

        <div v-if="resultText" class="uploadResult">
          <el-result
            v-if="resultType === 'success'"
            icon="success"
            :title="resultText"
            :sub-title="'共解析 ' + chapterCount + ' 章 / ' + wordCount + ' 字'"
          >
            <template #extra>
              <el-button type="primary" @click="goRead">立即阅读</el-button>
            </template>
          </el-result>
          <el-result v-else icon="error" :title="resultText" sub-title="未写入任何数据，请重试" />
        </div>
      </div>
    </div>
  </div>

  <Footer />
</template>

<script>
import "@/assets/styles/book.css";
import { reactive, toRefs, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { listCategorys, uploadBook } from "@/api/book";
import Header from "@/components/common/Header";
import Footer from "@/components/common/Footer";

export default {
  name: "bookUpload",
  components: {
    Header,
    Footer,
  },
  setup() {
    const router = useRouter();

    const state = reactive({
      form: {
        file: null,
        bookName: "",
        authorName: "",
        workDirection: 0,
        categoryId: null,
        categoryName: "",
        bookDesc: "",
      },
      categoryList: [],
      submitting: false,
      uploadPercent: 0,
      resultText: "",
      resultType: "",
      chapterCount: 0,
      wordCount: 0,
      bookId: null,
    });

    const loadCategory = async () => {
      if (state.form.workDirection === null || state.form.workDirection === undefined) return;
      const { data } = await listCategorys({ workDirection: state.form.workDirection });
      state.categoryList = data || [];
      state.form.categoryId = state.categoryList.length ? state.categoryList[0].id : null;
      state.form.categoryName = state.categoryList.length
        ? state.categoryList[0].name
        : "";
    };

    const handleFileChange = (uploadFile) => {
      state.form.file = uploadFile.raw || uploadFile;
    };

    const handleFileRemove = () => {
      state.form.file = null;
    };

    const handleExceed = () => {
      ElMessage.warning("最多只能上传一个文件");
    };

    const buildFormData = () => {
      const fd = new FormData();
      fd.append("file", state.form.file);
      fd.append("bookName", state.form.bookName.trim());
      if (state.form.authorName && state.form.authorName.trim()) {
        fd.append("authorName", state.form.authorName.trim());
      }
      fd.append("workDirection", state.form.workDirection);
      fd.append("categoryId", state.form.categoryId);
      fd.append("categoryName", state.form.categoryName);
      if (state.form.bookDesc && state.form.bookDesc.trim()) {
        fd.append("bookDesc", state.form.bookDesc.trim());
      }
      return fd;
    };

    const updateUploadProgress = (progressEvent) => {
      if (!progressEvent || !progressEvent.total) {
        return;
      }
      state.uploadPercent = Math.min(
        100,
        Math.round((progressEvent.loaded * 100) / progressEvent.total)
      );
    };

    const submitUpload = () => {
      if (!state.form.file) {
        ElMessage.warning("请选择 .txt 或 .epub 文件");
        return;
      }
      if (!state.form.bookName || !state.form.categoryId) {
        ElMessage.warning("请填写书名并选择分类");
        return;
      }
      state.submitting = true;
      state.uploadPercent = 0;
      state.resultText = "";
      state.resultType = "";
      uploadBook(buildFormData(), updateUploadProgress)
        .then((res) => {
          state.resultType = "success";
          state.resultText = res.data.message || "上传成功";
          state.chapterCount = res.data.chapterCount;
          state.wordCount = res.data.wordCount;
          state.bookId = res.data.bookId;
          ElMessage.success("上传成功，共解析 " + state.chapterCount + " 章");
        })
        .catch((err) => {
          state.resultType = "error";
          // 后端通过 RestResp 返回错误 message（A0702/A0703/A0704/A0705/A0706）
          state.resultText = (err && err.message) || "上传失败";
        })
        .finally(() => {
          state.submitting = false;
          state.uploadPercent = 0;
        });
    };

    const goRead = () => {
      if (state.bookId) {
        router.push({ path: `/book/${state.bookId}` });
      }
    };

    const resetForm = () => {
      state.form.file = null;
      state.form.bookName = "";
      state.form.authorName = "";
      state.form.bookDesc = "";
      state.form.categoryId = null;
      state.form.categoryName = "";
      state.uploadPercent = 0;
      state.resultText = "";
      state.resultType = "";
      state.chapterCount = 0;
      state.wordCount = 0;
    };

    onMounted(() => {
      loadCategory();
    });

    return {
      ...toRefs(state),
      loadCategory,
      handleFileChange,
      handleFileRemove,
      handleExceed,
      submitUpload,
      goRead,
      resetForm,
    };
  },
};
</script>

<style scoped>
.uploadBox {
  max-width: 640px;
  margin: 40px auto;
  padding: 20px 30px 30px;
  background: var(--nv-bg-container);
  border-radius: 6px;
}
.uploadTitle {
  font-size: 20px;
  color: var(--nv-text-primary);
  text-align: center;
  margin-bottom: 24px;
}
.uploadForm {
  margin: 0 auto;
  max-width: 480px;
}
.uploadResult {
  margin-top: 20px;
}
.uploadProgress {
  margin-top: 8px;
}
.uploadProgressText {
  margin-top: 8px;
  color: var(--nv-text-secondary);
  font-size: 13px;
  text-align: center;
}
.el-upload__tip {
  color: var(--nv-text-weak);
  line-height: 1.6;
}
</style>

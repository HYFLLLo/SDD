# 测试报告：T-001 上传配置与接口骨架

**测试时间**：2026-09-04 16:10 ~ 16:16
**Tester Agent ID**：Tester (Claude Code subagent)

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | application.yml 中 spring.servlet.multipart.max-file-size 和 max-request-size 已设置为 100MB | PASS | `src/main/resources/application.yml` 第 17-20 行：`max-file-size: 100MB`、`max-request-size: 100MB` |
| 2 | application.yml 中 novel.file.upload.path 已改为 Windows 可用路径（如 D:/novel-upload） | PASS | `src/main/resources/application.yml` 第 244 行：`path: D:/novel-upload` |
| 3 | 后端启动后，POST /api/front/resource/book/upload 接口可访问（返回占位响应或参数校验错误，不报 404） | PASS | 真实 curl 验证：(a) 不带参数 → HTTP 200 + `{"code":"A0400","message":"用户请求参数错误","data":null,"ok":false}`；(b) 带齐必填字段与文件 → HTTP 200 + `{"code":"00000","message":"一切 ok","data":{"bookId":null,"bookName":"test","chapterCount":null,"wordCount":null,"message":"接口骨架就绪，功能开发中"},"ok":true}`。均为 RestResp 格式，非 404 |

## Developer 产出文件核对

| 文件 | 存在 | 编译产物 |
|------|------|----------|
| `src/main/resources/application.yml` | 是 | - |
| `src/main/java/.../constant/ErrorCodeEnum.java`（A0702~A0706） | 是（第 130-150 行） | ErrorCodeEnum.class |
| `src/main/java/.../dto/req/BookUploadReqDto.java` | 是 | BookUploadReqDto.class |
| `src/main/java/.../dto/resp/BookUploadRespDto.java` | 是 | BookUploadRespDto.class + $Builder.class |
| `src/main/java/.../service/BookUploadService.java` | 是 | BookUploadService.class |
| `src/main/java/.../service/impl/BookUploadServiceImpl.java` | 是 | BookUploadServiceImpl.class |
| `src/main/java/.../controller/front/BookUploadController.java` | 是 | BookUploadController.class |

## 代码质量抽检

- 新增文件无 TODO/FIXME/HACK 残留
- 新增文件无硬编码密钥/密码
- 导入路径正确（`io.github.xxyopen.novel.core.common.resp.RestResp`、`ApiRouterConsts`、Swagger、Jakarta Validation、Spring Web 注解）
- ErrorCodeEnum 已注册 A0702~A0706（5 个新错误码），位置在 A0700/A0701 之后、SYSTEM_ERROR 之前
- `BookUploadController` 路由 = `API_FRONT_RESOURCE_URL_PREFIX`（即 `/api/front/resource`）+ `book/upload` = `/api/front/resource/book/upload`，与 AC3 一致
- `BookUploadServiceImpl.uploadBook` 为占位实现，返回 `RestResp.ok(BookUploadRespDto.builder()...message("接口骨架就绪，功能开发中").build())`，符合 T-001「接口骨架」定位

## 动态验证过程

1. 首次启动发现 `target/novel-3.5.1-SNAPSHOT.jar` 不含 T-001 新增类（Developer 仅运行 `mvnw compile`，未重新 `package`），导致首次 curl 返回 404
2. 停止进程后执行 `mvnw.cmd -q clean package -DskipTests` 重新打包，确认 JAR 内包含全部 6 个 T-001 `.class` 文件
3. 重启后 curl 验证 AC3 通过（见上表）
4. 验证完毕后停止 Spring Boot 进程，未保留后台运行

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | A0702（文件大小超限）由 Spring `MaxUploadSizeExceededException` 抛出，需 `CommonExceptionHandler` 将其映射为 A0702，否则会被兜底为 B0001 | T-002 联调范围 | Developer 已说明，T-002 实现时处理 |
| 2 | `application.yml` 中存在多处明文密钥（SiliconFlow API Key、Elasticsearch 密码、RabbitMQ 地址、SBA 账密、JWT secret），均为 T-001 之前既有 | 历史遗留 | 建议后续任务统一迁移到环境变量或外部配置，不在 T-001 范围 |
| 3 | JDK 实际路径为 `D:\tools\jdk21\jdk-21.0.12.1+1`（嵌套一层），与任务描述 `D:\tools\jdk21` 不一致 | 环境信息 | 仅影响自动化脚本，不影响判定 |

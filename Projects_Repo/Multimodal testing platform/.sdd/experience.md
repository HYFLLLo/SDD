# 项目经验

> 当前项目长期有效的经验。  
> Developer / Tester / Bugfix 在任务完成后维护本文件。

---

## Harness 系统经验摘要

新项目开始时，Developer / Tester / Bugfix 需要同时参考：

- 当前项目经验：`.sdd/experience.md`
- 系统级经验：`<Harness 根目录>/memory/harness-experience.md`

---

（项目经验将在开发过程中追加）

## 项目经验

- Windows 下用文件锁做单实例时，被锁字节区其他进程读不到；持锁者信息必须另写
  独立 JSON 文件，锁文件只负责互斥。
- 单实例判定不能依赖「端口上是否有本应用」：端口被占、换端口启动都会误判。
  显式锁 + PID 存活检测 + 陈旧锁接管才是可靠路径。
- `git rev-parse --short` 在部分环境需要显式 `HEAD`，否则构建元信息里的提交号为空。
- 打包期生成信息文件（如 `build_info.json`）应在 spec 里写盘并加入 datas，
  避免 datas 指向不存在文件导致构建失败。
- 批量规范化换行/BOM 前先限定文件清单，否则会把无关仓库文件一并改动，
  产生大规模无意义 diff。
- 测试与生产日志目录要可切换：日志器缓存了 handler 时会继续写旧工作区，
  需要按目标路径判断并重建。

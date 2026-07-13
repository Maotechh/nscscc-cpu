# Draft PR：活动 RegFile SpinalHDL 等价替换

状态：`implementation_in_review`。不自动创建、ready 或 merge；Claude review unavailable，且官方 baseline/mixed smoke 均 FAIL。

本 PR 只替换活动 `regfile.v`，不迁移 `regfile_dual.v`，不做性能优化。实现 commit `41b93e5ca0b9239a8277f268441abb75e9d92215`，证据 commit `1fc62c2c6728ab2304b092ef65de26ee629a3686`，分支已推送但未创建或合并 PR。验证、overlay、资源和回退结论以本迭代日志为准。官方 `func_lab19` 两次均在相同基线首错处失败，不能声明功能 PASS。

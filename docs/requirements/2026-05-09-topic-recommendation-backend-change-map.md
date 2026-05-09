# 选题分析与推荐后端改动对照文档

## 文档目的

本文档用于说明本轮“老师录题后生成题目画像、学生基于画像获得推荐结果”的后端改动范围，明确：

- 契约改了什么
- 后端实现改了什么
- 前端后续应如何对接
- 当前方案为什么符合论文逻辑

## 本轮目标

本轮采用“最少改动但论文逻辑完整”的方案：

- 不新增老师分析接口
- 不让推荐接口直接调用大模型
- 继续复用已有 `topics` 创建/更新链路
- 继续复用已有 `keyword_jobs` 队列
- 将 `keyword_jobs` 的语义从“关键词抽取”提升为“题目画像分析”
- 推荐模块继续保持“规则排序 + 可解释输出”

## 契约改动

本轮已修改 [spec/contract.yaml](/d:/毕业设计/spec/contract.yaml)。

### 1. 学生画像字段

原先 `student_profile` 为宽松 object。

现在明确为结构化字段：

- `interests: string[]`
- `skills: string[]`
- `keywords: string[]`
- `goal: string | null`
- `weekly_hours: integer | null`

涉及 schema：

- `UserMe.student_profile`
- `PatchUserMeRequest.student_profile`

### 2. 题目画像字段

原先 `Topic.portrait` 只有：

- `keywords`
- `extracted_at`

现在扩展为：

- `keywords`
- `difficulty_label`
- `difficulty_reason`
- `required_capabilities`
- `suitable_students`
- `risks`
- `summary`
- `extracted_at`

### 3. 推荐解释字段

原先 `RecommendationTopicItem.explain` 只有：

- `matched_skills`
- `matched_keywords`
- `reasons`

现在新增：

- `matched_capabilities`
- `difficulty_fit`
- `capacity_status`
- `warnings`

### 4. 接口文案语义更新

已同步更新接口说明文案：

- `POST /topics`
- `PATCH /topics/{topic_id}`
- `GET /recommendations/topics`

新的语义重点是：

- `topics` 保存后异步生成题目画像
- `recommendations/topics` 基于学生画像与题目画像规则排序

## 后端实现改动

### 1. 题目画像模型映射

文件：

- [app/topic/model/__init__.py](/d:/毕业设计/app/topic/model/__init__.py)

改动内容：

- 扩展 `TopicPortraitStored`
- 增加 `_ensure_str_list`
- 扩展 `contract_portrait_from_json`
- 让 `Topic.to_topic()` 能返回完整画像字段

结果：

- 数据库存储的 `portrait_json` 可以直接映射为新的 `Topic.portrait`

### 2. 题目画像 job 写回

文件：

- [app/task/keyword_jobs.py](/d:/毕业设计/app/task/keyword_jobs.py)

改动内容：

- 保留原有 job payload 和调用入口
- 在写回前新增本地结构化分析逻辑
- 写回 `portrait_json` 时不再只写关键词
- 改为写入完整画像：
  - 关键词
  - 难度
  - 能力要求
  - 适合学生
  - 风险提示
  - 总结说明

结果：

- 教师创建或更新题目后，异步 job 完成时能得到结构化画像

### 3. 推荐服务增强

文件：

- [app/recommendations/service/recommend_service.py](/d:/毕业设计/app/recommendations/service/recommend_service.py)

改动内容：

- 保持推荐域不直接调 LLM
- 继续使用只读规则打分
- 从学生画像中读取：
  - `skills`
  - `keywords`
  - `interests`
  - `goal`
  - `weekly_hours`
- 从题目画像中读取：
  - `keywords`
  - `required_capabilities`
  - `difficulty_label`
- 增强 explain 输出：
  - `matched_capabilities`
  - `difficulty_fit`
  - `capacity_status`
  - `warnings`

结果：

- 推荐结果不再只是分数和词交集
- 现在可以向前端提供更适合答辩展示的解释字段

## 当前链路如何工作

### 老师侧

1. 教师调用 `POST /topics` 或 `PATCH /topics/{topic_id}`
2. 后端同步保存基础题目信息
3. 后端入队 `keyword_jobs`
4. Worker 消费后生成结构化题目画像
5. `GET /topics/{topic_id}` 返回完整 `portrait`

### 学生侧

1. 学生通过 `PATCH /users/me` 保存 `student_profile`
2. 前端调用 `GET /recommendations/topics?term_id=...&explain=true`
3. 后端基于学生画像和题目画像做规则排序
4. 返回 Top-N 推荐及 explain 字段

## 为什么这套方案适合论文

这套方案的逻辑是清晰的：

- 大模型负责老师录题后的语义分析
- 规则负责学生侧推荐排序
- 结果具备可解释字段
- 过程能与真实选题业务对应

相比“推荐接口直接调用大模型”，当前方案有几个优点：

- 更符合现有后端架构约束
- 更容易测试和联调
- 更容易在论文中解释“模型负责分析，规则负责决策支持”
- 更适合答辩时说明系统边界

## 当前实现边界

需要明确的是，本轮后端虽然已经补齐了契约和实现主干，但 `keyword_jobs` 内部的结构化分析目前仍是基于规则和文本信号生成，并不是严格意义上的稳定 JSON 大模型输出解析。

也就是说：

- 当前已经具备“题目画像分析”的实现形态
- 但如果后续要进一步增强论文说服力，仍建议把 `app/use_cases/topic_keywords.py` 升级成真正的结构化 LLM 输出编排

## 前端下一步对接建议

前端可以按下面顺序切换：

1. Topics 老师分析页不再使用本地演示分析函数
2. 直接读取 `GET /topics/{topic_id}` 的 `portrait`
3. 学生推荐页不再用本地推荐试算
4. 改为保存 `student_profile` 后调用 `/recommendations/topics`

这样可以让当前前端页面从“演示版”平滑切到“真实联调版”。

## 本轮验证

本轮后端已完成验证：

- `pytest tests/test_topic_portraits_model.py tests/test_keyword_jobs.py tests/test_recommend_service.py tests/test_recommendations_api.py tests/test_topic_service.py -q`
- `pytest tests/spec/test_contract_schema_instances.py -q`
- `pytest`

结果：

- `695 passed`

## 一句话总结

本轮已经把“选题分析与推荐”从前端演示概念，推进到了“后端契约明确、题目画像可返回、推荐解释可输出”的可联调阶段，后续只需继续把前端页面切换到真实接口即可形成完整闭环。

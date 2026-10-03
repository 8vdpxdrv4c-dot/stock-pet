# PIPELINE_STATE — trading-psychology

## 当前阶段
**全部完成（阶段 0–5）— 14 个 skill 已安装到项目级 `.cursor/skills/`，DIGEST 已发布**

## 书籍元信息
- slug: `trading-psychology`
- 标题: 投资交易心理分析（典藏版）
- 作者: 布雷特·N. 斯蒂恩博格（Brett N. Steenbarger）
- 出版年: 2018（初版 2002/2003）
- 来源: `投资交易心理分析.pdf` → `book.txt`（500 页，pypdf 逐页提取）

## 阶段 checklist

- [x] **阶段 0** Adler 整书理解 → `BOOK_OVERVIEW.md`（用户已确认，聚焦交易执行/复盘类）
- [x] **阶段 1** 5 extractor 并行提取 → `candidates/`（23 框架 / 58 原则 / 40 案例 / 20 反例 / 25 术语）
- [x] **阶段 1.5** 三重验证 → `verified.md`（14 个通过）+ `rejected/`（5 个淘汰/合并）（用户已确认 14 个）
- [x] **阶段 2** RIA++ 构造 skills → 14 个 `*/SKILL.md`（2026-08-18 完成）
- [x] **阶段 3** Zettelkasten → `INDEX.md` + `GLOSSARY.md`（2026-08-18 完成）
- [x] **阶段 4** 压力测试 → 14 个 `*/test-prompts.json` + `_blind/` 盲测（2026-08-18 完成）
  - 14 个技能 × 6 条（3 触发 + 2 诱饵 + 1 边界）共 84 条测试
  - 全部 should_trigger / should_not_trigger 判定正确（诱饵均转向同书兄弟技能或 NONE）
  - edge 案例仅 1 处合理边界分歧（stress-inoculation edge-01 判给 internal-observer）
  - 通过率：13 个 100%（6/6），1 个 83%（5/6，含合理分歧）
- [x] **阶段 5** `DIGEST.md`（约 6100 字）+ 安装到项目级 `.cursor/skills/`（2026-08-18 完成）

## 通过验证的 14 个技能单元（v01-v14）与产出目录
1. v01 大无畏的交易清单 / 一致性复盘 → `fearless-trading-inventory/`
2. v02 聚焦解决方案 / 找特例 → `solution-focused-trading/`
3. v03 内部观察员 / 情绪即数据 → `internal-observer-emotion-data/`
4. v04 情绪温度测量 / 状态不对不交易 → `emotional-temperature-gate/`
5. v05 压力预防 / 脑海放电影 → `stress-inoculation-rehearsal/`
6. v06 触发器识别 → 消极自我对话 → 交易教练 → `trigger-and-trading-coach/`
7. v07 止损纪律（三分法 / 保本 / 失败即成本）→ `stop-loss-discipline/`
8. v08 交易计划 = 船锚（说出来 / 假设检验 / 先锋头寸）→ `trading-plan-anchor/`
9. v09 元信息传递 / 市场语言（怎么走）→ `market-meta-communication/`
10. v10 状态换挡（环境 / 姿势 / 跳跃）→ `state-shifting/`
11. v11 新意→改变→巩固 / 三类转换策略 → `novelty-change-consolidation/`
12. v12 逆向交易 / 弹球窍门 → `contrarian-pinball-edge/`
13. v13 交易-性格匹配 / 理想交易者建模 → `trading-personality-match/`
14. v14 内隐学习 / 沉浸式训练 → `implicit-learning-immersion/`

## 淘汰的候选（rejected/）
- 情感多元化（用户偏好：生活通用类）
- 梦/白日梦作为情感交流（V3 常识 + 用户偏好）
- 左右脑/脑裂/希弗眼镜（V3 不足 + 时代局限）
- 危机作为催化剂（范围过窄，跳跃已并入 v10/v11）
- 声光机器/生物反馈设备（时代局限）

## 更新时间
2026-08-18

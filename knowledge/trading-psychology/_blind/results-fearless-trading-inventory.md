# 盲测评审结果 — fearless-trading-inventory

## should-trigger-01
- activated_skill: fearless-trading-inventory
- reason: 用户要求系统性复盘全年交易历史，"一赚钱就亏回去"指向仓位/清仓等环节的重复性失误，正是本技能核心场景——逐笔对照成功与失败交易、找五维不一致，而非盯着盈亏数字。
- if_triggered_action: 先让用户导出/整理全部交易记录，按仓位、准备、执行、角度、清仓五个维度逐笔对照盈利与亏损交易。

## should-trigger-02
- activated_skill: fearless-trading-inventory
- reason: "每笔交易都有理由仍稳定亏钱"几乎逐字命中技能触发器：这正是需要一次性、不美化地审查全部交易历史、找出执行不一致缺口（而非提供即兴建议）的场景。
- if_triggered_action: 引导用户整理完整交易清单，逐笔标注当时理由与实际结果，对照五维找出一致性缺口，优先定位最反复出现的错误。

## should-trigger-03
- activated_skill: fearless-trading-inventory
- reason: 用户明确拥有交易日志并要求检验"交易一致性"，直接命中技能用途（借日志逐笔对照成败交易找不一致），且 Triggers 含"日志/一致性"，符合激活条件。
- if_triggered_action: 读取其交易日志，按五个维度统计一致与不一致之处，指出具体证据并定位最严重缺口，再逐项给修正建议。

## should-not-trigger-01
- activated_skill: state-shifting
- reason: 止损已执行完毕，问题不在止损纪律或历史复盘，而是止损后的沮丧情绪将人锁死、需即时"换挡"恢复思考，正属 state-shifting 用身体动作改变状态的场景。
- if_triggered_action: 先带用户做一次身体状态调整（起身活动、改变姿势、调整呼吸节奏），把情绪与思维从"难受"中抽离，再评估是否继续交易。

## should-not-trigger-02
- activated_skill: NONE
- reason: 用户要的是具体个股当日"买还是卖"的买卖点建议，属于纯行情/操作咨询；14 个技能均明确不适用于具体买卖点，也非心理或行为干预场景。
- if_triggered_action: 不激活技能，直接说明无法给出个股买卖点建议，引导其回到交易计划、止损规则或市场元信息解读框架。

## should-not-trigger-03
- activated_skill: trading-personality-match
- reason: "系统完善但实盘执行不了、怀疑心态问题"正是该技能触发条件：很多"情绪问题"实为方法-性格结构错配，需用 A/B 类综合征定位注意力风格并做理想交易者建模。
- if_triggered_action: 先做性格-方法匹配诊断，判断其属 A 类冲动分散还是 B 类过度僵化，区分结构错配与执行缺口后再定干预方向。

## edge-01
- activated_skill: fearless-trading-inventory
- reason: 技能适用于"有交易历史时的系统性复盘"，5 笔虽少仍可逐笔对照五维找不一致，属边界情形；但用户有日志可审，仍应激活，同时提示样本局限。
- if_triggered_action: 逐笔复盘这 5 笔交易的五维表现，指出已可识别的不一致点，并提醒样本量小、结论需更多交易验证后才可靠。

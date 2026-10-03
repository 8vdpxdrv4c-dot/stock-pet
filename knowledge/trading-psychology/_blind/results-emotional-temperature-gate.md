# 盲测评审结果 — emotional-temperature-gate

> 盲测执行：仅依据 all-skills.md 的 14 个技能 name+description 与 emotional-temperature-gate 的 SKILL.md 判断，未参考任何 test-prompts.json 或预期答案。

## should-trigger-01

- activated_skill: emotional-temperature-gate
- reason: "心情很烦躁"+"该不该开仓"双双命中情绪温度闸门的语言信号（心情烦躁/今天该不该开仓）——这正是"状态不对就不交易"的实时闸门场景，而非问买卖点或止损。状态判断优先于方法归属，internal-observer 只管观察机制，此处是闸门判断。
- if_triggered_action: 引导用户按 0–10 给激发水平（无聊0↔亢奋10）与效价（消极0↔积极10）打分并描述身体信号，对照危险清单判定是否适合开仓。

## should-trigger-02

- activated_skill: emotional-temperature-gate
- reason: 用户在问"交易前如何判断状态对不对"，即想建立"状态不对就不交易"的自检机制，正是本技能的核心应用；internal-observer 的描述明确注明"今天状态对不对的即时判断"归 emotional-temperature-gate。
- if_triggered_action: 教他量化测量情绪温度（激发×效价），设定开盘前、每个交易时段、情绪波动时各测一次的节奏，并明确命中危险状态时的行动（离场/缩仓/暂停）。

## should-trigger-03

- activated_skill: emotional-temperature-gate
- reason: 开盘前"没什么状态"纠结是硬做还是休息，命中"没状态/今天适合交易吗"触发词；本技能核心规则"状态不适配就不交易、先无害再盈利"恰好给出该场景的决策标准。
- if_triggered_action: 测量此刻情绪温度，若无聊/低落命中危险区间，明确建议休息或暂缓开仓，把"状态不适配"写成当天不开仓的正式依据。

## should-not-trigger-01

- activated_skill: stop-loss-discipline
- reason: 用户问的是"怎么设止损"，是止损规则本身的设计问题，命中 stop-loss-discipline 触发词（止损/做不到位），不属于交易前状态闸门；emotional-temperature-gate 明确不适用于止损数值咨询。
- if_triggered_action: 讲解三分法止损体系（基于价格/市场指标/时间），把止损重新定义为"假设被证伪"，帮他预先写死一套可执行、不靠临场意志的止损规则。

## should-not-trigger-02

- activated_skill: NONE
- reason: 用户在要市场涨跌的方向预测，这既落在 emotional-temperature-gate 的"不适用于：市场方向判断"边界内，也不属于其余 13 个技能（market-meta-communication 解读的是趋势元信息而非预测涨跌）。
- if_triggered_action: 不激活任何技能；回绝涨跌预测，说明这属于市场分析而非交易心理范畴，可引导用户关注可验证的市场解读框架而非押方向。

## edge-01

- activated_skill: emotional-temperature-gate
- reason: 状态"一般般"、模糊不定时问"能交易吗"，正是闸门要处理的边缘案例——不能凭笼统感觉拍板，需量化测量激发水平与效价后对照清单判断；internal-observer 的区分注释也指向此处归属温度闸门。
- if_triggered_action: 让他先打出两组 0–10 分数（激发/效价）并描述身体状态，若均落在适宜区间才允许交易；任一逼近危险边界则建议暂缓或缩仓。

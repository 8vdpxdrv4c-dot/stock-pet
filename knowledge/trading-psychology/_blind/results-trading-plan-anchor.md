# 盲测结果 — trading-plan-anchor

## should-trigger-01
- activated_skill: trading-plan-anchor
- reason: 盘中总被临时消息带跑、问如何坚持计划，精确命中 trading-plan-anchor 的 Triggers（盘中总被带跑/怎么坚持计划）；核心正是把成文计划当船锚、大声说出使其客观化，而非讲止损规则。
- if_triggered_action: 让他把计划写成一句话可证伪假设并开市前大声朗读，盘中被消息打断时先回到这条假设再决定动作。

## should-trigger-02
- activated_skill: trading-plan-anchor
- reason: 直接问开盘前准备什么，命中 trading-plan-anchor 的触发器；该技能正是教开市前把计划成文、说出并作为盘中锚，而非讲买卖点或止损规则本身。
- if_triggered_action: 引导开市前五分钟成文：入场理由、止损位、可证伪条件、目标，并大声说出计划使其客观化。

## should-trigger-03
- activated_skill: trading-plan-anchor
- reason: 小仓位试判断正是交易计划中的先锋头寸"投石问路"机制：把交易当科学假设，先小仓验证再决定加仓，命中 trading-plan-anchor 而非其他情绪/复盘技能。
- if_triggered_action: 帮他写下该判断的可证伪条件、先锋头寸规模上限与验证时限，再据验证结果决定是否加仓。

## should-not-trigger-01
- activated_skill: fearless-trading-inventory
- reason: 要求审查历史交易找止损不一致，命中 fearless-trading-inventory 的复盘/一致性/交易记录触发器；用户要的是系统比对不一致而非止损规则本身，故不用 stop-loss-discipline。
- if_triggered_action: 导出全部历史交易逐笔核对是否按计划止损，统计不一致分布，对照成功交易找出清仓维度的差距。

## should-not-trigger-02
- activated_skill: NONE
- reason: 问个股下周涨跌属于预测/方向咨询，14 个技能均不覆盖；市场元信息、计划、止损等均明确排除具体选股与买卖点咨询。
- if_triggered_action: 不激活任何技能；先澄清真实需求：是想知道该不该持仓（可转计划/止损），还是纯预测闲聊。

## edge-01
- activated_skill: trading-plan-anchor
- reason: 有计划却不看，问题不在计划缺失而在计划未"大声说出"使其客观化——正是 trading-plan-anchor 的核心方法：书写本身不是锚，说出口才是。
- if_triggered_action: 要求把计划压缩成一句核心假设，开盘前朗读，并设盘中检查点（价格触及假设条件即回看计划）。

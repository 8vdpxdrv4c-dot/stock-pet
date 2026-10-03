# 盲测评审结果 — novelty-change-consolidation

## should-trigger-01
- activated_skill: novelty-change-consolidation
- reason: "学了新方法几周后打回原形"正是技能描述的核心场景"学新方法但几周后打回原形"，属典型改变复发，需用"新意+巩固"两阶段模型解释为何光有新意不够。
- if_triggered_action: 先帮用户确认新方法是否经过状态绑定的重复内化，用两阶段模型指出缺的是巩固，再制定每日重复演练清单。

## should-trigger-02
- activated_skill: novelty-change-consolidation
- reason: "改变总是维持不住"直接命中技能触发词"改变维持不住/change doesn't stick"，用户想理解改变为何难以保持，正是该技能要回答的巩固缺失问题。
- if_triggered_action: 用新意+巩固两阶段框架解释改变维持不住的内在机制，引导用户找出自己缺少巩固环节的具体表现，规划持续重复计划。

## should-trigger-03
- activated_skill: novelty-change-consolidation
- reason: "如何让新习惯固定下来不反弹"是巩固阶段的方法诉求，技能核心正是改变如何在状态绑定的重复中内化固定，属于直接命中。
- if_triggered_action: 讲解巩固需要多次重复与持续努力，帮用户设计状态绑定的重复场景，把新习惯嵌入具体交易情境中反复演练。

## should-not-trigger-01
- activated_skill: trigger-and-trading-coach
- reason: "一亏就上头、现在就想打断"是单次触发情境下的即时失控，命中该技能"一亏就上头/又失控了"触发词，且 novelty-change-consolidation 明确将单次触发打断排除。
- if_triggered_action: 引导用户识别"触发器→消极自我对话→错误行动"三步链条，找出亏损触发点，用"交易教练"角色替换消极磁带。

## should-not-trigger-02
- activated_skill: NONE
- reason: 用户问波段还是趋势，属交易风格的方法论选择咨询，无复发、无执行困难、无情绪失控信号，未命中任何技能的触发场景，故选 NONE。
- if_triggered_action: 不激活技能；可提示风格选择需结合其交易系统与执行特点评估，建议补充系统情况后另行分析。

## edge-01
- activated_skill: novelty-change-consolidation
- reason: 用户坚持三周仍在巩固期，问是否需继续，技能核心正是"巩固需要多次重复+持续努力"，该问题落在巩固阶段内，属边缘命中。
- if_triggered_action: 确认其仍处巩固阶段，用两阶段模型说明巩固期的正常时长与持续要求，给出继续重复与回落预警的检查点。

# 盲测结果 — trading-personality-match

## should-trigger-01
- activated_skill: trading-personality-match
- reason: 用户系统完善但实盘执行不了，并自我怀疑"是不是心态问题"，正是本技能核心场景：很多"情绪问题"其实是性格与方法不匹配的"结构问题"。
- if_triggered_action: 先不急于定性为心态问题，引导用户用 A/B 类综合征定位注意力风格，判断现有系统是否与性格匹配，再决定调整方法还是调整系统。

## should-trigger-02
- activated_skill: trading-personality-match
- reason: 机械交易不顺手导致用户怀疑自己"不适合做交易"，技能明确覆盖"机械系统 vs 自由裁量"与"性格适合什么方法"，属于方法-性格匹配问题而非纯心理问题。
- if_triggered_action: 与用户核对机械系统不顺手的具体环节（入场自由度/节奏），对照自由裁量特征，判断其偏机械还是偏直觉，再定制匹配的执行框架。

## should-trigger-03
- activated_skill: trading-personality-match
- reason: 用户直接询问自己是冲动型还是分析型，对应技能中 A/B 类综合征（冲动分散 vs 过度僵化）的注意力风格定位，正是本技能的核心诊断功能。
- if_triggered_action: 先介绍 A/B 类综合征的判断标准（冲动分散 vs 过度僵化）让其对号入座，再根据定位出的风格推荐匹配的交易方法。

## should-not-trigger-01
- activated_skill: fearless-trading-inventory
- reason: 止损执行不一致属于执行维度缺口，技能明确指示此类系统性复盘应使用 fearless-trading-inventory 逐笔对照五维度查找不一致，而非 trading-personality-match。
- if_triggered_action: 调出完整交易历史，逐笔对照仓位/准备/执行/角度/清仓五个维度，标记止损不一致的具体场景与重复模式。

## should-not-trigger-02
- activated_skill: NONE
- reason: 用户询问具体市场方向（多空判断），属行情咨询；多个技能明确排除"买卖点/方向判断"，14 个技能均无此能力，故不激活任何技能。
- if_triggered_action: 不激活任何技能，向用户说明方向判断属于行情分析范畴，建议其基于已有交易系统与书面计划自行决策。

## edge-01
- activated_skill: trading-personality-match
- reason: 用户已测出 A 类但担忧做不好交易，技能核心正是用 A/B 类定位风格并说明方法匹配即可——A 类冲动分散风格可用机械化规则约束补偿，并非劣势。
- if_triggered_action: 先破除"冲动=做不好"的误解，说明 A 类可通过机械规则与外部约束补偿，再为用户设计匹配该风格的具体执行方式。

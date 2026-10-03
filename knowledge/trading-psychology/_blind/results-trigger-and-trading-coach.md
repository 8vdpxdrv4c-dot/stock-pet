# 盲测评审结果 — trigger-and-trading-coach

## should-trigger-01
- activated_skill: trigger-and-trading-coach
- reason: 一亏就上头、控制不住想加仓翻本，正是反复在同一情境失控的自动化坏行为，直接命中该技能"一亏就上头、控制不住自己"的触发词，属典型触发器驱动模式。
- if_triggered_action: 先陪用户拆解"亏损→上头→加仓翻本"三步链：定位触发器、辨识自动播放的消极自我对话，再引入交易教练口吻替换磁带。

## should-trigger-02
- activated_skill: trigger-and-trading-coach
- reason: 每次错过机会就追高，是同一类情境反复失控的自动化行为（类似兴奋后乱买），用户明确要"打断这个习惯"，正是该技能打断自动化坏行为的核心目标。
- if_triggered_action: 带用户识别"错过→追高"的触发点，捕捉其间自动播放的消极对话，设计交易教练话术替换，并演练新的打断动作。

## should-trigger-03
- activated_skill: trigger-and-trading-coach
- reason: "脑子里有个声音"是该技能的明确触发词，对应三步模型中的消极自我对话磁带；"我做不了交易"正是需要辨识并替换的磁带内容，而非单纯情绪问题。
- if_triggered_action: 先辨识这个声音出现的时机与具体内容，确认触发情境，再引导用户以交易教练角色对学生版自己说替代性话语。

## should-not-trigger-01
- activated_skill: novelty-change-consolidation
- reason: 坏习惯反复复发、想彻底改掉，指向"改变维持不住、打回原形"的复发主题，属新意足够但巩固不足，应激活 novelty-change-consolidation，而非单次触发打断。
- if_triggered_action: 诊断改变为何不巩固：确认是否缺重复与状态绑定，帮用户制定多次重复练习、把新模式内化的巩固计划。

## should-not-trigger-02
- activated_skill: NONE
- reason: "交易没意思、该不该退出"属动机与生涯层面的困惑，14 个技能均聚焦交易执行与心理干预，无匹配项，强行激活反而会错置问题。
- if_triggered_action: 不激活技能；先共情倾听，澄清"没意思"源于短期状态还是长期价值感问题，再决定是否需要交易以外的支持。

## edge-01
- activated_skill: trigger-and-trading-coach
- reason: 用户在复盘中识别出"一亏就上头"的重复模式，并直接询问是否算触发器，这正是该技能第一步"识别触发器"的典型入口，边缘情况但应激活。
- if_triggered_action: 确认这就是触发器，随即走完三步：锁定触发情境、辨识自动播放的消极磁带、用交易教练角色替换，并验证完整链条。

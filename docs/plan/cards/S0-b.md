# S0-b 数据画像与 γ₀、λ₀

- 周次：W1 评估地基（11/16 周一 – 11/22 周日）
- 线：研究线
- 估时：0.5 天
- 依赖：S0-a

## 提示词

写 scripts/profile_data.py，只读 data/processed/IS/，输出 results/profile/IS.json 和 figures/profile/ 下 5 张图：
评分分布；用户训练交互数分布（对数坐标）；用户内相邻交互间隔分布（单位天，对数坐标）；测试物品是否在训练集出现过的比例；用户内评分是否全部相同的比例。
JSON 另外给出：相邻间隔中位数（天）、训练集交互年龄中位数（以训练集最大时间戳为参照，天）、由它们算出的 γ0 = ln2 / 间隔中位数、λ0 = ln2 / 年龄中位数，每个数字附一句计算口径。
图同时导出 SVG 和 600dpi PNG，中文宋体、西文 Times New Roman，字号 10.5pt，样式写成 scripts/plot_style.py 供以后所有图复用。
脚本末尾断言用户数、物品数、交互数与 stats.json 一致。TH、OP 只算 JSON 不画图。

## 产出
results/profile/{IS,TH,OP}.json；figures/profile/*.svg|png；scripts/plot_style.py

## 验收
JSON 字段齐全；5 张图存在；断言通过

## 论文落点
第 3 章数据集小节、数据画像图；γ 和 λ 取值依据（替代 V8 的 γ=0.3、λ=0.001 经验值）

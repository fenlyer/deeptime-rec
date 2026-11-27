# T-ch4 第四章数据回填

- 周次：W5（12/18 – 12/22）
- 线：写作线
- 估时：0.5 天
- 依赖：S-rank-* 全部完成

## 目标

将排序实验数据填入 V9 论文第四章。

## 回填清单

| 表格 | 数据来源 | 状态 |
|-----|---------|------|
| 表 4-1 | S-rank-base + S-rank-newbase（排序基线汇总） | ⏳ 待实验 |
| 表 4-2 | S-rank-base + S-rank-main + S-rank-distill + S-rank-newbase | ⏳ 待实验 |
| 表 4-5 | S-rank-distill（消融2行）+ S-rank-main（消融3行） | ⏳ 待实验 |
| 表 4-6 | S-rank-distill（教师质量：AUC/Brier/校准曲线） | ⏳ 待实验 |

## 简化说明

以下表格推迟到后续整改：
- 表 4-3（端到端）：需要完整系统
- 表 4-4（全链路冷启动）：需要端到端数据
- 表 4-7（蒸馏敏感性）：仅留"本文设定值"一行，不扫

## 产出

- `thesis/src/ch4_rank.md` 数据回填完成
- `thesis/generated/numbers_ch4.json`

## 验收

- [ ] 表 4-1、4-2、4-5、4-6 数据已填入
- [ ] 数字与结果文件一致

# E-serve 原型服务实现

- 周次：W3-W4（12/08 – 12/18）
- 线：工程线
- 估时：3 天
- 依赖：S-recall-main（需要模型产物）

## 资源需求

| 类型 | 说明 |
|-----|------|
| **GPU** | ❌ 不需要（CPU 推理） |
| **SSH** | 不需要（本机开发） |
| **时长** | ≈ 2 天编码 + 1 天调试 |

## 目标

实现推荐服务 API，供系统评测使用。

## 实现

### 目录结构

```
serving/
├── app.py              # FastAPI 应用
├── pipeline.py         # 推荐管线
├── models/
│   ├── recall.py       # 召回（FAISS）
│   ├── rank.py         # 排序（PyTorch）
│   └── rerank.py       # 重排
└── cache.py            # 缓存
```

### 核心接口

```python
@app.get("/recommend/{user_id}")
def recommend(user_id: str, top_k: int = 20):
    # 1. 召回 Top-300
    # 2. 排序 Top-30
    # 3. 语义重排 Top-20
    return {"items": [...]}
```

## 产出

- `serving/` 目录完整实现
- `docs/api.md` 接口文档

## 简化说明

- 不做 RAG 解释（推迟）
- 不做前端（用 curl 测试）

## 验收

- [ ] API 可启动
- [ ] `/recommend/{user_id}` 返回正确结果
- [ ] 延迟 < 100ms（单并发）

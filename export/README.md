# export/ — 产物导出

- **用途**：从 checkpoint 导出原型所需的嵌入、ID 映射、FAISS 索引。
- **输入**：RecBole checkpoint、ID 映射文件。
- **产出**：`artifacts/{version}/` 下的 `user_emb.npy`、`item_emb.npy`、`id_map.json`、`faiss.index`、`manifest.json`。

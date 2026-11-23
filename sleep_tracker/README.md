# Sleep Tracker Core Service & OpenAPI Spec

本模块实现了每日睡眠时长记录的核心领域模型、打卡逻辑、数据校验、统计分析及 OpenAPI/Swagger 契约导出。

## 功能特性

1. **跨天归属日计算 (`calculate_attributed_date`)**：
   - 支持跨日夜间睡眠与当日午睡/小憩的归属日判定（标准健康应用 Wake-up Date 统计日归属）。
2. **入睡 / 醒来打卡机制**：
   - 实时入睡打卡 (`check_in_sleep`)：校验当前是否存在进行中状态，防止重复打卡。
   - 实时醒来打卡 (`check_out_wake`)：闭合睡眠区间，自动计算睡眠时长（分钟）与归属日。
3. **补录与重叠校验 (`add_manual_record` / `check_overlap`)**：
   - 校验历史与当前进行中区间的冲突，覆盖全包含、前重叠、后重叠与包裹等所有冲突场景。
4. **7/30 天趋势查询 (`query_trend`)**：
   - 聚合区间内总睡眠时长、日均睡眠时长、记录天数、单日最长/最短睡眠及每日明细。
5. **OpenAPI / Swagger 规范规范化契约导出**：
   - 符合 OpenAPI 3.0.3 标准。
   - 导出目录：`specs/openapi.yaml` 及 `specs/openapi.json`。

## 目录结构

```
sleep_tracker/
├── models.py              # 领域模型定义与校验
├── service.py             # 核心业务服务与趋势聚合逻辑
├── openapi_exporter.py    # OpenAPI 3.0.3 规范生成与导出脚本
├── pytest.ini             # 测试配置
├── specs/
│   ├── openapi.yaml       # 导出的 OpenAPI 3.0.3 YAML 契约
│   └── openapi.json       # 导出的 OpenAPI 3.0.3 JSON 契约
└── tests/
    └── test_sleep_tracker.py # 完整自动化测试用例集（13个测试全覆盖）
```

## 测试与导出运行

```bash
# 激活虚拟环境
source venv/bin/activate

# 导出 OpenAPI 契约文档
python openapi_exporter.py

# 运行自动化单测
pytest -v
```

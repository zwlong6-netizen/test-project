"""OpenAPI 3.0.3 Specification Definition and Exporter for Sleep Tracker API.
"""
import json
import yaml
from pathlib import Path


OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Sleep Tracker Core API (每日睡眠时长记录服务)",
        "version": "1.0.0",
        "description": (
            "提供每日睡眠时长记录核心功能接口，涵盖跨天归属日计算、实时入睡/醒来打卡、"
            "手动补录、时间段重叠防冲突校验，以及 7/30 天周期趋势聚合统计分析。"
        ),
        "contact": {
            "name": "Sleep Tracker Team",
            "email": "support@sleeptracker.example.com"
        }
    },
    "servers": [
        {
            "url": "https://api.sleeptracker.example.com/v1",
            "description": "Production Server"
        },
        {
            "url": "http://localhost:8000/v1",
            "description": "Local Development Server"
        }
    ],
    "paths": {
        "/sleep/check-in": {
            "post": {
                "summary": "入睡打卡",
                "description": "用户准备入睡时打卡，创建进行中的睡眠会话。若当前已有进行中的会话则拒绝打卡。",
                "operationId": "checkInSleep",
                "tags": ["Sleep Tracking"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/CheckInRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "入睡打卡成功",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/SleepRecordResponse"
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "参数错误或存在时间重叠冲突",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    },
                    "409": {
                        "description": "冲突：已有进行中的睡眠打卡",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/sleep/check-out": {
            "post": {
                "summary": "醒来打卡",
                "description": "用户醒来时打卡，完成正在进行中的睡眠会话，自动计算总时长与跨天归属日。",
                "operationId": "checkOutWake",
                "tags": ["Sleep Tracking"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/CheckOutRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "醒来打卡成功，返回完整闭合睡眠记录",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/SleepRecordResponse"
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "参数错误或时间冲突（醒来时间早于入睡时间）",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    },
                    "404": {
                        "description": "未找到进行中的睡眠打卡",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/sleep/records/manual": {
            "post": {
                "summary": "手动补录睡眠记录",
                "description": "支持补录历史睡眠，自动验证区间有效性、重叠校验以及跨天归属日计算。",
                "operationId": "addManualSleepRecord",
                "tags": ["Sleep Tracking"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ManualRecordRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "补录记录成功",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/SleepRecordResponse"
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "无效的时间区间（例如醒来时间早于入睡时间）",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    },
                    "409": {
                        "description": "时间冲突：补录区间与已有睡眠记录重叠",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/sleep/trend": {
            "get": {
                "summary": "7/30 天睡眠趋势查询",
                "description": "查询指定周期（7天或30天）的每日睡眠趋势、总时长、平均时长、极值及统计分析。",
                "operationId": "getSleepTrend",
                "tags": ["Analytics & Trend"],
                "parameters": [
                    {
                        "name": "user_id",
                        "in": "query",
                        "required": True,
                        "description": "用户ID",
                        "schema": {
                            "type": "string"
                        }
                    },
                    {
                        "name": "days",
                        "in": "query",
                        "required": True,
                        "description": "趋势统计天数，支持 7 或 30 天",
                        "schema": {
                            "type": "integer",
                            "enum": [7, 30]
                        }
                    },
                    {
                        "name": "end_date",
                        "in": "query",
                        "required": False,
                        "description": "统计截止日期（YYYY-MM-DD），默认为今天",
                        "schema": {
                            "type": "string",
                            "format": "date"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "趋势聚合数据返回成功",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/SleepTrendResponse"
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "无效的天数参数或日期格式错误",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    "components": {
        "schemas": {
            "CheckInRequest": {
                "type": "object",
                "required": ["user_id"],
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "用户ID",
                        "example": "user_1001"
                    },
                    "sleep_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "入睡时间（ISO 8601）。缺省默认为当前服务器时间",
                        "example": "2026-11-23T23:30:00+08:00"
                    },
                    "notes": {
                        "type": "string",
                        "description": "打卡备注",
                        "example": "睡前喝了牛奶"
                    }
                }
            },
            "CheckOutRequest": {
                "type": "object",
                "required": ["user_id"],
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "用户ID",
                        "example": "user_1001"
                    },
                    "wake_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "醒来时间（ISO 8601）。缺省默认为当前服务器时间",
                        "example": "2026-11-24T07:15:00+08:00"
                    },
                    "notes": {
                        "type": "string",
                        "description": "醒来感受或备注",
                        "example": "精神饱满"
                    }
                }
            },
            "ManualRecordRequest": {
                "type": "object",
                "required": ["user_id", "start_time", "end_time"],
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "用户ID",
                        "example": "user_1001"
                    },
                    "start_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "入睡时间（ISO 8601）",
                        "example": "2026-11-22T23:10:00+08:00"
                    },
                    "end_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "醒来时间（ISO 8601）",
                        "example": "2026-11-23T06:50:00+08:00"
                    },
                    "attributed_date": {
                        "type": "string",
                        "format": "date",
                        "description": "自定义归属日（YYYY-MM-DD）。如不传则按跨天唤醒日逻辑自动计算",
                        "example": "2026-11-23"
                    },
                    "notes": {
                        "type": "string",
                        "description": "补录原因或备注",
                        "example": "补录昨晚睡眠"
                    }
                }
            },
            "SleepRecordResponse": {
                "type": "object",
                "required": ["id", "user_id", "start_time", "record_type", "status"],
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "睡眠记录ID",
                        "example": "rec_9823fbc01"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "用户ID",
                        "example": "user_1001"
                    },
                    "start_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "入睡时间",
                        "example": "2026-11-23T23:30:00+08:00"
                    },
                    "end_time": {
                        "type": "string",
                        "format": "date-time",
                        "nullable": True,
                        "description": "醒来时间",
                        "example": "2026-11-24T07:15:00+08:00"
                    },
                    "attributed_date": {
                        "type": "string",
                        "format": "date",
                        "nullable": True,
                        "description": "睡眠归属统计日",
                        "example": "2026-11-24"
                    },
                    "record_type": {
                        "type": "string",
                        "enum": ["REALTIME", "MANUAL"],
                        "description": "打卡方式（实时打卡/手动补录）"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["IN_PROGRESS", "COMPLETED"],
                        "description": "状态（进行中/已完成）"
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "nullable": True,
                        "description": "睡眠时长（分钟）",
                        "example": 465
                    },
                    "notes": {
                        "type": "string",
                        "nullable": True,
                        "description": "备注信息"
                    }
                }
            },
            "SleepTrendSummary": {
                "type": "object",
                "properties": {
                    "total_minutes": {"type": "integer", "example": 3290},
                    "total_hours": {"type": "number", "example": 54.83},
                    "average_daily_minutes": {"type": "number", "example": 470.0},
                    "average_daily_hours": {"type": "number", "example": 7.83},
                    "recorded_days": {"type": "integer", "example": 7},
                    "average_recorded_day_minutes": {"type": "number", "example": 470.0},
                    "max_day": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "format": "date", "example": "2026-11-20"},
                            "total_minutes": {"type": "integer", "example": 510},
                            "total_hours": {"type": "number", "example": 8.5}
                        }
                    },
                    "min_day": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "format": "date", "example": "2026-11-21"},
                            "total_minutes": {"type": "integer", "example": 420},
                            "total_hours": {"type": "number", "example": 7.0}
                        }
                    }
                }
            },
            "DailyTrendItem": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "format": "date", "example": "2026-11-23"},
                    "total_minutes": {"type": "integer", "example": 465},
                    "total_hours": {"type": "number", "example": 7.75},
                    "sessions_count": {"type": "integer", "example": 1},
                    "sessions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "start_time": {"type": "string", "format": "date-time"},
                                "end_time": {"type": "string", "format": "date-time"},
                                "duration_minutes": {"type": "integer"},
                                "record_type": {"type": "string"}
                            }
                        }
                    }
                }
            },
            "SleepTrendResponse": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "example": "user_1001"},
                    "period_days": {"type": "integer", "example": 7},
                    "start_date": {"type": "string", "format": "date", "example": "2026-11-17"},
                    "end_date": {"type": "string", "format": "date", "example": "2026-11-23"},
                    "summary": {"$ref": "#/components/schemas/SleepTrendSummary"},
                    "daily_trends": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/DailyTrendItem"}
                    }
                }
            },
            "ErrorResponse": {
                "type": "object",
                "required": ["code", "message"],
                "properties": {
                    "code": {
                        "type": "string",
                        "example": "OVERLAP_CONFLICT"
                    },
                    "message": {
                        "type": "string",
                        "example": "与已有睡眠记录重叠"
                    },
                    "details": {
                        "type": "object",
                        "nullable": True
                    }
                }
            }
        }
    }
}


def export_openapi_specs(output_dir: Path):
    """导出 OpenAPI 规范为 YAML 与 JSON 两种标准格式"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    yaml_path = output_dir / "openapi.yaml"
    json_path = output_dir / "openapi.json"

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(OPENAPI_SPEC, f, allow_unicode=True, sort_keys=False, indent=2)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(OPENAPI_SPEC, f, ensure_ascii=False, indent=2)

    print(f"Exported OpenAPI YAML: {yaml_path}")
    print(f"Exported OpenAPI JSON: {json_path}")
    return yaml_path, json_path


if __name__ == "__main__":
    export_openapi_specs(Path(__file__).parent / "specs")

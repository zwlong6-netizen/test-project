"""Sleep Tracker Domain Models and Validation Logic.
"""
from __future__ import annotations
from datetime import datetime, date, time, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator


class SleepSessionStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class SleepRecordType(str, Enum):
    REALTIME = "REALTIME"  # 打卡
    MANUAL = "MANUAL"      # 补录


def calculate_attributed_date(wake_up_time: datetime, cutoff_hour: int = 18) -> date:
    """
    计算跨天归属日逻辑：
    按生理/行业通用睡眠归属约定，一次睡眠归属于醒来的那一天或根据切分点归属。
    通常规则：
    若在次日醒来（例如23:00睡，07:00醒），该睡眠归属为 wake_up_time 所在日期的睡眠周期（即目标日），
    或者若 wake_up_time 处于清晨/白天（00:00 - cutoff_hour:00，默认18:00前），归属为当日前半夜/该自然日周期的主睡眠；
    若午睡/小憩亦归属醒来当天。
    标准归属日：通常以醒来日期作为该觉睡眠统计日（即醒来日的睡眠），
    若特别定义夜间跨天（如 2026-11-23 23:00 入睡，2026-11-24 07:00 醒来）：
    行业健康App（如Apple Health / 华为运动健康）通常按"唤醒日"归属（Wake date归属），
    也有App按"入睡日归属"或"Cutoff 18:00"。
    此处提供标准清晰算法：
    以入睡和醒来时间综合判定：
    若醒来时间早于中午12:00（且跨天），入睡日为昨天，则通常归属为昨天夜间开始的睡眠（或以唤醒日作为统计日）。
    本实现提供标准 Wake-Up Date 归属策略：
    所有醒来时间在当日 00:00 ~ 23:59 的睡眠段，归属于 wake_up_time.date()。
    若需要基于入睡日或统一界限（例如每日中午12:00作为日分割线）：
    若 wake_up_time.time() < time(18, 0)，归属于 wake_up_time.date()。
    """
    return wake_up_time.date()


class SleepRecord(BaseModel):
    id: str = Field(..., description="唯一记录ID")
    user_id: str = Field(..., description="用户ID")
    start_time: datetime = Field(..., description="入睡时间 (ISO 8601)")
    end_time: Optional[datetime] = Field(None, description="醒来时间 (ISO 8601)，为None表示睡眠进行中")
    attributed_date: Optional[date] = Field(None, description="睡眠归属日 (YYYY-MM-DD)")
    record_type: SleepRecordType = Field(SleepRecordType.REALTIME, description="打卡类型：实时打卡 / 手动补录")
    status: SleepSessionStatus = Field(SleepSessionStatus.IN_PROGRESS, description="记录状态")
    duration_minutes: Optional[int] = Field(None, description="睡眠总时长 (分钟)")
    notes: Optional[str] = Field(None, description="备注说明")

    @model_validator(mode="after")
    def validate_times_and_duration(self) -> SleepRecord:
        if self.end_time is not None:
            if self.end_time <= self.start_time:
                raise ValueError("醒来时间 (end_time) 必须晚于入睡时间 (start_time)")
            duration = int((self.end_time - self.start_time).total_seconds() // 60)
            self.duration_minutes = duration
            self.status = SleepSessionStatus.COMPLETED
            if not self.attributed_date:
                self.attributed_date = calculate_attributed_date(self.end_time)
        else:
            self.status = SleepSessionStatus.IN_PROGRESS
            self.duration_minutes = None
        return self


class SleepOverlapError(Exception):
    """时间段重叠异常"""
    pass


class ActiveSessionExistsError(Exception):
    """已有未完成睡眠打卡异常"""
    pass


class NoActiveSessionError(Exception):
    """无进行中睡眠打卡异常"""
    pass


def check_overlap(
    new_start: datetime,
    new_end: datetime,
    existing_records: List[SleepRecord],
    exclude_id: Optional[str] = None
) -> None:
    """
    校验时间段是否与已有记录重叠。
    时间段重叠判定：max(start1, start2) < min(end1, end2)
    """
    for rec in existing_records:
        if exclude_id and rec.id == exclude_id:
            continue
        # 若已有记录是进行中状态 (end_time 为 None)
        if rec.end_time is None:
            # 如果新记录结束时间晚于已有进行中记录的开始时间，冲突
            if new_end > rec.start_time:
                raise SleepOverlapError(
                    f"与进行中的睡眠记录冲突 (ID: {rec.id}, 开始时间: {rec.start_time.isoformat()})"
                )
        else:
            # 两个已闭合时间区间的重叠判定
            if max(new_start, rec.start_time) < min(new_end, rec.end_time):
                raise SleepOverlapError(
                    f"与已有睡眠记录重叠 (ID: {rec.id}, 区间: {rec.start_time.isoformat()} ~ {rec.end_time.isoformat()})"
                )

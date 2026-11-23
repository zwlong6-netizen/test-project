"""Sleep Tracker Service - Core Business Logic.
"""
from __future__ import annotations
import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
from collections import defaultdict

from models import (
    SleepRecord,
    SleepRecordType,
    SleepSessionStatus,
    SleepOverlapError,
    ActiveSessionExistsError,
    NoActiveSessionError,
    check_overlap,
    calculate_attributed_date,
)


class SleepTrackerService:
    def __init__(self):
        # 内存存储结构：user_id -> List[SleepRecord]
        self.records: Dict[str, List[SleepRecord]] = defaultdict(list)

    def check_in_sleep(self, user_id: str, sleep_time: Optional[datetime] = None, notes: Optional[str] = None) -> SleepRecord:
        """
        入睡打卡：开启一个进行中的睡眠会话。
        若已有进行中的会话，则抛出 ActiveSessionExistsError。
        """
        now = sleep_time or datetime.now()
        user_records = self.records[user_id]
        
        # 检查是否有未结束的睡眠记录
        for r in user_records:
            if r.status == SleepSessionStatus.IN_PROGRESS:
                raise ActiveSessionExistsError(f"用户 {user_id} 已有进行中的睡眠记录 (ID: {r.id})，请先唤醒打卡")

        # 检查是否与历史记录重叠（入睡时间不能落在已完成的历史区间内）
        for r in user_records:
            if r.end_time and r.start_time <= now < r.end_time:
                raise SleepOverlapError(f"入睡打卡时间 {now.isoformat()} 落在历史记录区间内 (ID: {r.id})")

        record = SleepRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            start_time=now,
            end_time=None,
            record_type=SleepRecordType.REALTIME,
            status=SleepSessionStatus.IN_PROGRESS,
            notes=notes,
        )
        user_records.append(record)
        return record

    def check_out_wake(self, user_id: str, wake_time: Optional[datetime] = None, notes: Optional[str] = None) -> SleepRecord:
        """
        醒来打卡：结束最近一个进行中的睡眠会话。
        """
        now = wake_time or datetime.now()
        user_records = self.records[user_id]
        
        active_rec = None
        for r in user_records:
            if r.status == SleepSessionStatus.IN_PROGRESS:
                active_rec = r
                break
        
        if not active_rec:
            raise NoActiveSessionError(f"用户 {user_id} 没有进行中的睡眠打卡记录")

        if now <= active_rec.start_time:
            raise ValueError(f"醒来时间 ({now.isoformat()}) 不能早于或等于入睡时间 ({active_rec.start_time.isoformat()})")

        # 校验新产生的闭合区间 [active_rec.start_time, now] 是否与其他记录冲突
        check_overlap(active_rec.start_time, now, user_records, exclude_id=active_rec.id)

        # 更新记录
        active_rec.end_time = now
        active_rec.status = SleepSessionStatus.COMPLETED
        active_rec.duration_minutes = int((now - active_rec.start_time).total_seconds() // 60)
        active_rec.attributed_date = calculate_attributed_date(now)
        if notes:
            active_rec.notes = (active_rec.notes + " | " + notes) if active_rec.notes else notes

        return active_rec

    def add_manual_record(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        attributed_date: Optional[date] = None,
        notes: Optional[str] = None
    ) -> SleepRecord:
        """
        补录睡眠记录：包含严格时间顺序校验和重叠校验。
        """
        if end_time <= start_time:
            raise ValueError("醒来时间 (end_time) 必须晚于入睡时间 (start_time)")

        user_records = self.records[user_id]
        # 校验重叠
        check_overlap(start_time, end_time, user_records)

        target_date = attributed_date or calculate_attributed_date(end_time)
        record = SleepRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            attributed_date=target_date,
            record_type=SleepRecordType.MANUAL,
            status=SleepSessionStatus.COMPLETED,
            notes=notes,
        )
        user_records.append(record)
        return record

    def get_user_records(self, user_id: str) -> List[SleepRecord]:
        """获取用户所有记录，按开始时间正序排列"""
        return sorted(self.records[user_id], key=lambda x: x.start_time)

    def query_trend(self, user_id: str, days: int, end_date: Optional[date] = None) -> Dict:
        """
        查询 7 天或 30 天睡眠趋势统计：
        - 每日总睡眠时长（分钟及小时）
        - 每日睡眠次数
        - 期间平均睡眠时长
        - 最长/最短单日睡眠
        - 达标天数（如标准睡眠 >= 7小时 / 420分钟）
        """
        if days not in (7, 30):
            raise ValueError("趋势查询目前仅支持 7 天或 30 天")

        target_end = end_date or date.today()
        target_start = target_end - timedelta(days=days - 1)

        user_records = self.records[user_id]
        
        # 按归属日聚合完成的睡眠记录
        daily_duration_map = defaultdict(int)
        daily_count_map = defaultdict(int)
        daily_records_map = defaultdict(list)

        for r in user_records:
            if r.status == SleepSessionStatus.COMPLETED and r.attributed_date:
                if target_start <= r.attributed_date <= target_end:
                    daily_duration_map[r.attributed_date] += (r.duration_minutes or 0)
                    daily_count_map[r.attributed_date] += 1
                    daily_records_map[r.attributed_date].append({
                        "id": r.id,
                        "start_time": r.start_time.isoformat(),
                        "end_time": r.end_time.isoformat() if r.end_time else None,
                        "duration_minutes": r.duration_minutes,
                        "record_type": r.record_type.value,
                    })

        # 连续日期序列构建
        daily_stats = []
        total_duration = 0
        recorded_days = 0

        curr = target_start
        while curr <= target_end:
            curr_dur = daily_duration_map[curr]
            curr_count = daily_count_map[curr]
            if curr_count > 0:
                recorded_days += 1
            total_duration += curr_dur

            daily_stats.append({
                "date": curr.isoformat(),
                "total_minutes": curr_dur,
                "total_hours": round(curr_dur / 60.0, 2),
                "sessions_count": curr_count,
                "sessions": daily_records_map[curr]
            })
            curr += timedelta(days=1)

        avg_daily_minutes = round(total_duration / days, 1)
        avg_recorded_minutes = round(total_duration / recorded_days, 1) if recorded_days > 0 else 0

        max_stat = max(daily_stats, key=lambda x: x["total_minutes"])
        min_recorded_stat = min([s for s in daily_stats if s["sessions_count"] > 0], key=lambda x: x["total_minutes"], default=None)

        return {
            "user_id": user_id,
            "period_days": days,
            "start_date": target_start.isoformat(),
            "end_date": target_end.isoformat(),
            "summary": {
                "total_minutes": total_duration,
                "total_hours": round(total_duration / 60.0, 2),
                "average_daily_minutes": avg_daily_minutes,
                "average_daily_hours": round(avg_daily_minutes / 60.0, 2),
                "recorded_days": recorded_days,
                "average_recorded_day_minutes": avg_recorded_minutes,
                "max_day": {
                    "date": max_stat["date"],
                    "total_minutes": max_stat["total_minutes"],
                    "total_hours": max_stat["total_hours"]
                },
                "min_day": {
                    "date": min_recorded_stat["date"] if min_recorded_stat else None,
                    "total_minutes": min_recorded_stat["total_minutes"] if min_recorded_stat else 0,
                    "total_hours": min_recorded_stat["total_hours"] if min_recorded_stat else 0
                }
            },
            "daily_trends": daily_stats
        }

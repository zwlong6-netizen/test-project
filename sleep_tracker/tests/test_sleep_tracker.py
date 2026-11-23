"""Comprehensive Automated Unit & Contract Tests for Sleep Tracker.
"""
import pytest
from datetime import datetime, date, timedelta
from pathlib import Path
import json
import yaml

from models import (
    SleepRecord,
    SleepRecordType,
    SleepSessionStatus,
    SleepOverlapError,
    ActiveSessionExistsError,
    NoActiveSessionError,
    calculate_attributed_date,
    check_overlap,
)
from service import SleepTrackerService
from openapi_exporter import OPENAPI_SPEC, export_openapi_specs


@pytest.fixture
def service():
    return SleepTrackerService()


class TestCrossDayAttributedDate:
    """跨天归属日计算测试"""

    def test_overnight_sleep_attributed_date(self):
        # 2026-11-23 23:00 入睡，2026-11-24 07:00 醒来
        wake_time = datetime(2026, 11, 24, 7, 0)
        attr_date = calculate_attributed_date(wake_time)
        assert attr_date == date(2026, 11, 24)

    def test_nap_same_day_attributed_date(self):
        # 午睡：当天 13:00 入睡，14:30 醒来
        wake_time = datetime(2026, 11, 24, 14, 30)
        attr_date = calculate_attributed_date(wake_time)
        assert attr_date == date(2026, 11, 24)


class TestRealtimeCheckInOut:
    """实时入睡 / 醒来打卡测试"""

    def test_normal_check_in_and_check_out(self, service):
        user_id = "user_001"
        start = datetime(2026, 11, 23, 23, 30)
        end = datetime(2026, 11, 24, 7, 30)

        # 1. 入睡打卡
        rec = service.check_in_sleep(user_id=user_id, sleep_time=start, notes="准备入睡")
        assert rec.status == SleepSessionStatus.IN_PROGRESS
        assert rec.end_time is None
        assert rec.duration_minutes is None

        # 2. 醒来打卡
        completed_rec = service.check_out_wake(user_id=user_id, wake_time=end, notes="醒来打卡")
        assert completed_rec.id == rec.id
        assert completed_rec.status == SleepSessionStatus.COMPLETED
        assert completed_rec.end_time == end
        assert completed_rec.duration_minutes == 480  # 8 hours = 480 min
        assert completed_rec.attributed_date == date(2026, 11, 24)

    def test_duplicate_check_in_fails(self, service):
        user_id = "user_002"
        service.check_in_sleep(user_id=user_id, sleep_time=datetime(2026, 11, 23, 23, 0))
        
        # 未醒来时再次打卡，应抛出 ActiveSessionExistsError
        with pytest.raises(ActiveSessionExistsError):
            service.check_in_sleep(user_id=user_id, sleep_time=datetime(2026, 11, 23, 23, 30))

    def test_check_out_without_check_in_fails(self, service):
        user_id = "user_003"
        with pytest.raises(NoActiveSessionError):
            service.check_out_wake(user_id=user_id, wake_time=datetime(2026, 11, 24, 8, 0))

    def test_check_out_time_before_check_in_fails(self, service):
        user_id = "user_004"
        service.check_in_sleep(user_id=user_id, sleep_time=datetime(2026, 11, 24, 1, 0))
        with pytest.raises(ValueError, match="醒来时间 .* 不能早于或等于入睡时间"):
            service.check_out_wake(user_id=user_id, wake_time=datetime(2026, 11, 24, 0, 30))


class TestManualRecordAndOverlapValidation:
    """补录与时间重叠冲突校验测试"""

    def test_add_manual_record_success(self, service):
        user_id = "user_005"
        start = datetime(2026, 11, 22, 23, 0)
        end = datetime(2026, 11, 23, 6, 30)
        rec = service.add_manual_record(user_id, start, end, notes="手工补录")

        assert rec.status == SleepSessionStatus.COMPLETED
        assert rec.record_type == SleepRecordType.MANUAL
        assert rec.duration_minutes == 450
        assert rec.attributed_date == date(2026, 11, 23)

    def test_overlap_with_existing_completed_record(self, service):
        user_id = "user_006"
        # 存在一段记录: 22:00 ~ 06:00
        service.add_manual_record(
            user_id,
            datetime(2026, 11, 22, 22, 0),
            datetime(2026, 11, 23, 6, 0)
        )

        # 1. 完全包含在其内：23:00 ~ 05:00
        with pytest.raises(SleepOverlapError):
            service.add_manual_record(
                user_id,
                datetime(2026, 11, 22, 23, 0),
                datetime(2026, 11, 23, 5, 0)
            )

        # 2. 前半段重叠：21:00 ~ 23:00
        with pytest.raises(SleepOverlapError):
            service.add_manual_record(
                user_id,
                datetime(2026, 11, 22, 21, 0),
                datetime(2026, 11, 22, 23, 0)
            )

        # 3. 后半段重叠：05:00 ~ 08:00
        with pytest.raises(SleepOverlapError):
            service.add_manual_record(
                user_id,
                datetime(2026, 11, 23, 5, 0),
                datetime(2026, 11, 23, 8, 0)
            )

        # 4. 外层完全包裹：21:00 ~ 07:00
        with pytest.raises(SleepOverlapError):
            service.add_manual_record(
                user_id,
                datetime(2026, 11, 22, 21, 0),
                datetime(2026, 11, 23, 7, 0)
            )

        # 5. 紧挨着（非重叠）应当成功：06:00 ~ 07:00
        rec_ok = service.add_manual_record(
            user_id,
            datetime(2026, 11, 23, 6, 0),
            datetime(2026, 11, 23, 7, 0)
        )
        assert rec_ok.duration_minutes == 60

    def test_overlap_with_in_progress_record(self, service):
        user_id = "user_007"
        service.check_in_sleep(user_id=user_id, sleep_time=datetime(2026, 11, 24, 22, 0))

        # 补录的时间段跨过了正在打卡的开始时间
        with pytest.raises(SleepOverlapError):
            service.add_manual_record(
                user_id,
                datetime(2026, 11, 24, 21, 0),
                datetime(2026, 11, 24, 23, 0)
            )


class TestTrendQuery:
    """7天 / 30天趋势查询接口测试"""

    def test_7_day_trend_query(self, service):
        user_id = "user_trend_7"
        end_date = date(2026, 11, 23)

        # 模拟过去 7 天连续每日睡眠记录（每天 480 分钟 = 8 小时）
        for i in range(7):
            d = end_date - timedelta(days=i)
            # 入睡前一晚 23:00，醒来当天 07:00
            start = datetime(d.year, d.month, d.day, 7, 0) - timedelta(hours=8)
            end = datetime(d.year, d.month, d.day, 7, 0)
            service.add_manual_record(user_id, start, end)

        trend = service.query_trend(user_id=user_id, days=7, end_date=end_date)
        assert trend["user_id"] == user_id
        assert trend["period_days"] == 7
        assert len(trend["daily_trends"]) == 7
        assert trend["summary"]["recorded_days"] == 7
        assert trend["summary"]["total_minutes"] == 7 * 480
        assert trend["summary"]["average_daily_minutes"] == 480.0
        assert trend["summary"]["average_daily_hours"] == 8.0

    def test_30_day_trend_query_with_partial_data(self, service):
        user_id = "user_trend_30"
        end_date = date(2026, 11, 30)

        # 仅有 10 天有睡眠记录
        for i in [1, 2, 5, 10, 15, 20, 22, 25, 28, 29]:
            d = end_date - timedelta(days=i)
            start = datetime(d.year, d.month, d.day, 7, 0) - timedelta(hours=7)
            end = datetime(d.year, d.month, d.day, 7, 0)
            service.add_manual_record(user_id, start, end)

        trend = service.query_trend(user_id=user_id, days=30, end_date=end_date)
        assert trend["period_days"] == 30
        assert len(trend["daily_trends"]) == 30
        assert trend["summary"]["recorded_days"] == 10
        assert trend["summary"]["total_minutes"] == 10 * 420
        assert trend["summary"]["average_recorded_day_minutes"] == 420.0

    def test_invalid_trend_days_raises_error(self, service):
        user_id = "user_invalid"
        with pytest.raises(ValueError, match="仅支持 7 天或 30 天"):
            service.query_trend(user_id, days=15)


class TestOpenAPIContract:
    """OpenAPI 规范契约导出与完整性测试"""

    def test_openapi_spec_export(self, tmp_path):
        yaml_path, json_path = export_openapi_specs(tmp_path)
        assert yaml_path.exists()
        assert json_path.exists()

        # 验证 YAML 解析
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
        assert yaml_data["openapi"] == "3.0.3"
        assert "/sleep/check-in" in yaml_data["paths"]
        assert "/sleep/check-out" in yaml_data["paths"]
        assert "/sleep/records/manual" in yaml_data["paths"]
        assert "/sleep/trend" in yaml_data["paths"]

        # 验证 JSON 解析
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        assert json_data["info"]["title"] == "Sleep Tracker Core API (每日睡眠时长记录服务)"
        assert "SleepRecordResponse" in json_data["components"]["schemas"]
        assert "SleepTrendResponse" in json_data["components"]["schemas"]

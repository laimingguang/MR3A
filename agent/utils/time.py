from __future__ import annotations

import re
from datetime import datetime, time, timedelta
from typing import Any, Dict, Optional, Tuple

import pytz

DEFAULT_TIMEZONE = "Asia/Shanghai"

_WEEKDAY_NAMES: Dict[int, Tuple[str, ...]] = {
    0: ("mon", "monday", "周一", "星期一", "礼拜一"),
    1: ("tue", "tuesday", "周二", "星期二", "礼拜二"),
    2: ("wed", "wednesday", "周三", "星期三", "礼拜三"),
    3: ("thu", "thursday", "周四", "星期四", "礼拜四"),
    4: ("fri", "friday", "周五", "星期五", "礼拜五"),
    5: ("sat", "saturday", "周六", "星期六", "礼拜六"),
    6: ("sun", "sunday", "周日", "周天", "星期日", "星期天", "礼拜日", "礼拜天"),
}


def get_timezone(tz_name: Optional[str] = None):
    return pytz.timezone(tz_name or DEFAULT_TIMEZONE)


def now_in_timezone(tz_name: Optional[str] = None) -> datetime:
    return datetime.now(get_timezone(tz_name))


def parse_weekday(value: Any) -> Optional[int]:
    """
    解析目标星期，返回 Python weekday（0=周一 … 6=周日）。
    支持 0-6 整数、中英文名称；字符串 "1"-"7" 按 ISO（1=周一，7=周日）解析。
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        if 0 <= value <= 6:
            return value
        return None

    if isinstance(value, str):
        text = value.strip().lower()
        if not text:
            return None
        if text.isdigit():
            num = int(text)
            if 1 <= num <= 7:
                return num - 1
            if 0 <= num <= 6:
                return num
            return None
        for weekday, names in _WEEKDAY_NAMES.items():
            if text in names:
                return weekday
        return None

    return None


def parse_time_of_day(param: Dict[str, Any]) -> Optional[time]:
    """
    从参数字典解析时刻，支持：
    - time: "HH:MM" / "H:MM" / "HH:MM:SS"
    - hour + minute + second
    """
    if not param:
        return None

    raw_time = param.get("time")
    if raw_time is not None:
        if isinstance(raw_time, str):
            text = raw_time.strip()
            match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", text)
            if not match:
                return None
            hour, minute, second = int(match.group(1)), int(match.group(2)), int(
                match.group(3) or 0
            )
        else:
            return None
    else:
        hour_raw = param.get("hour")
        if hour_raw is None:
            return None
        try:
            hour = int(hour_raw)
            minute = int(param.get("minute", 0))
            second = int(param.get("second", 0))
        except (TypeError, ValueError):
            return None

    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        return None
    return time(hour=hour, minute=minute, second=second)


def today_at(target: time, now: datetime) -> datetime:
    return now.replace(
        hour=target.hour,
        minute=target.minute,
        second=target.second,
        microsecond=0,
    )


def ms_timestamp_diff_to_dhm(timestamp1_ms, timestamp2_ms):
    """
    将两个毫秒级时间戳的差值转换为天-时-分格式

    参数:
        timestamp1_ms (int): 第一个毫秒时间戳
        timestamp2_ms (int): 第二个毫秒时间戳

    返回:
        str: 格式化为"X天-X时-X分"的字符串
    """
    # 计算时间戳之间的绝对差值（毫秒）
    diff_ms = abs(timestamp2_ms - timestamp1_ms)

    # 转换为秒
    diff_seconds = diff_ms / 1000

    # 计算天、小时、分钟
    days = int(diff_seconds // (24 * 3600))
    remaining_seconds = diff_seconds % (24 * 3600)
    hours = int(remaining_seconds // 3600)
    remaining_seconds %= 3600
    minutes = int(remaining_seconds // 60)

    # 返回中文格式的结果
    return f"{days}天-{hours}时-{minutes}分"


def is_current_period(timestamp_ms, timezone="Asia/Shanghai"):
    """
    判断毫秒级时间戳是否在当前周和当前月

    参数:
        timestamp_ms: 毫秒级时间戳
        timezone: 时区字符串，默认为"Asia/Shanghai"（北京时间）

    返回:
        tuple: (is_current_week, is_current_month)
    """

    tz = pytz.timezone(timezone)
    timestamp_datetime = datetime.fromtimestamp(timestamp_ms / 1000.0, tz)
    now = datetime.now(tz)

    # 计算当前周的开始（本周或上周一05:00:00）
    # Python中，weekday()返回0-6，0是周一，6是周日
    days_since_monday = now.weekday()  # 距离最近过去的周一的天数

    # 计算到本周一的天数
    week_start = now.replace(hour=5, minute=0, second=0, microsecond=0) - timedelta(
        days=days_since_monday
    )

    # 如果当前时间早于周一5点，则使用上周一作为周期开始
    if now.weekday() == 0 and now.hour < 5:  # 如果是周一且不到5点
        week_start = week_start - timedelta(days=7)  # 使用上周一

    # 计算下周一05:00:00作为本周结束
    week_end = week_start + timedelta(days=7)

    # 计算当前月的开始（当月1号05:00:00）
    if now.day == 1 and now.hour < 5:
        # 如果是1号但不到5点，使用上个月1号作为开始
        if now.month == 1:
            month_start = datetime(now.year - 1, 12, 1, 5, 0, 0, 0, tzinfo=tz)
        else:
            month_start = datetime(now.year, now.month - 1, 1, 5, 0, 0, 0, tzinfo=tz)
    else:
        # 否则使用本月1号
        month_start = now.replace(day=1, hour=5, minute=0, second=0, microsecond=0)
        # 如果已经过了1号5点，但当前日期小于1号，则需要往前调整一个月
        if now.day < 1 or (now.day == 1 and now.hour < 5):
            if month_start.month == 1:
                month_start = month_start.replace(year=month_start.year - 1, month=12)
            else:
                month_start = month_start.replace(month=month_start.month - 1)

    # 计算下个月1号05:00:00作为当月结束
    if month_start.month == 12:
        month_end = datetime(month_start.year + 1, 1, 1, 5, 0, 0, 0, tzinfo=tz)
    else:
        month_end = datetime(
            month_start.year, month_start.month + 1, 1, 5, 0, 0, 0, tzinfo=tz
        )

    # 判断是否在当前周和当前月
    is_current_week = week_start <= timestamp_datetime < week_end
    is_current_month = month_start <= timestamp_datetime < month_end

    return is_current_week, is_current_month

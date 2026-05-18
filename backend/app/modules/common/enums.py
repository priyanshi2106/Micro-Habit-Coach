from enum import Enum


class HabitCategory(str, Enum):
    MINDFULNESS = "mindfulness"
    MOVEMENT = "movement"
    LEARNING = "learning"
    PRODUCTIVITY = "productivity"
    FINANCE = "finance"
    SOCIAL = "social"
    HEALTH = "health"


class ScheduleBlockType(str, Enum):
    FREE = "free"
    BUSY = "busy"


class HabitLogStatus(str, Enum):
    DONE = "done"
    SNOOZED = "snoozed"
    SKIPPED = "skipped"


class SuggestionSource(str, Enum):
    MANUAL = "manual"
    RULE_ENGINE = "rule_engine"
    ADAPTIVE_ENGINE = "adaptive_engine"
    CALENDAR = "calendar"
    AI = "ai"

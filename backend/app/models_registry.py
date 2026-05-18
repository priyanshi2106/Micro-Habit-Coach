"""Import all ORM modules for side effects (mapper registration, metadata)."""

from app.modules.habit_logs import models as habit_log_models  # noqa: F401
from app.modules.habits import models as habit_models  # noqa: F401
from app.modules.schedules import models as schedule_models  # noqa: F401
from app.modules.suggestions import models as suggestion_models  # noqa: F401
from app.modules.users import models as user_models  # noqa: F401

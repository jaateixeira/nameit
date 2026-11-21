"""NameIt - rename research article PDFs in a standardised way."""

__version__ = "0.9.0"

from nameit.api import (  # noqa: E402
    RenamePlan,
    apply_plan,
    plan_rename,
    rename_pdf,
    undo_renames,
)

__all__ = ["RenamePlan", "apply_plan", "plan_rename", "rename_pdf", "undo_renames", "__version__"]

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime


import traceback

from utils.unified_logger import logger
from utils.unified_console import console


class ErrorSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ErrorModel:
    """Loguru-optimized error model with Rich console support."""
    error_type: str
    message: str
    severity: ErrorSeverity = ErrorSeverity.ERROR
    timestamp: str = datetime.now().isoformat()
    context: Optional[Dict[str, Any]] = None
    solution: Optional[str] = None
    stacktrace: Optional[str] = None

    @classmethod
    def capture(
            cls,
            exc: Exception,
            *,
            context: Optional[Dict[str, Any]] = None,
            solution: Optional[str] = None,
            severity: ErrorSeverity = ErrorSeverity.ERROR
    ) -> "ErrorModel":
        """Create, log, and return an error model."""
        nameit_error = cls(
            error_type=exc.__class__.__name__,
            message=str(exc),
            severity=severity,
            context=context,
            solution=solution,
            stacktrace="".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        )
        nameit_error._log_with_loguru()
        return nameit_error

    def _log_with_loguru(self):
        """Internal method to handle Loguru logging with Rich formatting."""
        log_method = {
            ErrorSeverity.INFO: logger.info,
            ErrorSeverity.WARNING: logger.warning,
            ErrorSeverity.ERROR: logger.error,
            ErrorSeverity.CRITICAL: logger.critical,
        }[self.severity]

        log_method(
            "{} [bold]{}[/bold]: {}",
            self._get_severity_icon(),
            self.error_type,
            self.message,
            extra={"markup": True}  # Enable Rich markup
        )

        if self.context:
            logger.bind(context=self.context).debug("Context details")

        if logger.level(self.severity.value).no >= logger.level("ERROR").no:
            logger.opt(exception=True).debug("Full stack trace")

    def _get_severity_icon(self) -> str:
        icons = {
            ErrorSeverity.INFO: "ℹ️",
            ErrorSeverity.WARNING: "⚠️",
            ErrorSeverity.ERROR: "❌",
            ErrorSeverity.CRITICAL: "💥"
        }
        return icons[self.severity]

    def display_user_friendly(self) -> None:
        """Print rich-formatted error to console."""
        console.print(f"\n[{self._get_severity_color()}]┏━━ {self.error_type} ━━[/]")
        console.print(f"[{self._get_severity_color()}]┃[/] {self.message}")
        if self.solution:
            console.print(f"[{self._get_severity_color()}]┃[/] [bold]Solution:[/] {self.solution}")
        console.print(f"[{self._get_severity_color()}]┗━━━[/]\n")

    def _get_severity_color(self) -> str:
        colors = {
            ErrorSeverity.INFO: "blue",
            ErrorSeverity.WARNING: "yellow",
            ErrorSeverity.ERROR: "red",
            ErrorSeverity.CRITICAL: "bold red"
        }
        return colors[self.severity]


if __name__ == '__main__':
    # Example 1: Simple error capture
    try:
        1 / 0
    except Exception as e:
        error = ErrorModel.capture(e)
        error.display_user_friendly()

    # Example 2: With business context
    try:
        pdf_file_path = "report.txt"
        if not pdf_file_path.endswith('.pdf'):
            raise ValueError(f"Invalid file extension for {pdf_file_path}")
    except Exception as e:
        error = ErrorModel.capture(
            e,
            context={
                "file": pdf_file_path,
                "operation": "file_validation",
                "checks": ["extension", "mime_type"]
            },
            solution="Please provide a valid PDF file",
            severity=ErrorSeverity.WARNING
        )
        error.display_user_friendly()

    # Example 3: Critical error
    try:
        raise RuntimeError("Database connection failed")
    except Exception as e:
        ErrorModel.capture(
            e,
            context={
                "db_host": "localhost",
                "attempts": 3,
                "timeout": "30s"
            },
            solution="Check database service and credentials",
            severity=ErrorSeverity.CRITICAL
        ).display_user_friendly()
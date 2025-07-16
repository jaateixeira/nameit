import os


class NameItError(Exception):
    """Base exception class for all NameIt application errors."""
    pass


class PDFError(NameItError):
    """Base class for PDF-related errors."""
    pass


class FileSystemError(NameItError):
    """Base class for filesystem-related errors."""
    pass


class ValidationError(NameItError):
    """Base class for input validation errors."""
    pass


# PDF-specific exceptions
class PDFPermissionError(PDFError):
    """Raised when the application doesn't have permission to access the PDF."""

    def __init__(self, path, operation):
        self.path = path
        self.operation = operation
        super().__init__(
            f"Cannot {operation} PDF at '{path}'. "
            f"Check file permissions."
        )


class PDFCorruptedError(PDFError):
    """Raised when a PDF file is corrupted or invalid."""

    def __init__(self, path):
        self.path = path
        super().__init__(
            f"PDF file at '{path}' appears to be corrupted or invalid. "
            f"Try opening it with a PDF viewer to verify."
        )


class PDFMetadataError(PDFError):
    """Raised when there are issues reading or extracting PDF metadata."""

    def __init__(self, path, missing_fields=None):
        self.path = path
        self.missing_fields = missing_fields or []
        message = f"Failed to extract metadata from PDF at '{path}'"
        if missing_fields:
            message += f". Missing fields: {', '.join(missing_fields)}"
        super().__init__(message)


class PDFEncryptedError(PDFError):
    """Raised when attempting to process an encrypted PDF."""

    def __init__(self, path):
        self.path = path
        super().__init__(
            f"PDF at '{path}' is encrypted. "
            f"Decrypt the file before processing."
        )


# CrossRef exceptions
class InvalidCrossrefDataError(Exception):
    """Raised when essential Crossref metadata fields are missing or invalid."""
    def __init__(self, missing_fields):
        message = f"Missing or invalid fields in Crossref metadata: {', '.join(missing_fields)}"
        super().__init__(message)
        self.missing_fields = missing_fields


# Filesystem exceptions
class InvalidNameItPath(FileSystemError):
    """Raised when a provided path is invalid or doesn't meet PDF requirements.

    Args:
        path (str): The problematic path
        reason (str): Technical reason for invalidity
        suggestion (str): Optional suggestion to fix
    """

    def __init__(self, path, reason=None, suggestion=None):
        self.path = path
        self.reason = reason
        self.suggestion = suggestion

        message_parts = [
            f"Invalid path: '{path}'",
            f"Reason: {reason}" if reason else "",
            f"Suggestion: {suggestion}" if suggestion else "",
            "Please provide either:",
            "- A valid PDF file (.pdf extension)",
            "- OR a directory containing PDF files"
        ]

        super().__init__("\n".join(filter(None, message_parts)))


class SourceFileNotFoundError(FileSystemError):
    """Raised when the source PDF file doesn't exist."""

    def __init__(self, path):
        self.path = path
        super().__init__(
            f"Source PDF not found at '{path}'. "
            f"Verify the file exists and path is correct."
        )


class DestinationExistsError(FileSystemError):
    """Raised when the target filename already exists."""

    def __init__(self, path, conflict_type='file'):
        self.path = path
        self.conflict_type = conflict_type
        super().__init__(
            f"Cannot rename - {conflict_type} already exists at '{path}'. "
            f"Choose a different name or enable overwrite mode."
        )


class StorageLimitExceededError(FileSystemError):
    """Raised when operation would exceed storage limits."""

    def __init__(self, operation, available, required):
        self.operation = operation
        self.available = available
        self.required = required
        super().__init__(
            f"Cannot {operation} - requires {required} bytes "
            f"but only {available} bytes available."
        )


# Validation exceptions
class InvalidFilenamePatternError(ValidationError):
    """Raised when the provided filename pattern is invalid."""

    def __init__(self, pattern, reason):
        self.pattern = pattern
        self.reason = reason
        super().__init__(
            f"Invalid filename pattern '{pattern}': {reason}. "
            f"Use valid pattern with supported metadata tags."
        )


class MissingMetadataError(ValidationError):
    """Raised when required PDF metadata is missing for renaming."""

    def __init__(self, field_name, available_fields=None):
        self.field_name = field_name
        self.available_fields = available_fields or []
        message = f"Required metadata field '{field_name}' is missing"
        if available_fields:
            message += f". Available fields: {', '.join(available_fields)}"
        super().__init__(message)


class UnsupportedFileTypeError(ValidationError):
    """Raised when a non-PDF file is provided."""

    def __init__(self, path, actual_type=None):
        self.path = path
        self.actual_type = actual_type
        message = f"File at '{path}' is not a PDF"
        if actual_type:
            message += f" (detected as {actual_type})"
        super().__init__(message)


class ConfigurationError(NameItError):
    """Raised when there are issues with application configuration."""

    def __init__(self, setting, reason):
        self.setting = setting
        self.reason = reason
        super().__init__(
            f"Invalid configuration for '{setting}': {reason}. "
            f"Check your settings file."
        )


class NamingConflictError(NameItError):
    """Raised when the renaming operation would cause duplicates or conflicts."""

    def __init__(self, original_path, new_path):
        self.original_path = original_path
        self.new_path = new_path
        super().__init__(
            f"Renaming '{original_path}' to '{new_path}' would cause naming conflict. "
            f"Consider a different naming pattern."
        )
class AppException(Exception):
    status_code = 500
    code = "application_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class CompanyNotFoundError(AppException):
    status_code = 404
    code = "company_not_found"


class ScrapingError(AppException):
    status_code = 502
    code = "scraping_failed"


class LLMExtractionError(AppException):
    status_code = 502
    code = "llm_extraction_failed"


class ExcelGenerationError(AppException):
    status_code = 500
    code = "excel_generation_failed"


class DatabaseOperationError(AppException):
    status_code = 500
    code = "database_operation_failed"


class ConfigurationError(AppException):
    status_code = 500
    code = "configuration_error"

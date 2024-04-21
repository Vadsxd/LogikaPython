from enum import Enum


class ErrorCode(Enum):
    BadRequest = (0, "нарушение структуры запроса")
    WriteProtected = (1, "защита от записи")
    ArgumentError = (2, "недопустимое значение")

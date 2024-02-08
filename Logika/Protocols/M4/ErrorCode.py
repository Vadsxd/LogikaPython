from enum import Enum


class ErrorCode(Enum):
    BadRequest = 0
    WriteProtected = 1
    ArgumentError = 2

    def __str__(self):
        descriptions = {
            ErrorCode.BadRequest: "нарушение структуры запроса",
            ErrorCode.WriteProtected: "защита от записи",
            ErrorCode.ArgumentError: "недопустимое значение",
        }
        return descriptions[self]

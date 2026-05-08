import enum


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    PARTIES_CONFIRMED = "parties_confirmed"
    BUILT = "built"
    EXPORTED = "exported"
    FAILED = "failed"


class RevisionType(str, enum.Enum):
    INS = "INS"
    DEL = "DEL"
    FORMAT_ONLY = "FORMAT_ONLY"


class ClauseFlag(str, enum.Enum):
    MULTI_PARAGRAPH = "MULTI_PARAGRAPH"
    NEW_CLAUSE = "NEW_CLAUSE"
    DELETED_CLAUSE = "DELETED_CLAUSE"
    LOW_NUMBERING_CONFIDENCE = "LOW_NUMBERING_CONFIDENCE"
    LOW_CONFIDENCE_BOUNDARY = "LOW_CONFIDENCE_BOUNDARY"


class RowFlag(str, enum.Enum):
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MULTI_PARAGRAPH_SOURCE = "MULTI_PARAGRAPH_SOURCE"
    MANUALLY_ADDED = "MANUALLY_ADDED"
    USER_EDITED = "USER_EDITED"

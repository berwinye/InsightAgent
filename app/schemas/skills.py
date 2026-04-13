from pydantic import BaseModel
from typing import Any, Optional


class RunPythonRequest(BaseModel):
    code: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": (
                        "import pandas as pd\n"
                        "df = read_sql('SELECT productLine, SUM(quantityOrdered * priceEach) as revenue "
                        "FROM orderdetails od JOIN products p ON od.productCode = p.productCode "
                        "GROUP BY productLine ORDER BY revenue DESC')\n"
                        "print(df.to_csv(index=False))"
                    )
                }
            ]
        }
    }


class RunPythonSuccess(BaseModel):
    status: str = "success"
    stdout: str
    summary: dict[str, Any]


class RunPythonError(BaseModel):
    status: str
    error_type: str
    message: str
    hint: Optional[str] = None


class AnalyzeRequest(BaseModel):
    question: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"question": "Compare the total revenue of each office/store."}
            ]
        }
    }


class AnalyzeResponse(BaseModel):
    answer: str
    iterations: int
    generated_code: Optional[str] = None
    saved_query_id: Optional[int] = None
    log_id: Optional[int] = None
    tool_trace: list[str] = []

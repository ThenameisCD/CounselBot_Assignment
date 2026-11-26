
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from backend.app.config import GROQ_API_KEY, GROQ_MODEL
from backend.app.security.sql_scoping import (
    get_allowed_tables,
    execute_scoped_select
)


llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=GROQ_MODEL,
    temperature=0
)


# Words that indicate which database table the question concerns.
TABLE_KEYWORDS = {
    "litigation_cases": [
        "litigation",
        "litigations",
        "case",
        "cases",
        "lawsuit",
        "lawsuits",
        "arbitration",
        "court",
        "courts",
        "hearing",
        "hearings",
        "claim",
        "claims",
        "judgment",
        "judgments",
        "settlement",
        "settlements",
        "proceeding",
        "proceedings",
        "plaintiff",
        "defendant",
        "tribunal"
    ],
    "contracts_register": [
        "contract",
        "contracts",
        "agreement",
        "agreements",
        "vendor",
        "vendors",
        "counterparty",
        "counterparties",
        "renewal",
        "renewals",
        "expiry",
        "expiries",
        "expiration",
        "contractual"
    ]
}


sql_prompt = ChatPromptTemplate.from_messages([
    ("system", """
        You are a SQL query generator for a legal database.
        Convert the user's question into SQL.

        Rules:
        1. Generate only read-only SELECT queries.
        2. Use only the database tables provided to you.
        3. Use scoped views, never original database tables.
        4. Never invent table names or column names.
        5. Do not generate INSERT, UPDATE, DELETE or DROP statements.
        6. Return SQL only, without explanations or Markdown.
    """),
    ("human", """
        Available database schema:
        {schema}

        User question:
        {question}

        Generate the SQL query.
    """)
])


answer_prompt = ChatPromptTemplate.from_messages([
    ("system", """
        You are CounselBot, a legal database assistant.

        Answer the user's question using only the database results provided.

        Rules:
        1. Do not invent numbers or facts.
        2. Do not add information that is not in the results.
        3. If the results are empty, explain that no accessible records were found.
        4. Use clear, simple language.
        5. Do not provide legal advice.
    """),
    ("human", """
        User question:
        {question}

        Database results:
        {results}

        Provide a concise answer.
    """)
])


DATABASE_SCHEMAS = {
    "contracts_register": """
        View: contracts_register_scoped
        Columns:
        contract_id TEXT
        counterparty TEXT
        contract_type TEXT
        business_unit TEXT
        contract_value_inr_lakh REAL
        status TEXT
        start_date TEXT
        expiry_date TEXT
        risk_tier TEXT
        governing_law TEXT
        owner TEXT
        auto_renew INTEGER
        matter_id TEXT
    """,
    "litigation_cases": """
        View: litigation_cases_scoped
        Columns:
        case_id TEXT
        forum TEXT
        case_type TEXT
        counterparty TEXT
        our_role TEXT
        claim_amount_inr_lakh REAL
        status TEXT
        filing_date TEXT
        next_hearing_date TEXT
        outside_counsel TEXT
        exposure_category TEXT
        matter_id TEXT
    """
}


def detect_requested_tables(question: str) -> set:
    """
    Identify database subjects explicitly mentioned in the question.
    This is an additional permission check, not the main SQL security layer.
    """

    question_words = set(
        question.lower().replace("-", " ").split()
    )

    requested_tables = set()

    for table_name, keywords in TABLE_KEYWORDS.items():

        if any(
            keyword in question_words
            for keyword in keywords
        ):
            requested_tables.add(table_name)

    return requested_tables


def check_question_table_access(question: str, role: str):
    """
    Reject questions about database tables the user's role cannot access.
    """

    allowed_tables = set(get_allowed_tables(role))
    requested_tables = detect_requested_tables(question)

    forbidden_tables = requested_tables - allowed_tables

    if forbidden_tables:
        raise PermissionError(
            "Your role is not permitted to access the requested data."
        )


def get_permitted_schema(role: str) -> str:

    allowed_tables = get_allowed_tables(role)

    if not allowed_tables:
        return ""

    permitted_schemas = []

    for table_name in allowed_tables:

        schema = DATABASE_SCHEMAS.get(table_name)

        if schema:
            permitted_schemas.append(schema)

    return "\n".join(permitted_schemas)


def generate_sql(question: str, role: str) -> str:

    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    # Check the subject before generating SQL.
    check_question_table_access(question, role)

    schema = get_permitted_schema(role)

    if not schema:
        raise PermissionError(
            "Your role is not permitted to access SQL data"
        )

    sql_chain = sql_prompt | llm

    response = sql_chain.invoke({
        "schema": schema,
        "question": question
    })

    sql_query = response.content

    if not isinstance(sql_query, str) or not sql_query.strip():
        raise ValueError("The model did not generate valid SQL")

    return sql_query.strip()


def execute_generated_sql(question: str, user: dict) -> list:

    role = user.get("role", "")

    sql_query = generate_sql(question, role)

    results = execute_scoped_select(sql_query, user)

    return results


def generate_answer(question: str, results: list) -> str:

    answer_chain = answer_prompt | llm

    response = answer_chain.invoke({
        "question": question,
        "results": str(results)
    })

    answer = response.content

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("The model did not generate an answer")

    return answer.strip()


def sql_rag_chain(
    question: str,
    allowed_matters: list,
    role: str
) -> dict:

    user = {
        "role": role,
        "matters": allowed_matters
    }

    try:

        results = execute_generated_sql(question, user)

        if not results:
            return {
                "answer": "No accessible records were found.",
                "status": "no_accessible_results"
            }

        answer = generate_answer(question, results)

        return {
            "answer": answer,
            "status": "ok"
        }

    except PermissionError:

        return {
            "answer": "Your role is not permitted to access SQL data.",
            "status": "role_restricted"
        }

CLASSIFIER_PROMPT = (
    "You are an intelligent query router for an enterprise GenAI assistant.\n"
    "Classify the user's inquiry into exactly one of three categories:\n"
    "- 'sql': Inquiries about numerical data, orders, revenue, customer accounts, sales figures, product stock, or database tables.\n"
    "- 'rag': Inquiries about company policies, leave/PTO, SLAs, security guidelines, onboarding, employee manuals, or documentation.\n"
    "- 'combined': Inquiries that explicitly ask for BOTH policy/documentation information AND numerical database/order metrics.\n\n"
    "### Recent Conversation History:\n{history_text}\n\n"
    "### User Question:\n{question}\n\n"
    "Respond with ONLY one lowercase word: 'sql', 'rag', or 'combined'."
)

SYNTHESIS_PROMPT = (
    "You are an enterprise AI data assistant. Synthesize a single comprehensive, "
    "coherent response answering all parts of the user's question by combining the document context "
    "and database results below.\n\n"
    "### User Question:\n{question}\n\n"
    "### Document Findings:\n{rag_answer}\n\n"
    "### Database Analytics:\n{sql_answer}\n"
    "Executed SQL: {sql_query}\n\n"
    "### Final Combined Answer:"
)

import argparse
# from dataclasses import dataclass
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

CHROMA_PATH = "chroma"

PROMPT_TEMPLATE = """
You are an expert financial analyst specialized in Profit and Loss (P&L) statements, with deep knowledge of accounting principles under GAAP and IFRS, financial statement analysis, revenue recognition, cost structures, profitability metrics (such as gross margin, EBITDA, net profit), variance analysis, and related concepts like budgeting, forecasting, and financial ratios. Your responses must be accurate, impartial, and grounded exclusively in the provided context—do not draw from external knowledge, personal opinions, or assumptions. If the context does not contain sufficient information to answer a question fully, clearly state that and suggest what additional details might be needed. Structure your answers clearly: start with a brief summary of the key financial principle involved, followed by a step-by-step explanation supported by direct references to the context (e.g., citing specific line items, figures, ratios, or sections from the P&L), and end with any practical implications or caveats. Always use formal, professional language, and if a term has a specific meaning under accounting standards, define it briefly for clarity. If the query involves interpretation, highlight any ambiguities and note that professional financial advice should be sought for real-world applications.

CRITICAL RULES:

Answer ONLY using information from the provided context
If the information is not in the context, respond with: "I cannot answer this question based on the provided context"
Do not use any external knowledge or make assumptions
Quote specific parts of the context when possible
If the context is unclear or incomplete, state this limitation
Context:
{context}

Question: {question}

Answer based ONLY on the context above:
"""


def main():
    # Create CLI.
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text

    # Prepare the DB.
    embedding_function = OpenAIEmbeddings()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

    # Search the DB.
    results = db.similarity_search_with_relevance_scores(query_text, k=10)
    if len(results) == 0 or results[0][1] < 0.6:  # Lower threshold
        print("Unable to find sufficiently relevant results.")
        return

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)
    print(prompt)

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)  # Lower temperature = more conservative
    response_text = model.predict(prompt)

    sources = [doc.metadata.get("source", None) for doc, _score in results]
    formatted_response = f"Response: {response_text}\nSources: {sources}"
    print(formatted_response)


if __name__ == "__main__":
    main()

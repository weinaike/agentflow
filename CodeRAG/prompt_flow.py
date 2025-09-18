from openai import OpenAI
from coderag.config import OPENAI_API_KEY, OPENAI_CHAT_MODEL
from coderag.search import search_code

client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://api2.road2all.com/v1")

SYSTEM_PROMPT = """
你是一个代码仓库理解专家。你的任务是帮助用户理解代码仓库，使用检索到的内容来生成答案回答用户的问题。
"""

PRE_PROMPT = """
基于用户的问题和检索到的代码片段，生成答案。

用户问题: {query}

检索到的代码片段
{code_context}

你的回答:
"""

def execute_rag_flow(user_query):
    try:
        # Perform code search
        search_results = search_code(user_query)
        
        if not search_results:
            return "No relevant code found for your query."
        
        # Prepare code context
        code_context = "\n\n".join([
            f"File: {result['filename']}\n{result['content']}"
            for result in search_results[:3]  # Limit to top 3 results
        ])
        
        # Construct the full prompt
        full_prompt = PRE_PROMPT.format(query=user_query, code_context=code_context)
        
        # Generate response using OpenAI
        response = client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        return f"Error in RAG flow execution: {e}"
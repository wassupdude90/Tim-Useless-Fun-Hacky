import json
import pandas as pd
import streamlit as st
from cloudflare import Cloudflare
from haystack import Finder
from haystack.document_store.memory import InMemoryDocumentStore
from haystack.nodes.retriever import BM25Retriever
from haystack.schema import Document

# 加载魔法食谱数据集
recipes_df = pd.read_csv("/Users/irisyu/Desktop/Project/ai-magic-recipe-generator/data/magic_recipes.csv")

st.title("Harry Potter AI Magic Recipe Generator with Haystack")

# 设置 Cloudflare API 密钥
client = Cloudflare(api_token=st.secrets["CLOUDFLARE_API_TOKEN"])

# 初始化聊天记录
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 将数据集转换为 Haystack 文档格式
def df_to_haystack_docs(df):
    docs = []
    for _, row in df.iterrows():
        content = row['Output']  # 假设 'Output' 包含食谱详细内容
        title = row['Input']     # 假设 'Input' 包含食谱名称或类型
        docs.append(Document(content=content, meta={"name": title}))
    return docs

# 初始化 Haystack 的 InMemoryDocumentStore
document_store = InMemoryDocumentStore()
docs = df_to_haystack_docs(recipes_df)
document_store.write_documents(docs)

# 初始化 BM25Retriever
retriever = BM25Retriever(document_store=document_store)

# 初始化 Finder
finder = Finder(retriever=retriever)

# 函数：查找参考食谱
def find_reference_recipes_haystack(user_input, finder):
    # 使用 Haystack 检索相关文档
    retrieved_docs = finder.retrieve(query=user_input, top_k=3)  # 返回 3 个相关食谱
    return retrieved_docs

# 函数：处理 AI 生成的流式输出
def iter_tokens(response):
    tokens = []
    for line in response.iter_lines():
        if line.startswith("data: ") and not line.endswith("[DONE]"):
            entry = json.loads(line.replace("data: ", ""))
            tokens.append(entry["response"])
    return "".join(tokens)

# 接受用户输入
if prompt := st.chat_input("Please enter the type of magic recipe you want to generate:"):

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 使用 Haystack 检索相关参考食谱
    retrieved_docs = find_reference_recipes_haystack(prompt, finder)

    if retrieved_docs:
        reference_text = "\n\n".join([doc.content for doc in retrieved_docs])
    else:
        reference_text = "No relevant recipes found in the database."

    # 显示检索到的食谱 (可选，作为调试或参考)
    st.write("Retrieved Recipes:")
    for doc in retrieved_docs:
        st.markdown(f"**{doc.meta['name']}**: {doc.content}")

    # 使用 Cloudflare Workers AI 生成新的魔法食谱
    with st.chat_message("assistant"):
        try:
            with client.workers.ai.with_streaming_response.run(
                account_id=st.secrets["CLOUDFLARE_ACCOUNT_ID"],
                model_name="@cf/meta/llama-3.1-8b-instruct",
                messages=[
                    {"role": "system", "content": "You are an expert in Harry Potter magic recipes. Use the provided recipes as references to generate a new detailed magic recipe."},
                    {"role": "system", "content": f"Here are some reference recipes:\n{reference_text}"},
                    {"role": "user", "content": prompt}
                ],
                stream=True,
            ) as response:
                completion = iter_tokens(response)

                st.markdown(f"**Generated Magic Recipe:**\n\n{completion}")

        except Exception as e:
            st.error(f"An error occurred: {e}")

    st.session_state.messages.append({"role": "assistant", "content": completion})

    # 函数：在数据库中查找与生成食谱相似的预定义食谱
    def find_similar_recipes(generated_recipe, recipes_df):
        similar_recipes = recipes_df[recipes_df['Output'].str.contains(generated_recipe, case=False, na=False, regex=False)]
        return similar_recipes

    # 查找与生成结果相似的食谱
    similar_recipes = find_similar_recipes(completion, recipes_df)

    if not similar_recipes.empty:
        st.write("Similar predefined magic recipes found in the database:")
        st.dataframe(similar_recipes)
    else:
        st.write("No similar predefined magic recipes found.")

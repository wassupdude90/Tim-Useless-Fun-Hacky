import json
import pandas as pd
import streamlit as st
from cloudflare import Cloudflare


recipes_df = pd.read_csv("/Users/irisyu/desktop/project/ai-magic-recipe-generator/useless-hack/Tim-Useless-Fun-Hacky/python/.streamlit/magic_recipes.csv")

st.title("Harry Potter AI Magic Recipe Generator")

client = Cloudflare(api_token=st.secrets["CLOUDFLARE_API_TOKEN"])

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def find_reference_recipes(user_input, recipes_df):
    reference_recipes = recipes_df[recipes_df['Input'].str.contains(user_input, case=False, na=False)]
    return reference_recipes


def iter_tokens(response):
    tokens = []
    for line in response.iter_lines():
        if line.startswith("data: ") and not line.endswith("[DONE]"):
            entry = json.loads(line.replace("data: ", ""))
            tokens.append(entry["response"])
    return "".join(tokens)


if prompt := st.chat_input("Please enter the type of magic recipe you want to generate:"):

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)


    reference_recipes = find_reference_recipes(prompt, recipes_df)

    if not reference_recipes.empty:
        reference_text = "\n\n".join(reference_recipes['Output'].tolist())
    else:
        reference_text = "No relevant recipes found in the database."
    

    with st.chat_message("assistant"):
        try:

            with client.workers.ai.with_streaming_response.run(
                account_id=st.secrets["CLOUDFLARE_ACCOUNT_ID"],
                model_name="@cf/meta/llama-3.1-8b-instruct",
                messages=[
                    {"role": "system", "content": "You are an expert in Harry Potter magic recipes. Generate detailed, accurate, and creative magic recipes based on the user's input. The recipes should include ingredients, steps, and special magical instructions."},
                    {"role": "system", "content": f"Here are some reference recipes from the database:\n{reference_text}"},
                    {"role": "user", "content": prompt}
                ],
                stream=True,
            ) as response:
                completion = iter_tokens(response)

                st.markdown(f"**Generated Magic Recipe:**\n\n{completion}")

        except Exception as e:
            st.error(f"An error occurred: {e}")

    st.session_state.messages.append({"role": "assistant", "content": completion})

    def find_similar_recipes(generated_recipe, recipes_df):
        similar_recipes = recipes_df[recipes_df['Output'].str.contains(generated_recipe, case=False, na=False, regex=False)]
        return similar_recipes


    similar_recipes = find_similar_recipes(completion, recipes_df)
    

    if not similar_recipes.empty:
        st.write("Similar predefined magic recipes found in the database:")
        st.dataframe(similar_recipes)
    else:
        st.write("No similar predefined magic recipes found.")

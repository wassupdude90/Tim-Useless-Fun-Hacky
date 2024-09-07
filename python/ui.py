import json
import pandas as pd
import streamlit as st
from cloudflare import Cloudflare
import time

# Load the recipe database
recipes_df = pd.read_csv("/Users/andreamellany/Documents/Useless-Fun-Hacky_Muggle-s_Kitchen/python/.streamlit/magic_recipes.csv")

# Inject custom CSS for design and wand cursor
st.markdown(
    """
    <style>
    /* Main Background */
    .stApp {
        background-color: #000000; /* Deep Indigo */
        color: white;
    }

    /* Sidebar Background */
    .css-1d391kg {
        background-color: #CBC3E3 !important; /* Deep Purple */
        color: white;
    }

    /* Sidebar Title and Info Text */
    .css-1v0mbdj h1 {
        font-family: 'Harry Potter', cursive;
        color: #FFD700; /* Gold */
    }
    .css-1v0mbdj p {
        color: white;
        font-size: 14px;
    }

    /* Heading Fonts */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Harry Potter', cursive;
        color: #FFD700; /* Gold */
    }

    /* Text Inputs, Select Boxes, Buttons */
    .stTextInput > div > div > input {
        background-color: #6A0DAD; /* Royal Purple */
        color: white;
    }

    .stButton > button {
        background-color: #800080; /* Deep purple */
        color: white;
        border-radius: 10px;
        font-size: 18px;
        cursor: url('https://Users/andreamellany/Documents/Useless-Fun-Hacky_Muggle-s_Kitchen/python/images.png'), auto;
    }

    .stSelectbox > div > div > div > div > ul {
        background-color: #4B0082; /* Indigo */
        color: white;
    }

    /* Custom Fonts - Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Gloock&display=swap');
    @font-face {
        font-family: 'Harry Potter';
        src: url('https://fonts.cdnfonts.com/s/15456/HarryPotter.woff') format('woff');
    }

    /* Parchment-like text area */
    .stTextArea > label, .stTextArea > div > textarea {
        background-color: rgba(75, 0, 130, 0.8); /* Deep Purple with Transparency */
        border-radius: 10px;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Title with magical font
st.title("✨ Harry Potter AI Magic Recipe Generator ✨")
st.markdown("---")  # Add a horizontal line

# Sidebar information
st.sidebar.title("About")
st.sidebar.info("This is a magical recipe generator powered by AI.")
st.sidebar.markdown("""
### Welcome to Muggle's Kitchen: A Totally Useless Guide for Conjuring Magical Recipes

Ah, yes. You, a humble muggle, have stumbled upon the **Harry Potter AI Magic Recipe Generator**—the very tool that probably *won't* turn you into a world-renowned potion master. But hey, who needs practicality when you can randomly mash buttons and pretend you're a wizard!

**How It Works (Maybe...)**:  
1. **Enter some magical gibberish** in the text box. Potions? Spells? Breakfast foods that might or might not explode? Go wild.
2. **Press the shiny "Generate Recipe" button**. Watch in awe as our AI, which is totally not just a random word generator, spits out a concoction of ingredients that are at best, mildly concerning, and at worst, legally questionable.
3. **Pretend you understand** the instructions it gives you. Trust us, it's more fun that way.
4. **Enjoy** your magical (and definitely inedible) recipe, guaranteed to *almost* never summon a Dark Lord (we think).

**Disclaimer**:  
Results may vary depending on the alignment of Mars, the mood of our AI, and how much tea we've had. Please refrain from actually mixing ingredients unless you want to explain to a hospital why your cauldron is now your neighbor's problem.

So what are you waiting for? Get ready to laugh at our AI's questionable culinary skills. Your Hogwarts letter may have gotten lost in the mail, but now you can pretend it didn't!
""")
st.subheader("Conjure Your Magical Recipe!")

# Initialize Cloudflare client
client = Cloudflare(api_token=st.secrets["CLOUDFLARE_API_TOKEN"])

# Initialize session state to store messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Placeholder for generated recipe (to appear above the input box)
recipe_placeholder = st.empty()

# Function to find reference recipes from the CSV database
def find_reference_recipes(user_input, recipes_df):
    reference_recipes = recipes_df[recipes_df['Input'].str.contains(user_input, case=False, na=False)]
    return reference_recipes

# Function to iterate over tokens in the AI response
def iter_tokens(response):
    tokens = []
    for line in response.iter_lines():
        if line.startswith("data: ") and not line.endswith("[DONE]"):
            entry = json.loads(line.replace("data: ", ""))
            tokens.append(entry["response"])
    return "".join(tokens)

# placeholder = st.empty()
# if st.button("Start Brewing"):
#     for i in range(5):
#         placeholder.text(f"Brewing... Step {i+1}/5")
#         time.sleep(1)
#     placeholder.text("Your potion is ready!")

# Input field and Generate button logic
prompt = st.text_input("Ask for a magical recipe:")
placeholder = st.empty()

if st.button("Start Brewing") and prompt:
    for i in range(5):
        placeholder.text(f"Brewing... Step {i+1}/5")
        time.sleep(1)
    
    placeholder.text("Your potion is ready! Generating the magic recipe...")

    # Find reference recipes from the database
    reference_recipes = find_reference_recipes(prompt, recipes_df)

    if not reference_recipes.empty:
        reference_text = "\n\n".join(reference_recipes['Output'].tolist())
    else:
        reference_text = "No relevant recipes found in the database."

    # Generate response using Cloudflare's AI with reference recipes
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

    # Save assistant's response as a message
    st.session_state.messages.append({"role": "assistant", "content": completion})

    # Function to find similar recipes in the dataset
    def find_similar_recipes(generated_recipe, recipes_df):
        similar_recipes = recipes_df[recipes_df['Output'].str.contains(generated_recipe, case=False, na=False, regex=False)]
        return similar_recipes

    # Find and display similar recipes from the database
    similar_recipes = find_similar_recipes(completion, recipes_df)

    if not similar_recipes.empty:
        st.write("Similar predefined magic recipes found in the database:")
        st.dataframe(similar_recipes)
    else:
        st.write("No similar predefined magic recipes found.")
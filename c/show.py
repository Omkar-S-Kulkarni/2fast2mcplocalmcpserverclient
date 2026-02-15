import openai
openai.api_key = "your-api-key-here"
while True:
    user_input = input("You: ")
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": user_input}])
    print("Bot:", response.choices[0].message.content)
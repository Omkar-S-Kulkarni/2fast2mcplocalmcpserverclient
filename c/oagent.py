import requests

API_KEY = "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"
URL = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# conversation memory
messages = []

print("Grok Code Fast Chatbot (type 'exit' to quit)\n")

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        break

    messages.append({
        "role": "user",
        "content": user_input
    })

    data = {
        "model": "x-ai/grok-code-fast-1",   # ← your model
        "messages": messages
    }

    response = requests.post(URL, headers=headers, json=data)
    result = response.json()

    bot_reply = result["choices"][0]["message"]["content"]

    messages.append({
        "role": "assistant",
        "content": bot_reply
    })

    print("Bot:", bot_reply)

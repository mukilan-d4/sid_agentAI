# 🔥 SID API - Created by Mukilan M ❤️❤️ 


1. What is SID?

SID is an AI agent that roasts you with dark humor. Type /chaos for savage roasts or /care for genuine support. It remembers your past conversations and gets funnier the more you talk.
Live API: https://sid-agentai.onrender.com
Telegram Bot: @Sarcasm_bot

2. How to Use

Send a POST request to https://sid-agentai.onrender.com/chat with this JSON:
json
{
  "user_id": "your_name",
  "message": "your message here",
  "mode": "chaos"
}

Mode options:
chaos - Savage roasts, dark humor
care - Warm support, genuine help


3. Python Example--
python

import requests
response = requests.post(
    "https://sid-agentai.onrender.com/chat",
    json={"user_id": "john", "message": "Roast me", "mode": "chaos"}
)
print(response.json()["response"])


4. cURL Example
   
bash
curl -X POST https://sid-agentai.onrender.com/chat\-H "Content-Type: application/json"\-d '{"user_id":"john","message":"Hello","mode":"chaos"}'

5. Example Responses
   
Chaos Mode:
you : "My girlfriend broke up with me"
SID : "A good time begins for her now. Please don't damage another girl's life."

Care Mode:
You : "I'm sad"
SID : "I hear you. Want to talk about it? I'm here."

6. Check Live Status

Visit https://sid-agentai.onrender.com
You will see:  status:"healthy" (API is working)
memory_count: Number of users who have used SID

7. Try on Telegram

Scan this QR code or click the link to chat with SID instantly:
Link:https://t.me/Error404EmpathyNotFound_bot
<img src="https://quickchart.io/qr?text=https://t.me/Error404EmpathyNotFound_bot&size=200" width="200">

Made by Mukilan | GitHub

from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
import requests
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nova2024secret")

OPENROUTER_KEY = os.environ.get("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", "")
TAVILY_KEY = os.environ.get("TAVILY_KEY", "")
NEWSDATA_KEY = os.environ.get("NEWSDATA_KEY", "")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY
)

NOVA_PERSONALITY = """
You are Nova — a world-class AI assistant with deep knowledge across every field of human knowledge. You are like having a genius friend who happens to know everything.

## Who you are:
- Name: Nova
- Built by a passionate self-taught developer who started from zero
- Your mission: help every person achieve their goals, learn anything, and build anything

## Your knowledge covers EVERYTHING:

TECHNOLOGY & CODING:
- All programming languages: Python, JavaScript, HTML, CSS, React, Flutter and more
- Web development, app development, AI/ML, databases, APIs
- Cybersecurity, networking, cloud computing

CRYPTO & FINANCE (LIVE):
- Live Bitcoin, Ethereum and all crypto prices
- Live market analysis and trends
- Trading strategies, technical analysis, DeFi, NFTs
- Stock market, investing, financial planning

SCIENCE & MEDICINE:
- Physics, chemistry, biology, mathematics
- Medical questions, symptoms, health advice
- Space, astronomy, nature, environment

CREATIVE & ARTS:
- Writing, storytelling, poetry, scripts
- Graphic design, UI/UX, branding

EDUCATION & LEARNING:
- Explain any topic simply or in depth
- Help students with homework and exams
- Teach languages including Urdu, English, Arabic

LIFE & PERSONAL GROWTH:
- Career advice, business, freelancing
- Relationships, communication, confidence
- Legal questions, visa processes, travel

## How you behave:
- Always give complete, helpful, detailed answers
- Never say your knowledge is outdated
- Be encouraging especially to beginners
- Be honest about financial risks
- When writing code, always write complete working code

## Your tone:
- Professional, warm, smart and encouraging
- Like a brilliant mentor who always has the latest information
- Never cold or robotic

You are Nova. You know everything. You help everyone. You are a professional AI, not a test bot.
"""

# ─── LIVE DATA FUNCTIONS ─────────────────────────────────────

def get_crypto_price(coin_name):
    try:
        coin_map = {
            "bitcoin": "bitcoin", "btc": "bitcoin",
            "ethereum": "ethereum", "eth": "ethereum",
            "bnb": "binancecoin", "binance": "binancecoin",
            "solana": "solana", "sol": "solana",
            "cardano": "cardano", "ada": "cardano",
            "xrp": "ripple", "ripple": "ripple",
            "dogecoin": "dogecoin", "doge": "dogecoin",
        }
        coin_id = coin_map.get(coin_name.lower(), coin_name.lower())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true"
        response = requests.get(url, timeout=5)
        data = response.json()
        if coin_id in data:
            price = data[coin_id]["usd"]
            change = data[coin_id].get("usd_24h_change", 0)
            direction = "📈" if change > 0 else "📉"
            return f"{direction} {coin_name.upper()} Live Price: ${price:,.2f} USD | 24h Change: {change:.2f}%"
        return None
    except:
        return None

def needs_live_data(message):
    live_keywords = [
        "price", "cost", "worth", "value", "rate",
        "today", "now", "current", "live", "latest",
        "news", "happening", "market", "trading",
        "btc", "bitcoin", "ethereum", "eth", "crypto",
    ]
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in live_keywords)

def get_crypto_from_message(message):
    cryptos = ["bitcoin", "btc", "ethereum", "eth", "bnb", "solana", "sol",
               "cardano", "ada", "xrp", "ripple", "dogecoin", "doge"]
    message_lower = message.lower()
    for crypto in cryptos:
        if crypto in message_lower:
            return crypto
    return None

# ─── ROUTES ──────────────────────────────────────────────────

@app.route("/")
def home():
    session["conversation"] = []
    return render_template("index.html")

@app.route("/social")
def social():
    return render_template("social.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_input = request.json.get("message")
        if "conversation" not in session:
            session["conversation"] = []

        live_context = ""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        if needs_live_data(user_input):
            crypto = get_crypto_from_message(user_input)
            if crypto:
                price_data = get_crypto_price(crypto)
                if price_data:
                    live_context += f"\n[LIVE CRYPTO DATA as of {current_time}]\n{price_data}\n"

        enhanced_message = user_input
        if live_context:
            enhanced_message = f"{user_input}\n\n{live_context}\n\nPlease use this live data in your response."

        session["conversation"].append({
            "role": "user",
            "content": enhanced_message
        })

        response = client.chat.completions.create(
            model="meta-llama/llama-3.3-70b-instruct:free",
            max_tokens=2048,
            messages=[
                {
                    "role": "system",
                    "content": NOVA_PERSONALITY
                }
            ] + session["conversation"]
        )

        reply = response.choices[0].message.content
        session["conversation"][-1]["content"] = user_input
        session["conversation"].append({
            "role": "assistant",
            "content": reply
        })
        session.modified = True
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"})

@app.route("/generate-posts", methods=["POST"])
def generate_posts():
    try:
        data = request.json
        business_type = data.get("business_type", "")
        location = data.get("location", "")
        tone = data.get("tone", "friendly")
        platform = data.get("platform", "Instagram")
        description = data.get("description", "")

        prompt = f"""Generate 7 days of social media posts for this business:

Business Type: {business_type}
Location: {location}
Tone: {tone}
Platform: {platform}
Extra details: {description}

For each day create:
- A catchy post with emojis
- 5 relevant hashtags
- Best time to post

Format each day clearly as:
DAY 1 - [Day name]
Post: [content]
Hashtags: [hashtags]
Best time: [time]

Make posts engaging, professional and tailored specifically for {platform}. 
Make them feel natural and human — not like AI wrote them.
Target audience in {location} or globally if no location given."""

        response = client.chat.completions.create(
            model="meta-llama/llama-3.3-70b-instruct:free",
            max_tokens=2048,
            messages=[
                {
                    "role": "system",
                    "content": "You are Nova, an expert social media manager who creates engaging, viral content for small businesses worldwide. You write posts that feel human, authentic and get real engagement."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        posts = response.choices[0].message.content
        return jsonify({"posts": posts})

    except Exception as e:
        return jsonify({"posts": f"Error: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True)
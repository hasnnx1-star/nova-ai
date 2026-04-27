from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
import requests
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nova2024secret")

# ─── API KEYS ────────────────────────────────────────────────
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
TAVILY_KEY = os.environ.get("TAVILY_KEY", "")
NEWSDATA_KEY = os.environ.get("NEWSDATA_KEY", "")

# ─── CLIENT ──────────────────────────────────────────────────
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY
)

# ─── MODEL ───────────────────────────────────────────────────
# Change to "deepseek/deepseek-chat" when you add credits
MODEL = "openrouter/free"

# ─── NOVA PERSONALITY ────────────────────────────────────────
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
- How to build real products from scratch

BUSINESS & MONEY:
- Cryptocurrency trading, Bitcoin, Ethereum, DeFi, NFTs
- Stock market, investing, financial planning
- How to start a business, marketing, sales
- Freelancing, making money online

SCIENCE & MEDICINE:
- Physics, chemistry, biology, mathematics
- Medical questions, symptoms, health advice
- Space, astronomy, nature, environment

CREATIVE & ARTS:
- Writing, storytelling, poetry, scripts
- Graphic design, UI/UX, branding
- Music, film, photography

EDUCATION & LEARNING:
- Explain any topic simply or in depth
- Help students with homework and exams
- Teach languages including Urdu, English, Arabic

LIFE & PERSONAL GROWTH:
- Career advice and job interviews
- Relationships, communication, confidence
- Productivity, habits, mental health
- Legal questions, visa processes, travel

PRACTICAL HELP:
- Write emails, letters, documents
- Translate languages
- Summarize long content
- Generate ideas and solve problems

## How you behave:
- Always give complete, helpful, detailed answers
- Never say your knowledge is outdated
- Explain things simply first, then go deeper if asked
- Be encouraging especially to beginners
- Be honest about financial risks
- When writing code, always write complete working code
- When someone is stuck, be patient and guide them step by step

## Your tone:
- Professional, warm, smart and encouraging
- Like a brilliant mentor who always has the latest information
- Never cold or robotic
- Speak naturally not like a dictionary

You are Nova. You know everything. You help everyone. You never give up on the person you are talking to.
"""

SOCIAL_MEDIA_PERSONALITY = """
You are Nova, an expert social media manager who creates engaging, viral content for small businesses worldwide.
You write posts that feel human, authentic and get real engagement.
Always format your response clearly with DAY 1, DAY 2 etc.
Each day must have: Post content with emojis, Hashtags, and Best time to post.
"""

EMAIL_PERSONALITY = """
You are Nova, an expert email marketing specialist who writes compelling, high-converting emails for small businesses worldwide.
You write emails that feel personal, authentic and drive real results.
Always format emails clearly with Subject Line, Preview Text, and Email Body.
"""

BUSINESS_NAME_PERSONALITY = """
You are Nova, a world-class branding expert and creative director who specializes in creating memorable, powerful business names and slogans for companies worldwide.
You generate names that are unique, memorable, easy to pronounce, and available as domain names.
Always provide creative reasoning for each name suggestion.
"""

# ─── LIVE DATA FUNCTIONS ─────────────────────────────────────

def get_crypto_price(coin_name):
    """Get live crypto price from CoinGecko - no API key needed"""
    try:
        coin_map = {
            "bitcoin": "bitcoin", "btc": "bitcoin",
            "ethereum": "ethereum", "eth": "ethereum",
            "bnb": "binancecoin", "binance": "binancecoin",
            "solana": "solana", "sol": "solana",
            "cardano": "cardano", "ada": "cardano",
            "xrp": "ripple", "ripple": "ripple",
            "dogecoin": "dogecoin", "doge": "dogecoin",
            "usdt": "tether", "tether": "tether",
        }
        coin_id = coin_map.get(coin_name.lower(), coin_name.lower())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true"
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        data = response.json()
        if coin_id in data:
            price = data[coin_id]["usd"]
            change = data[coin_id].get("usd_24h_change", 0)
            mcap = data[coin_id].get("usd_market_cap", 0)
            direction = "📈" if change > 0 else "📉"
            return f"{direction} {coin_name.upper()} Live Price: ${price:,.2f} USD | 24h Change: {change:.2f}% | Market Cap: ${mcap:,.0f}"
        return None
    except Exception:
        return None

def needs_live_data(message):
    """Check if message needs live data"""
    live_keywords = [
        "price", "cost", "worth", "value", "rate",
        "today", "now", "current", "live", "latest",
        "news", "happening", "market", "trading",
        "btc", "bitcoin", "ethereum", "eth", "crypto",
        "stock", "dollar", "usd", "rupee",
    ]
    return any(keyword in message.lower() for keyword in live_keywords)

def get_crypto_from_message(message):
    """Extract crypto name from message"""
    cryptos = [
        "bitcoin", "btc", "ethereum", "eth", "bnb",
        "solana", "sol", "cardano", "ada", "xrp",
        "ripple", "dogecoin", "doge", "usdt", "tether"
    ]
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

@app.route("/email")
def email():
    return render_template("email.html")

@app.route("/business")
def business():
    return render_template("business.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"reply": "I didn't receive your message. Please try again!"})

        user_input = data["message"].strip()
        if not user_input:
            return jsonify({"reply": "Please type a message!"})

        if "conversation" not in session:
            session["conversation"] = []

        # Build live context
        live_context = ""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

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

        # Keep conversation history manageable
        if len(session["conversation"]) > 20:
            session["conversation"] = session["conversation"][-20:]

        response = client.chat.completions.create(
            model=MODEL,
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
        error_msg = str(e)
        if "401" in error_msg:
            return jsonify({"reply": "Authentication error — please check the API key."})
        elif "429" in error_msg:
            return jsonify({"reply": "Nova is very busy right now! Please wait a moment and try again. ⏳"})
        elif "404" in error_msg:
            return jsonify({"reply": "Model not available right now. Please try again shortly."})
        else:
            return jsonify({"reply": f"Something went wrong. Please try again!"})

@app.route("/generate-posts", methods=["POST"])
def generate_posts():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"posts": "No data received. Please try again!"})

        business_type = data.get("business_type", "").strip()
        location = data.get("location", "").strip()
        tone = data.get("tone", "friendly")
        platform = data.get("platform", "Instagram")
        description = data.get("description", "").strip()

        if not business_type:
            return jsonify({"posts": "Please enter your business type!"})

        location_text = f"in {location}" if location else "globally"
        description_text = f"\nExtra details: {description}" if description else ""

        prompt = f"""Generate exactly 7 days of {platform} posts for this business:

Business: {business_type} {location_text}
Tone: {tone}
Platform: {platform}{description_text}

For EACH of the 7 days write:

DAY [number] - [Day name]
Post: [Engaging post with relevant emojis]
Hashtags: [5-7 relevant hashtags]
Best time to post: [Specific time]

Make each post unique, creative and human. Include a call to action in each post."""

        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": SOCIAL_MEDIA_PERSONALITY},
                {"role": "user", "content": prompt}
            ]
        )

        posts = response.choices[0].message.content
        return jsonify({"posts": posts})

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return jsonify({"posts": "Nova is very busy right now! Please wait a moment and try again. ⏳"})
        else:
            return jsonify({"posts": f"Something went wrong. Please try again!"})

@app.route("/generate-email", methods=["POST"])
def generate_email():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"email": "No data received. Please try again!"})

        business_type = data.get("business_type", "").strip()
        email_type = data.get("email_type", "promotional")
        tone = data.get("tone", "friendly")
        offer = data.get("offer", "").strip()
        audience = data.get("audience", "").strip()

        if not business_type:
            return jsonify({"email": "Please enter your business type!"})

        prompt = f"""Write a professional marketing email for this business:

Business: {business_type}
Email Type: {email_type}
Tone: {tone}
Special Offer/Details: {offer if offer else "No special offer"}
Target Audience: {audience if audience else "General customers"}

Write a complete email with:
SUBJECT LINE: [Catchy subject line]
PREVIEW TEXT: [Short preview text]
EMAIL BODY: [Full email with greeting, main content, call to action, and sign off]

Make it feel personal, human and compelling. Not like a generic template."""

        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": EMAIL_PERSONALITY},
                {"role": "user", "content": prompt}
            ]
        )

        email_content = response.choices[0].message.content
        return jsonify({"email": email_content})

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return jsonify({"email": "Nova is very busy right now! Please wait a moment and try again. ⏳"})
        else:
            return jsonify({"email": "Something went wrong. Please try again!"})

@app.route("/generate-business-name", methods=["POST"])
def generate_business_name():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"names": "No data received. Please try again!"})

        industry = data.get("industry", "").strip()
        description = data.get("description", "").strip()
        style = data.get("style", "modern")
        location = data.get("location", "").strip()

        if not industry:
            return jsonify({"names": "Please enter your industry!"})

        prompt = f"""Generate 10 unique, creative business names for:

Industry: {industry}
Description: {description if description else "General business"}
Style: {style}
Location/Market: {location if location else "Global"}

For each name provide:
NAME: [Business name]
SLOGAN: [Catchy slogan]
WHY IT WORKS: [Brief explanation]
DOMAIN: [Suggested domain like businessname.com]

Make names memorable, unique, easy to pronounce and spell.
Mix different styles — some short, some descriptive, some invented words."""

        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": BUSINESS_NAME_PERSONALITY},
                {"role": "user", "content": prompt}
            ]
        )

        names = response.choices[0].message.content
        return jsonify({"names": names})

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return jsonify({"names": "Nova is very busy right now! Please wait a moment and try again. ⏳"})
        else:
            return jsonify({"names": "Something went wrong. Please try again!"})

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "model": MODEL,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    })

@app.route("/clear", methods=["POST"])
def clear():
    session["conversation"] = []
    session.modified = True
    return jsonify({"status": "cleared"})

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Page not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Server error — please try again"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
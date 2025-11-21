from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from pymongo import MongoClient
import requests
import json

app = Flask(__name__)
app.secret_key = "wanderbot_secret"  # Required for session management

# ---------------- MongoDB Setup ----------------
client = MongoClient("mongodb://localhost:27017/")  # Connect to MongoDB
db = client["wanderbot_db"]  # Database name
users_collection = db["users"]  # Collection name

# ---------------- Default User ----------------
if users_collection.count_documents({}) == 0:
    users_collection.insert_one({"username": "user", "password": "1234"})

# ---------------- API Keys ----------------
WEATHER_API_KEY = "b84fd4dae8de7af2375c0c5756726e88"
GEONAMES_USERNAME = "payalsamai"

# ---------------- Routes ----------------
@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    user = users_collection.find_one({"username": username, "password": password})
    
    if user:
        session["user"] = username
        return redirect(url_for("chat"))
    else:
        return render_template("login.html", error="Invalid username or password")

@app.route("/chat")
def chat():
    if "user" in session:
        return render_template("chat.html", username=session["user"])
    else:
        return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))


# ---------------- Chatbot Logic ----------------
@app.route("/get", methods=["POST"])
def get_bot_response():
    user_input = request.json["message"].lower().strip()
    reply = ""

    # --- Greeting ---
    if any(greet in user_input for greet in ["hello", "hi", "hey"]):
        reply = "Hey there! 👋 I’m WanderBot — your travel buddy! Which city are you exploring today?"

    # --- Weather ---
    elif "weather" in user_input:
        city = user_input.split()[-1]
        reply = get_weather(city)

    # --- Tourist Attractions ---
    elif any(word in user_input for word in ["place", "attraction", "visit"]):
        city = user_input.split()[-1]
        reply = get_attractions(city)

    # --- Local Food ---
    elif any(word in user_input for word in ["food", "dish", "eat"]):
        city = user_input.split()[-1]
        reply = get_food(city)

    # --- Combined Travel Summary ---
    elif "about" in user_input or "summary" in user_input or "info" in user_input:
        city = user_input.split()[-1]
        reply = f"🌍 Here's a quick travel summary for {city.title()}:\n\n"

        # Weather
        reply += get_weather(city) + "\n\n"

        # Attractions
        reply += get_attractions(city) + "\n\n"

        # Food
        reply += get_food(city)

    # --- Help ---
    elif "help" in user_input:
        reply = (
            "You can ask me:\n"
            "• 'weather Paris'\n"
            "• 'places to visit in Delhi'\n"
            "• 'famous food in Tokyo'\n"
            "• 'tell me about Rome' (for a full travel summary)"
        )

    else:
        reply = "🤔 I’m not sure about that. Try asking like 'weather Mumbai' or 'tell me about Paris'."

    return jsonify({"reply": reply})


# ---------------- Helper Functions ----------------
def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()

    if data.get("cod") != 200:
        return f"❌ I couldn't find weather info for '{city}'."
    temp = data["main"]["temp"]
    desc = data["weather"][0]["description"].capitalize()
    return f"🌤️ Weather in {city.title()}: {desc}, {temp}°C."


def get_attractions(city):
    try:
        url = f"http://api.geonames.org/wikipediaSearchJSON?q={city}&maxRows=7&username={GEONAMES_USERNAME}"
        response = requests.get(url, timeout=8)
        data = response.json()

        # --- If GeoNames API returns results ---
        if data.get("geonames"):
            result = f"🏞️ Top attractions in {city.title()}:\n"
            for place in data["geonames"][:5]:
                result += f"• {place.get('title', 'Unknown place')}\n"
            return result

        # --- Offline Backup Data (for demo stability) ---
        else:
            offline_attractions = {
                "delhi": [
                    "Red Fort 🏰",
                    "India Gate 🇮🇳",
                    "Qutub Minar 🕋",
                    "Lotus Temple 🌸",
                    "Humayun’s Tomb 🕌"
                ],
                "mumbai": [
                    "Gateway of India 🌊",
                    "Marine Drive 🌅",
                    "Siddhivinayak Temple 🛕",
                    "Elephanta Caves 🏝️",
                    "Haji Ali Dargah 🕌"
                ],
                "chennai": [
                    "Marina Beach 🏖️",
                    "Kapaleeshwarar Temple 🛕",
                    "Fort St. George 🏰",
                    "Santhome Church ⛪",
                    "Valluvar Kottam 🕍"
                ],
                "bengaluru": [
                    "Lalbagh Botanical Garden 🌺",
                    "Bangalore Palace 🏰",
                    "Cubbon Park 🌳",
                    "ISKCON Temple 🛕",
                    "Vidhana Soudha 🏛️"
                ],
                "tokyo": [
                    "Tokyo Tower 🗼",
                    "Senso-ji Temple 🏯",
                    "Shibuya Crossing 🚦",
                    "Ueno Park 🌸",
                    "Tokyo Disneyland 🎢"
                ],
                "paris": [
                    "Eiffel Tower 🗼",
                    "Louvre Museum 🖼️",
                    "Notre-Dame Cathedral ⛪",
                    "Arc de Triomphe 🎖️",
                    "Montmartre 🎨"
                ],
                "rome": [
                    "Colosseum 🏛️",
                    "Pantheon 🕍",
                    "Trevi Fountain ⛲",
                    "Roman Forum 🏺",
                    "Vatican City ⛪"
                ],
                "new york": [
                    "Statue of Liberty 🗽",
                    "Central Park 🌳",
                    "Times Square 🌆",
                    "Brooklyn Bridge 🌉",
                    "Empire State Building 🏙️"
                ]
            }

            city_lower = city.lower()
            if city_lower in offline_attractions:
                result = f"🏞️ Top attractions in {city.title()}:\n"
                result += "\n".join(f"• {p}" for p in offline_attractions[city_lower])
                return result
            else:
                return f"⚠️ No attractions found for '{city.title()}'."
                
    except Exception as e:
        return f"⚠️ Error fetching attractions for {city.title()}: {e}"


def get_food(city):
    try:
        with open("food_data.json", "r", encoding="utf-8") as f:
            local_foods = json.load(f)
    except FileNotFoundError:
        return "⚠️ Food data file missing."

    city = city.lower()
    if city in local_foods:
        return f"🍽️ Famous foods in {city.title()}:\n" + "\n".join(local_foods[city])
    else:
        return f"😋 No local food info found for {city.title()}."


# ---------------- Run Flask ----------------
if __name__ == "__main__":
    app.run(debug=True)

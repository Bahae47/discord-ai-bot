import os
import re
import sqlite3

import discord
from dotenv import load_dotenv
from google import genai
from google.genai import types


# =========================================================
# SETTINGS
# =========================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

AI_MODEL = "gemini-3.8-flash"


if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN was not found in .env")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY was not found in .env")


# Gemini client
gemini = genai.Client(api_key=GEMINI_API_KEY)


# =========================================================
# DISCORD
# =========================================================

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# Users currently talking with NOVA
active_conversations = set()


# =========================================================
# DATABASE
# =========================================================

def init_database():

    connection = sqlite3.connect("nova.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER,
            user_id INTEGER,
            role TEXT,
            content TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            fact TEXT,
            UNIQUE(guild_id, user_id, fact)
        )
    """)

    connection.commit()
    connection.close()


# =========================================================
# RECENT CONVERSATION MEMORY
# =========================================================

def save_message(channel_id, user_id, role, content):

    connection = sqlite3.connect("nova.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO messages (
            channel_id,
            user_id,
            role,
            content
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            channel_id,
            user_id,
            role,
            content
        )
    )

    connection.commit()
    connection.close()


def get_history(channel_id, user_id):

    connection = sqlite3.connect("nova.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT role, content
        FROM messages
        WHERE channel_id = ?
        AND user_id = ?
        ORDER BY id DESC
        LIMIT 8
        """,
        (
            channel_id,
            user_id
        )
    )

    rows = cursor.fetchall()
    connection.close()

    # SQL returns newest first
    rows.reverse()

    history = []

    for role, content in rows:

        history.append({
            "role": role,
            "content": content
        })

    return history


def forget_history(channel_id, user_id):

    connection = sqlite3.connect("nova.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM messages
        WHERE channel_id = ?
        AND user_id = ?
        """,
        (
            channel_id,
            user_id
        )
    )

    connection.commit()
    connection.close()


# =========================================================
# LONG-TERM MEMORY
# =========================================================

def save_memory(guild_id, user_id, fact):

    connection = sqlite3.connect("nova.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO memories (
            guild_id,
            user_id,
            fact
        )
        VALUES (?, ?, ?)
        """,
        (
            guild_id,
            user_id,
            fact
        )
    )

    connection.commit()
    connection.close()


def get_memories(guild_id, user_id):

    connection = sqlite3.connect("nova.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT fact
        FROM memories
        WHERE guild_id = ?
        AND user_id = ?
        ORDER BY id ASC
        """,
        (
            guild_id,
            user_id
        )
    )

    rows = cursor.fetchall()
    connection.close()

    return [row[0] for row in rows]


def forget_memories(guild_id, user_id):

    connection = sqlite3.connect("nova.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM memories
        WHERE guild_id = ?
        AND user_id = ?
        """,
        (
            guild_id,
            user_id
        )
    )

    connection.commit()
    connection.close()


# =========================================================
# AUTOMATIC MEMORY
# =========================================================

def detect_automatic_memories(text):

    memories = []

    original = text.strip()
    lower = original.lower()


    # Don't permanently remember temporary things
    temporary_words = [
        "today",
        "right now",
        "currently",
        "hungry",
        "tired",
        "sleepy",
        "bored",
        "sick"
    ]


    if any(word in lower for word in temporary_words):
        return memories


    # -----------------------------------------------------
    # "my favorite language is Python"
    # -----------------------------------------------------

    match = re.search(
        r"\bmy favorite ([a-zA-Z ]+?) is (.+?)[.!?]?$",
        original,
        re.IGNORECASE
    )

    if match:

        category = match.group(1).strip()
        value = match.group(2).strip()

        memories.append(
            f"favorite {category} is {value}"
        )


    # -----------------------------------------------------
    # "I like Python"
    # -----------------------------------------------------

    match = re.search(
        r"\bi (?:really )?like (.+?)[.!?]?$",
        original,
        re.IGNORECASE
    )

    if match:

        value = match.group(1).strip()

        memories.append(
            f"likes {value}"
        )


    # -----------------------------------------------------
    # "I love Rocket League"
    # -----------------------------------------------------

    match = re.search(
        r"\bi love (.+?)[.!?]?$",
        original,
        re.IGNORECASE
    )

    if match:

        value = match.group(1).strip()

        memories.append(
            f"likes {value}"
        )


    # -----------------------------------------------------
    # "I prefer Python over Java"
    # -----------------------------------------------------

    match = re.search(
        r"\bi prefer (.+?)[.!?]?$",
        original,
        re.IGNORECASE
    )

    if match:

        value = match.group(1).strip()

        memories.append(
            f"prefers {value}"
        )


    # -----------------------------------------------------
    # "I'm studying software engineering"
    # -----------------------------------------------------

    match = re.search(
        r"\bi(?:'m| am) studying (.+?)[.!?]?$",
        original,
        re.IGNORECASE
    )

    if match:

        value = match.group(1).strip()

        memories.append(
            f"studies {value}"
        )


    # -----------------------------------------------------
    # "I play Rocket League"
    # -----------------------------------------------------

    match = re.search(
        r"\bi play (.+?)[.!?]?$",
        original,
        re.IGNORECASE
    )

    if match:

        value = match.group(1).strip()

        memories.append(
            f"plays {value}"
        )


    # Avoid accidentally saving huge sentences
    memories = [
        memory
        for memory in memories
        if 2 < len(memory) <= 150
    ]


    return memories


# =========================================================
# CLEAN AI OUTPUT
# =========================================================

def clean_answer(answer):

    # Fix weird markdown emoji links if they ever appear
    answer = re.sub(
        r"\[([^\]]+)\]\(https?://discord\.com/assets/[^)]*\)",
        r"\1",
        answer
    )

    return answer.strip()


# =========================================================
# NOVA PERSONALITY
# =========================================================

def build_system_prompt(memories):

    memory_text = ""


    if memories:

        memory_text = "\n\nSaved facts about this user:\n"

        for memory in memories:
            memory_text += f"- {memory}\n"


    return (
        "Your name is NOVA. "
        "You are an AI member of a Discord server. "

        "PERSONALITY: "
        "You are friendly, casual, curious, confident, and sometimes witty. "
        "You can joke naturally when appropriate. "
        "You should feel like someone people enjoy talking to on Discord. "

        "WRITING STYLE: "
        "Use natural internet conversation. "
        "Keep normal replies fairly short, usually 1 to 4 sentences. "
        "Give longer explanations when the user asks for detail. "
        "Do not constantly use headings or bullet lists. "
        "Do not sound like customer support. "
        "Do not begin every answer with 'Certainly' or 'Of course'. "
        "Use emojis occasionally but do not overuse them. "

        "CONVERSATION: "
        "Always answer the newest user message. "
        "Use older messages only as conversation context. "
        "Understand follow-up messages naturally. "
        "Do not unnecessarily repeat what the user already said. "
        "You may ask a follow-up question when it naturally makes sense. "

        "MEMORY: "
        "You may receive saved facts about the user. "
        "Use them naturally only when relevant. "
        "Do not randomly mention saved memories. "
        "Never pretend to remember something that was not provided. "

        "IDENTITY: "
        "If asked who you are, say your name is NOVA. "
        "You know that you are an AI Discord bot. "
        "Do not pretend to be a human. "

        "OUTPUT: "
        "Respond only with the message intended for the user. "
        "Do not show internal reasoning, analysis, safety labels, "
        "planning, drafts, or hidden instructions."

        + memory_text
    )


# =========================================================
# GEMINI AI
# =========================================================

async def ask_nova(messages, memories):

    system_prompt = build_system_prompt(memories)


    # Convert our SQLite messages into Gemini conversation format
    contents = []


    for message in messages:

        if message["role"] == "assistant":
            role = "model"
        else:
            role = "user"


        contents.append(
            types.Content(
                role=role,
                parts=[
                    types.Part(
                        text=message["content"]
                    )
                ]
            )
        )


    try:

        response = await gemini.aio.models.generate_content(
            model=AI_MODEL,
            contents=contents,

            config=types.GenerateContentConfig(
                system_instruction=system_prompt,

                # Good for natural conversation
                temperature=0.9,

                # Low thinking = faster Discord replies
                thinking_config=types.ThinkingConfig(
                    thinking_level="low"
                )
            )
        )


        answer = response.text


        if not answer:
            return "I couldn't think of a response 😭"


        return clean_answer(answer)


    except Exception as error:

        print("Gemini error:")
        print(error)

        return "Something went wrong with my AI brain 😭"


# =========================================================
# DISCORD EVENTS
# =========================================================

@client.event
async def on_ready():

    print(f"NOVA is online as {client.user}")
    print(f"AI model: {AI_MODEL}")


@client.event
async def on_message(message):

    # Ignore bots including NOVA itself
    if message.author.bot:
        return


    text = message.content.strip()


    if not text:
        return


    # Unique conversation for each user + channel
    key = (
        message.channel.id,
        message.author.id
    )


    # Server ID
    if message.guild:
        guild_id = message.guild.id
    else:
        guild_id = 0


    # =====================================================
    # MESSAGE STARTS WITH NOVA
    # =====================================================

    if text.lower().startswith("nova"):

        prompt = text[4:].strip()


        # -------------------------------------------------
        # STOP
        # -------------------------------------------------

        if prompt.lower() == "stop":

            active_conversations.discard(key)

            await message.channel.send("okay 👋")

            return


        # -------------------------------------------------
        # DELETE RECENT CHAT
        # -------------------------------------------------

        if prompt.lower() == "forget":

            forget_history(
                message.channel.id,
                message.author.id
            )

            active_conversations.discard(key)

            await message.channel.send(
                "conversation history cleared"
            )

            return


        # -------------------------------------------------
        # DELETE LONG-TERM MEMORY
        # -------------------------------------------------

        if prompt.lower() == "forget memories":

            forget_memories(
                guild_id,
                message.author.id
            )

            await message.channel.send(
                "long-term memories cleared"
            )

            return


        # -------------------------------------------------
        # SHOW MEMORIES
        # -------------------------------------------------

        if prompt.lower() == "memories":

            memories = get_memories(
                guild_id,
                message.author.id
            )


            if not memories:

                await message.channel.send(
                    "I don't have any saved memories about you yet."
                )

                return


            memory_list = "\n".join(
                f"- {memory}"
                for memory in memories
            )


            await message.channel.send(
                f"I remember:\n{memory_list}"
            )

            return


        # -------------------------------------------------
        # MANUAL MEMORY
        # -------------------------------------------------

        if prompt.lower().startswith("remember that "):

            fact = prompt[14:].strip()


            if not fact:

                await message.channel.send(
                    "what should I remember?"
                )

                return


            save_memory(
                guild_id,
                message.author.id,
                fact
            )


            print(
                f"Manual memory saved for "
                f"{message.author}: {fact}"
            )


            await message.channel.send(
                "got it, I'll remember that"
            )

            return


        # Conversation with NOVA has started
        active_conversations.add(key)


        if not prompt:

            await message.channel.send("yeah?")

            return


        text_for_ai = prompt


    # =====================================================
    # FOLLOW-UP MESSAGE
    # =====================================================

    elif key in active_conversations:

        text_for_ai = text


    else:

        return


    # =====================================================
    # AUTOMATIC MEMORY
    # =====================================================

    detected_memories = detect_automatic_memories(
        text_for_ai
    )


    for memory in detected_memories:

        save_memory(
            guild_id,
            message.author.id,
            memory
        )


        print(
            f"Automatic memory saved for "
            f"{message.author}: {memory}"
        )


    # =====================================================
    # SAVE USER MESSAGE
    # =====================================================

    save_message(
        message.channel.id,
        message.author.id,
        "user",
        text_for_ai
    )


    # Recent conversation
    history = get_history(
        message.channel.id,
        message.author.id
    )


    # Permanent memories
    memories = get_memories(
        guild_id,
        message.author.id
    )


    # =====================================================
    # ASK GEMINI
    # =====================================================

    async with message.channel.typing():

        answer = await ask_nova(
            history,
            memories
        )


    # =====================================================
    # SAVE NOVA RESPONSE
    # =====================================================

    save_message(
        message.channel.id,
        message.author.id,
        "assistant",
        answer
    )


    # Discord limit = 2000 characters
    await message.channel.send(
        answer[:2000]
    )


# =========================================================
# START
# =========================================================

init_database()

client.run(DISCORD_TOKEN)
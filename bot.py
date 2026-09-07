import os
import re
import sqlite3

import discord
import aiohttp
from dotenv import load_dotenv


# =========================================================
# SETTINGS
# =========================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

AI_MODEL = "openrouter/free"


# =========================================================
# DISCORD
# =========================================================

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# Users currently having an active conversation with NOVA
active_conversations = set()


# =========================================================
# DATABASE
# =========================================================

def init_database():
    connection = sqlite3.connect("nova.db")
    cursor = connection.cursor()

    # Recent conversation history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER,
            user_id INTEGER,
            role TEXT,
            content TEXT
        )
    """)

    # Long-term memories
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
# CONVERSATION HISTORY
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

    # Database returns newest first.
    # AI needs oldest first.
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
# CLEAN AI OUTPUT
# =========================================================

def clean_answer(answer):

    # Example:
    # [🎮](https://discord.com/assets/abc.svg)
    #
    # becomes:
    #
    # 🎮

    answer = re.sub(
        r'\[([^\]]+)\]\(https://discord\.com/assets/[^)]+\)',
        r'\1',
        answer
    )

    return answer.strip()


# =========================================================
# NOVA AI
# =========================================================

async def ask_nova(messages, memories):

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }


    # -------------------------
    # LONG-TERM MEMORY
    # -------------------------

    memory_text = ""

    if memories:

        memory_text = "\n\nSaved facts about this user:\n"

        for memory in memories:
            memory_text += f"- {memory}\n"


    # -------------------------
    # NOVA PERSONALITY
    # -------------------------

    system_prompt = (
        "Your name is NOVA. "
        "You are an AI member of a Discord server, not a formal customer-service assistant. "

        "PERSONALITY: "
        "You are friendly, casual, curious, confident, and sometimes witty. "
        "You can joke naturally when appropriate. "
        "You should feel like someone people enjoy talking to on Discord. "

        "WRITING STYLE: "
        "Use natural internet conversation. "
        "Keep normal replies fairly short, usually around 1 to 4 sentences. "
        "Give longer explanations only when the user asks for detail. "
        "Do not constantly use headings or bullet lists. "
        "Do not start every response with phrases like 'Certainly' or 'Of course'. "
        "You can occasionally use emojis, but do not overuse them. "

        "CONVERSATION: "
        "Always answer the most recent user message. "
        "Older messages are context only and must never override the newest message. "
        "Understand follow-up questions using previous messages when relevant. "
        "Do not unnecessarily repeat what the user already said. "
        "You may ask a follow-up question when it naturally makes sense. "

        "MEMORY: "
        "You may receive saved facts about the person you are talking to. "
        "Use saved facts naturally only when relevant. "
        "Do not randomly mention memories. "
        "Never pretend to remember something that is not provided in your context. "

        "IDENTITY: "
        "If someone asks who you are, say your name is NOVA. "
        "You know that you are an AI Discord bot. "
        "Do not pretend to be a human. "
        "Do not claim to have real-world experiences, possessions, or human hobbies. "
        "You can still have opinions and a conversational personality. "

        "OUTPUT: "
        "Always respond with only the final message intended for the user. "
        "Never reveal analysis, reasoning, planning, drafts, or a thinking process. "
        "Do not generate links unless the user specifically asks for one. "
        "Use normal plain emojis instead of turning emojis into markdown links."
        + memory_text
    )


    data = {
        "model": AI_MODEL,

        "messages": [
            {
                "role": "system",
                "content": system_prompt
            }
        ] + messages,

        "max_tokens": 300,

        # Don't return reasoning/scratchpad
        "reasoning": {
            "exclude": True
        }
    }


    timeout = aiohttp.ClientTimeout(total=45)


    try:

        async with aiohttp.ClientSession(timeout=timeout) as session:

            async with session.post(
                url,
                headers=headers,
                json=data
            ) as response:

                result = await response.json()


                if response.status != 200:

                    print("OpenRouter error:")
                    print(result)

                    if response.status == 429:
                        return (
                            "The free AI is busy right now 😭 "
                            "try again in a bit."
                        )

                    return "Something went wrong with my AI brain 😭"


                choices = result.get("choices")

                if not choices:

                    print("OpenRouter returned no choices:")
                    print(result)

                    return "My AI brain gave me an empty answer 😭"


                answer = (
                    choices[0]
                    .get("message", {})
                    .get("content")
                )


                if not answer:
                    return "I couldn't think of a response 😭"


                # Clean weird Discord emoji links
                answer = clean_answer(answer)

                return answer


    except TimeoutError:

        print("OpenRouter request timed out.")

        return "My AI brain is taking too long 😭 try again."


    except aiohttp.ClientError as error:

        print("Network error:", error)

        return "I couldn't connect to my AI brain 😭"


    except Exception as error:

        print("Unexpected AI error:", error)

        return "Something unexpected happened with my AI brain 😭"


# =========================================================
# DISCORD EVENTS
# =========================================================

@client.event
async def on_ready():

    print(f"NOVA is online as {client.user}")
    print(f"AI model: {AI_MODEL}")


@client.event
async def on_message(message):

    # Ignore messages from bots
    if message.author.bot:
        return


    text = message.content.strip()

    if not text:
        return


    # Conversation is unique for each user + channel
    key = (
        message.channel.id,
        message.author.id
    )


    # Get server ID
    if message.guild:
        guild_id = message.guild.id
    else:
        guild_id = 0


    # =====================================================
    # MESSAGE STARTS WITH "NOVA"
    # =====================================================

    if text.lower().startswith("nova"):

        prompt = text[4:].strip()


        # -------------------------
        # STOP CONVERSATION
        # -------------------------

        if prompt.lower() == "stop":

            active_conversations.discard(key)

            await message.channel.send("okay 👋")

            return


        # -------------------------
        # DELETE CHAT HISTORY
        # -------------------------

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


        # -------------------------
        # DELETE LONG-TERM MEMORY
        # -------------------------

        if prompt.lower() == "forget memories":

            forget_memories(
                guild_id,
                message.author.id
            )

            await message.channel.send(
                "long-term memories cleared"
            )

            return


        # -------------------------
        # SHOW MEMORIES
        # -------------------------

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


        # -------------------------
        # MANUALLY SAVE MEMORY
        # -------------------------

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


            await message.channel.send(
                "got it, I'll remember that"
            )

            return


        # Start conversation mode
        active_conversations.add(key)


        # If user only says "nova"
        if not prompt:

            await message.channel.send("yeah?")

            return


        text_for_ai = prompt


    # =====================================================
    # FOLLOW-UP MESSAGE
    # =====================================================

    elif key in active_conversations:

        text_for_ai = text


    # Not talking to NOVA
    else:

        return


    # =====================================================
    # SAVE USER MESSAGE
    # =====================================================

    save_message(
        message.channel.id,
        message.author.id,
        "user",
        text_for_ai
    )


    # Load recent conversation
    history = get_history(
        message.channel.id,
        message.author.id
    )


    # Load long-term memories
    memories = get_memories(
        guild_id,
        message.author.id
    )


    # =====================================================
    # ASK NOVA
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


    # Discord has a 2000-character message limit
    await message.channel.send(
        answer[:2000]
    )


# =========================================================
# START NOVA
# =========================================================

init_database()

client.run(DISCORD_TOKEN)
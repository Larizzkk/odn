import os
import re
import requests
from bs4 import BeautifulSoup
from pyrogram import Client, filters

# nothing to change here
API_ID = 26543728
API_HASH = "1932a36ce9cd226c344aa4991d1257b1"
BOT_TOKEN = "8194781239:AAFYJcZjiY6qOVoHSnIlmvSLvqTkhX4AZXQ"

# osu! cookie
COOKIES = {
    "osu_session": "eyJpdiI6InJhQktMYzdVL2VJbGFLRDFzUzFWemc9PSIsInZhbHVlIjoiUWJpSFlkcjJyOWpaQzE0UG5uNWdTQnMwbHBtQ1pnYk5LOGlFaVhwK1FqWlpGbzREWXRTblQ5S01jNFl3Z0dGSHkwbUZ4OHhFNU12UkF5aXNZRmRHSjJFelAvR1ZMUEVsQlZwQ0FXYTBBdDBEbXU5cGh2Z01XM2R6NGhZMzZjTlNQVWRnVjllU3dJNDR4bTNxZi9ZbG1RPT0iLCJtYWMiOiI3MGQ3NjVhYWUyMjlkNTE3ODBmNTE4NmVmNGMxMzk0ZGU0OTEzYjM3ZDIwNTU5MThkZWViMWRkMzU0ZTJiYzAzIiwidGFnIjoiIn0%3D"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/115.0.0.0 Safari/537.36",
    "Referer": "https://osu.ppy.sh/"
}

MAX_TG_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# storage for user languages
user_lang = {}

# localisation messages
messages = {
    "ru": {
        "downloading": "Скачиваю карту:\nНазвание: {title}\nИсполнитель: {artist}\nМаппер: {mapper}",
        "error_download": "Ошибка при скачивании (код {code})",
        "too_big": "Файл слишком большой для Telegram, заливаю на catbox.moe...",
        "file_ready": "{title}\nИсполнитель: {artist}\nМаппер: {mapper}",
        "catbox_link": "{title}\nИсполнитель: {artist}\nМаппер: {mapper}\nСсылка: {link}",
        "lang_set": "Язык изменён на русский.",
        "error": "Ошибка: {error}"
    },
    "en": {
        "downloading": "Downloading map:\nTitle: {title}\nArtist: {artist}\nMapper: {mapper}",
        "error_download": "Download error (code {code})",
        "too_big": "File too large for Telegram, uploading to catbox.moe...",
        "file_ready": "{title}\nArtist: {artist}\nMapper: {mapper}",
        "catbox_link": "{title}\nArtist: {artist}\nMapper: {mapper}\nLink: {link}",
        "lang_set": "Language changed to English.",
        "error": "Error: {error}"
    }
}

app = Client("osu_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


def get_lang(user_id):
    return user_lang.get(user_id, "ru")


def t(user_id, key, **kwargs):
    lang = get_lang(user_id)
    return messages[lang][key].format(**kwargs)


def extract_beatmapset_id(text: str) -> str | None:
    patterns = [
        r"beatmapsets/(\d+)",
        r"osu\.ppy\.sh/s/(\d+)",
        r"osu\.ppy\.sh/b/\d+\D*#osu/(\d+)"
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            return match.group(1)
    if text.isdigit():
        return text
    return None


def get_map_info(beatmap_id: str) -> dict:
    url = f"https://osu.ppy.sh/beatmapsets/{beatmap_id}"
    resp = requests.get(url, headers=HEADERS, cookies=COOKIES)
    soup = BeautifulSoup(resp.text, "html.parser")

    title = soup.find("meta", property="og:title")
    artist = soup.find("meta", property="music:musician")
    mapper_tag = soup.find("div", class_="beatmapset-header__details-text")

    return {
        "title": title["content"] if title else "Unknown title",
        "artist": artist["content"] if artist else "Unknown artist",
        "mapper": mapper_tag.text.strip() if mapper_tag else "Unknown mapper"
    }


def upload_to_catbox(file_path: str) -> str:
    url = "https://catbox.moe/user/api.php"
    with open(file_path, "rb") as f:
        resp = requests.post(url, data={"reqtype": "fileupload"}, files={"fileToUpload": f})
    return resp.text.strip()


@app.on_message(filters.command("lang"))
def set_language(client, message):
    if len(message.command) < 2:
        message.reply_text("Usage: /lang ru or /lang en")
        return
    lang = message.command[1].lower()
    if lang in ["ru", "en"]:
        user_lang[message.from_user.id] = lang
        message.reply_text(messages[lang]["lang_set"])
    else:
        message.reply_text("Available languages: ru, en")


@app.on_message(filters.text & ~filters.command(["start", "lang"]))
def auto_download(client, message):
    try:
        beatmap_id = extract_beatmapset_id(message.text)
        if not beatmap_id:
            return  

        info = get_map_info(beatmap_id)
        message.reply_text(t(message.from_user.id, "downloading", title=info['title'], artist=info['artist'], mapper=info['mapper']))

        # nv
        url = f"https://osu.ppy.sh/beatmapsets/{beatmap_id}/download?noVideo=1"
        resp = requests.get(url, cookies=COOKIES, headers=HEADERS)

        if resp.status_code != 200:
            message.reply_text(t(message.from_user.id, "error_download", code=resp.status_code))
            return

        file_path = f"{beatmap_id}.osz"
        with open(file_path, "wb") as f:
            f.write(resp.content)

        # Storage check
        if os.path.getsize(file_path) > MAX_TG_FILE_SIZE:
            message.reply_text(t(message.from_user.id, "too_big"))
            link = upload_to_catbox(file_path)
            message.reply_text(t(message.from_user.id, "catbox_link", title=info['title'], artist=info['artist'], mapper=info['mapper'], link=link))
        else:
            message.reply_document(
                file_path,
                caption=t(message.from_user.id, "file_ready", title=info['title'], artist=info['artist'], mapper=info['mapper'])
            )

        os.remove(file_path)

    except Exception as e:
        message.reply_text(t(message.from_user.id, "error", error=str(e)))


app.run()

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS  # 允許外部設備存取
import requests
import re
import random
import os

app = Flask(__name__, template_folder="templates")  # 指定 HTML 存放位置
CORS(app)  # 允許外部設備存取 API

# API Keys
WORDNIK_API_KEY = "5a1d59fba2c80d6e9a20b0c83da02b0a4c862a9668479c8f2"

# API URLs
WORDNIK_EXAMPLE_API = "https://api.wordnik.com/v4/word.json/{}/examples?api_key={}"
WORDNIK_DEFINITIONS_API = "https://api.wordnik.com/v4/word.json/{}/definitions?limit=5&api_key={}"
WORDNIK_SIMILAR_API = "https://api.wordnik.com/v4/word.json/{}/relatedWords?useCanonical=false&relationshipTypes=synonym&limitPerRelationshipType=5&api_key={}"
MYMEMORY_API = "https://api.mymemory.translated.net/get"

# 書籤 & 歷史紀錄
history = []
bookmarks = {}

def get_wordnik_examples(word):
    """ 使用 Wordnik API 獲取例句，並過濾不自然的例句 """
    url = WORDNIK_EXAMPLE_API.format(word, WORDNIK_API_KEY)
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        examples = [item["text"] for item in data.get("examples", [])]

        # 過濾技術性例句並去除重複
        filtered_examples = list(set([
            s for s in examples if len(s) < 150 and not re.search(r'[@\\\/]', s)
        ]))

        return filtered_examples[:5] if filtered_examples else ["未找到適合的例句"]
    
    return ["未找到例句"]

def get_wordnik_definitions(word):
    """ 使用 Wordnik API 獲取詞性與意思，並翻譯成中文 """
    url = WORDNIK_DEFINITIONS_API.format(word, WORDNIK_API_KEY)
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        definitions = {}
        for item in data:
            part_of_speech = item.get("partOfSpeech", "未知詞性")
            definition = item.get("text", "無定義")

            # 翻譯定義成中文
            translated_definition = mymemory_translate(definition)

            if part_of_speech not in definitions:
                definitions[part_of_speech] = []
            definitions[part_of_speech].append(f"{definition}（{translated_definition}）")

        return definitions
    return {}


def get_wordnik_synonyms(word):
    """ 使用 Wordnik API 獲取相似單字 """
    url = WORDNIK_SIMILAR_API.format(word, WORDNIK_API_KEY)
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data and len(data) > 0:
            return data[0]["words"][:5]
    return ["未找到相似單字"]

def mymemory_translate(text, target_lang="zh-TW"):
    """ 使用 MyMemory 免費翻譯 API """
    params = {"q": text, "langpair": f"en|{target_lang}"}
    response = requests.get(MYMEMORY_API, params=params)
    
    if response.status_code == 200:
        return response.json()["responseData"]["translatedText"]
    return "翻譯失敗"

@app.route("/")
def home():
    return render_template("index.html")  # 返回 index.html

@app.route("/translate", methods=["POST"])
def translate():
    data = request.json
    word = data.get("word", "").lower()

    # 記錄歷史紀錄
    if word not in history:
        history.append(word)

    # 取得詞性與定義
    definitions = get_wordnik_definitions(word)

    # 取得 Wordnik 例句
    example_sentences = get_wordnik_examples(word)

    # 翻譯例句
    translated_sentences = [mymemory_translate(sentence) for sentence in example_sentences]

    # 取得相似單字
    similar_words = get_wordnik_synonyms(word)

    return jsonify({
        "word": word,
        "definitions": definitions,
        "example_sentences": example_sentences,
        "translated_sentences": translated_sentences,
        "similar_words": similar_words
    })

@app.route("/bookmark", methods=["POST"])
def add_bookmark():
    """ 新增單字到書籤（包含詞性與意思） """
    data = request.json
    word = data.get("word", "").lower()

    if word not in bookmarks:
        definitions = get_wordnik_definitions(word)  # 獲取詞性與意思
        bookmarks[word] = definitions

    return jsonify({"message": f"{word} 已加入書籤"})

@app.route("/bookmarks")
def bookmarks_page():
    """ 書籤頁面 """
    return render_template("bookmarks.html", bookmarks=bookmarks)

@app.route("/quiz", methods=["GET"])
def start_quiz():
    """ 開始測驗（隨機從書籤中挑選單字） """
    if not bookmarks:
        return jsonify({"quiz_word": "沒有書籤可測驗"})

    quiz_word = random.choice(list(bookmarks.keys()))
    return jsonify({"quiz_word": quiz_word})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
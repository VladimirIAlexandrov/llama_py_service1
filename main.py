
import re

from bson import ObjectId
from flask import Flask, request, jsonify
from llama_cpp import Llama
from conversation import Conversation
import uuid
from pprint import pprint
from flask_cors import CORS
from pymongo import MongoClient

from googletrans import Translator
app = Flask(__name__)
CORS(app)
from googletrans import Translator
client = MongoClient("mongodb://localhost:27017/")
db = client["llamaChat"]  # Имя базы данных
messages_collection = db["messages"]  # Коллекция для сообщений
ratings_collection = db["ratings"]  # Коллекция для оценок
translator = Translator()
@app.route('/chat', methods=['POST'])
def handle_messages():
    print(request)
    data = request.json
    contentUser = data.get("content")
    conv_id = data.get("conversation_id")
    message = data.get("message")

    #message["content"] = custom_translate(message["content"], 'ru', 'en')

    over = data.get("over")


    if not conv_id:
        conv = Conversation()
        conv_id = conv.id
        conversations[conv_id] = conv
    else:
        conv_id = uuid.UUID(conv_id)



    if conv_id not in conversations:
        return jsonify({"status": "error", "hint": f"There is no conversation with particular conversation_id = {conv_id}."})

    if over:
        del conversations[conv_id]
        return jsonify({"status": "ok"})



    if not message:
        return jsonify({"status": "error",
                        "hint": "Message is absent in request.",
                        "conversation_id": conv_id,
                        })

    conversations[conv_id].add_message(message)

    messages = conversations[conv_id].get_messages()
    res = llm.create_chat_completion(messages)["choices"][0]["message"]
    conversations[conv_id].add_message(res.copy())

    res["conversation_id"] = conv_id
    res["status"] = "ok"


    dataS = jsonify(res).json

    conv_idS = dataS.get("conversation_id")


    res["pair_id"] = str(ObjectId())
    message_document = {
        "_id": res["pair_id"],
        "conversation_id": conv_idS,
        "user": message,
        "assistant": res["content"],
    }

    res["content"] = custom_translate(res["content"])

    messages_collection.insert_one(message_document)
    pprint(messages)

    return jsonify(res)

@app.route('/rate', methods=['POST'])
def rate_message():
    data = request.json
    pair_id = data.get("id_pair")
    rating = data.get("rating")
    username = data.get("username")  # Получаем имя пользователя отдельно
    print(f"Pair ID: {pair_id}, Rating: {rating}, Username: {username}")

    if pair_id and rating:
        try:
            object_id = ObjectId(pair_id)
        except:
            return jsonify({"status": "error", "message": "Invalid pair ID format"})

        ratings_collection.insert_one({
            "pair_id": pair_id,
            "rating": rating,
            "username": username,  # Сохраняем имя пользователя отдельно
        })
        return jsonify({"status": "ok"})
    else:
        return jsonify({"status": "error", "message": "Pair ID and a rating are required"})


@app.route('/conversations', methods=['GET'])
def get_conversations():
    pipeline = [
        {"$sort": {"_id": 1}},  # Сортировка документов по _id, что также отражает порядок создания
        {"$group": {
            "_id": "$conversation_id",
            "first_message": {"$first": "$user.content"},  # Используем первое сообщение из поля content объекта user
            "first_message_timestamp": {"$first": "$_id"}  # Используем _id для получения временной метки создания
        }},
        {"$project": {
            "conversation_id": "$_id",
            "first_message": 1,
            "timestamp": "$first_message_timestamp"
        }},
        {"$sort": {"timestamp": -1}}  # Сортировка результатов по временной метке в обратном порядке
    ]
    results = messages_collection.aggregate(pipeline)
    # Преобразование результатов в список словарей
    conversations = [{
        "conversation_id": str(result['_id']),
        "first_message": result['first_message'],
        "timestamp": result['timestamp']
    } for result in results]
    return jsonify(conversations)

@app.route('/messages/<conversation_id>', methods=['GET'])
def get_messages_by_conversation(conversation_id):
    messages = messages_collection.find(
        {"conversation_id": conversation_id},
    ).sort("_id", 1)  # Сортировка по _id для сохранения порядка сообщений

    # Преобразование документов MongoDB в список для JSON-ответа
    messages_list = []
    for message in messages:
        # Добавляем сообщение пользователя, если оно есть
        if "user" in message and "content" in message["user"]:
            user_message = {
                "role": "user",
                "content": message["user"]["content"],
                "type": "user_message"  # Дополнительное поле для идентификации типа сообщения
            }
            messages_list.append(user_message)

        # Добавляем сообщение ассистента, если оно есть
        if "assistant" in message:
            assistant_message = {
                "role": "assistant",
                "content": custom_translate(message["assistant"]),
                "pair_id": message["_id"],
                "type": "assistant_message"  # Дополнительное поле для идентификации типа сообщения
            }
            messages_list.append(assistant_message)


    return jsonify(messages_list)


def custom_translate(text, src='en', dest='ru'):
    translator = Translator()

    # Разбиваем текст на фрагменты по тройным апострофам
    parts = re.split(r'(```.*?```)', text, flags=re.DOTALL)
    translated_parts = []

    for part in parts:
        # Проверяем, является ли часть блоком кода
        if part.startswith('```') and part.endswith('```'):
            # Добавляем блок кода без изменений
            translated_parts.append(part)
        else:
            # Переводим текст
            translated_text = translator.translate(part, src=src, dest=dest).text
            translated_parts.append(translated_text)

    # Собираем переведенный текст обратно
    return '\n'.join(translated_parts)
if __name__ == '__main__':
    model_path = 'C:\\webmodel\\llama-2-7b-chat.Q3_K_M.gguf'

    llm = Llama(model_path=model_path)

    conversations = {}

    app.run(debug=True, host='0.0.0.0', threaded=True)



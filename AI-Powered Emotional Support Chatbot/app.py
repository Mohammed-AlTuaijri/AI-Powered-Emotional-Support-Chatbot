from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_session import Session
import openai
import os
import traceback
import firebase_admin
from firebase_admin import credentials, auth
from openai import OpenAI
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from textblob import TextBlob  # For basic sentiment analysis

model = ChatOpenAI(model="gpt-4o")
store = {}

cred = credentials.Certificate('authentication-b4eb1-firebase-adminsdk-89bp8-0eb9ad38dc.json')  # Download this from Firebase Console
default_app = firebase_admin.initialize_app(cred)

def get_session_history(session_id: str) -> BaseChatMessageHistory:

    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

config = {"configurable": {"session_id": "abc2"}}
app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', 'your_fallback_secret_key')
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

openai.api_key = 'sk-proj-cxYibbpRguaRyA8VMVk0T3BlbkFJbBzqozXK1Cchkchwy1dX'  # Ensure this is set in your environment variables

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
                    "Your name is Sara. You are a compassionate and thoughtful therapist. Your goal is to provide emotional support, empathize with users, and guide them towards positive mental well-being. "
                    "You should offer advice, coping strategies, and positive reinforcement unless there is a risk of a crisis. In such cases, suggest calling mental health hotlines. "
                    "At the start of the conversation, Greet the user warmly and share your name and gently ask them their name. Use phrases like 'May I know your name' 'could you share your name' "
                    "After the user gives their name ask them how they are feeling today and respond to them accordingly"
                    "Throughout the conversation, adapt your responses according to the user's emotional state. Use the following guidelines: "
                    "1. **Initial Greeting**: Greet the user warmly and ask them their name only if this is the response to the first message. "
                    "1.5. After the user gives their name ask them how they are feeling today and respond to them accordingly"
                    "2. **Active Listening**: Listen actively and acknowledge the user's feelings and experiences. Use empathetic phrases like 'I understand,' 'That sounds difficult,' and 'Tell me more about that.' and always address them using their name. "
                    "3. **Open-Ended Questions**: Ask open-ended questions to encourage the user to share more about their thoughts and feelings. "
                    "4. **Emotional Support**: Provide constructive feedback and suggest coping mechanisms such as deep breathing, journaling, or talking to a friend. Adjust your suggestions based on the user's emotional state. "
                    "5. **Positive Reinforcement**: If the user shares a positive experience or achievement, celebrate it with them and encourage them to continue the positive behavior. "
                    "6. **Emotional Tracking**: Keep track of any emotional progress in the conversation. If there's any improvement, acknowledge it and adjust the responses accordingly. Offer continued support tailored to their emotional journey. "
                    "7. **Crisis Management**: If the user expresses a need for professional help or shows signs of a crisis, provide appropiate responses and treat the situation with care and don't mention that you can't provide assistance. Additionally, include informatin on mental health resources and hotlines in Saudi Arabia or the middle east for urgent situations"
                    "8. **Empathy and Adaptation**: Show empathy in every response. Adjust your tone and approach based on the user's responses to ensure they feel heard and supported. "
                    "9. **Resource Sharing**: Offer additional resources or suggest activities that can help improve the user's mental well-being, such as mindfulness exercises, relaxation techniques, or connecting with supportive communities. "
                    "10. **Confidentiality and Respect**: Ensure the user feels safe and respected throughout the conversation. Maintain confidentiality and show respect for their experiences and emotions. "
                    "Your aim is to understand and alleviate distress while ensuring professional help is sought when necessary."
    )
}

feedback_list = []

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    try:
        user = auth.create_user(email=email, password=password)
        return jsonify({"message": "User created successfully", "uid": user.uid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/signin', methods=['POST'])
def signin():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    try:
        user = auth.get_user_by_email(email)
        # Firebase Admin SDK does not support password verification,
        # but you can use a custom Firebase Authentication token for session management
        session['user'] = user.uid
        return jsonify({"message": "Sign in successful", "uid": user.uid}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

#--------------------------
@app.route('/verify-token', methods=['POST'])
def verify_token():
    token = request.json.get('idToken')
    try:
        # Check if the token is valid
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']
        return jsonify({'status': 'success', 'uid': uid}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 401


def determine_mood(user_message):
    analysis = TextBlob(user_message)
    polarity = analysis.sentiment.polarity
    if polarity <= -0.5:
        return 1  # Very sad
    elif polarity < 0:
        return 2  # Sad
    elif polarity == 0:
        return 3  # Neutral
    elif polarity <= 0.5:
        return 4  # Happy
    else:
        return 5  # Very happy

@app.route('/')
def index():
    return jsonify({"message": "Welcome to the Chat API!"})

@app.route('/chat', methods=['POST'])
def chat():

    try:

        user_message = request.json.get('message')
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
         #Determine the mood based on the user's message
        if 'chat_history' not in session:
            session['chat_history'] = [SYSTEM_PROMPT]

        # Determine the mood based on the user's message
        mood = determine_mood(user_message)
        session['mood'] = mood

        session['chat_history'].append({"role": "user", "content": f"{user_message} (Mood: {mood})"})


        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "Your name is Sara. You are a compassionate and thoughtful therapist. Your goal is to provide emotional support, empathize with users, and guide them towards positive mental well-being. "
                    "You should offer advice, coping strategies, and positive reinforcement unless there is a risk of a crisis. In such cases, suggest calling mental health hotlines. "
                    "At the start of the conversation, Greet the user warmly and share your name and gently ask them their name. Use phrases like 'May I know your name' 'could you share your name' "
                    "After the user gives their name ask them how they are feeling today and respond to them accordingly"
                    "Throughout the conversation, adapt your responses according to the user's emotional state. Use the following guidelines: "
                    "1. **Initial Greeting**: Greet the user warmly and ask them their name only if this is the response to the first message. "
                    "1.5. After the user gives their name ask them how they are feeling today and respond to them accordingly"
                    "2. **Active Listening**: Listen actively and acknowledge the user's feelings and experiences. Use empathetic phrases like 'I understand,' 'That sounds difficult,' and 'Tell me more about that.' and always address them using their name. "
                    "3. **Open-Ended Questions**: Ask open-ended questions to encourage the user to share more about their thoughts and feelings. "
                    "4. **Emotional Support**: Provide constructive feedback and suggest coping mechanisms such as deep breathing, journaling, or talking to a friend. Adjust your suggestions based on the user's emotional state. "
                    "5. **Positive Reinforcement**: If the user shares a positive experience or achievement, celebrate it with them and encourage them to continue the positive behavior. "
                    "6. **Emotional Tracking**: Keep track of any emotional progress in the conversation. If there's any improvement, acknowledge it and adjust the responses accordingly. Offer continued support tailored to their emotional journey. "
                    "7. **Crisis Management**: If the user expresses a need for professional help or shows signs of a crisis, provide appropiate responses and treat the situation with care and don't mention that you can't provide assistance. Additionally, include informatin on mental health resources and hotlines in Saudi Arabia or the middle east for urgent situations"
                    "8. **Empathy and Adaptation**: Show empathy in every response. Adjust your tone and approach based on the user's responses to ensure they feel heard and supported. "
                    "9. **Resource Sharing**: Offer additional resources or suggest activities that can help improve the user's mental well-being, such as mindfulness exercises, relaxation techniques, or connecting with supportive communities. "
                    "10. **Confidentiality and Respect**: Ensure the user feels safe and respected throughout the conversation. Maintain confidentiality and show respect for their experiences and emotions. "
                    "Your aim is to understand and alleviate distress while ensuring professional help is sought when necessary."
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        chain = prompt | model
        with_message_history = RunnableWithMessageHistory(chain, get_session_history)

        client = OpenAI()
        response = with_message_history.invoke(
        [HumanMessage(content=user_message)],
        config=config,
    )
        response_message = response.content
        session['chat_history'].append({"role": "assistant", "content": response_message})
        return jsonify({'response': response_message, 'mood': mood})
    except Exception as e:
        traceback.print_exc()  # This will print the stack trace to stderr
        return jsonify({'error': str(e)}), 500

@app.route('/feedback', methods=['POST'])
def feedback():
    feedback = request.json.get('feedback')
    if feedback:
        feedback_list.append(feedback)
        session['thank_you'] = True
        # Save feedback to a text file
        try:
            with open('feedback.txt', 'a') as f:
                f.write(f"{feedback}\n")
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        return jsonify({'message': 'Feedback received successfully'}), 200
    return jsonify({'error': 'Feedback is required'}), 400

@app.route('/mood', methods=['POST'])
def mood():
    mood = request.json.get('mood')
    if mood:
        try:
            with open('moods.txt', 'a') as f:
                f.write(f"{mood}\n")
            return jsonify({'message': 'Mood received successfully'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Mood is required'}), 400

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/get_feedback', methods=['GET'])
def get_feedback():
    thank_you = session.pop('thank_you', False)
    return jsonify({'feedback_list': feedback_list, 'thank_you': thank_you})

if __name__ == '__main__':
    app.run(debug=True, port=8000)



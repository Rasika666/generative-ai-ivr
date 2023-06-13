from flask import Flask, request, jsonify
import openai
import re
import json
import subprocess
import logging
# Create an instance of the Flask class
app = Flask(__name__)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

openai.api_key = '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'
conversation = [
    {'role': 'system',
     'content': 'Act as Spark hotel reception. When User say start conversation. you can great with mention hotel name. '
                'and ask how you can help.'},
    {'role': 'system',
     'content': 'If user want to reserve a table for lunch or dinner. Your task is to fill below example json using '
                'users input. {"name":"shehan","date":"06-03","meal":"lunch","people_count":4}'
                ' You can ask questions from user to '
                'fill all the parameters of json.But You have to ask question one by one from user. wait for user '
                'response before next question. After you get all details you can start your response as "RECIVE_API" '
                'and then'
                'response filled json.Please add the keyword "RECIVE_API" to your response.When you are returning the '
                'json please add the "RECIVE_API" keyword also'},
    {'role': 'system',
     'content': 'Please act as this is year 2023 and format the date based on that'},
    {'role': 'system',
     'content': 'After you get all details you can response as "RECIVE_API" and the json.'},
    {'role': 'system',
     'content': 'If you ready to act as  reception reply as yes.'},
]

conversation2 = [
    {'role': 'system',
     'content': 'Analyze the below-given information and generate and fill the JSON request sample only with the '
                'necessary data that matches the given sample JSON parameters'}
]

conversation3 = [
    {'role': 'system',
     'content': 'Generate a human understandable sentence based on the provided JSON. Please '
                'reply only with the'
                'generated sentence. Do not return the json any other explanation.just generate a human '
                'understandable sentence  based on the response JSON'}
]

app_list_check_api_URL = "http://127.0.0.1:8083/api/booking"
app_list_check_sample_request = {
    "name": "",
    "date": "",
    "meal": "",
    "number_of_people": 0
}


# Define a route and the corresponding function to handle the request
@app.route('/', methods=['GET', 'POST'])
def generate_user_response():
    if request.method == 'POST':

        # Get the JSON data from the request
        json_data = request.get_json()

        # Check if the 'user' key exists in the JSON data
        if 'message' in json_data:
            user_question = json_data['message']
            print("****************************")
            print(user_question)
            conversation.append({'role': 'user', 'content': user_question})

            response = generate_chat_response(conversation)
            reply = response[0]
            json_string = response[1]
            conversation.append({'role': 'assistant', 'content': reply})
            serialized_conversation = [{'role': conv['role'], 'content': conv['content']} for conv in conversation]

            if "RECIVE_API" in reply or json_string is not None and len(json_string) > 0:
                conversation_for_request_generate = generate_conversation_for_request_generate(conversation2,
                                                                                               conversation)
                conversation_for_request_generate.append(
                    {'role': 'user', 'content': f'''"sample json - {app_list_check_sample_request}"'''})

                response_request = generate_request(conversation_for_request_generate)

                if json_validation(app_list_check_sample_request, response_request):

                    human_readable_json = external_api_call(response_request, app_list_check_api_URL)

                    conversation3.append({'role': 'user', 'content': f'JSON RESPONSE {human_readable_json}'})
                    # last_system_entry = next(
                    #     conv['content'] for conv in reversed(conversation) if conv['role'] == 'user')
                    #conversation3.append({'role': 'user', 'content': f'Question I want to reserve a table'})
                    final_response = generate_chat_response(conversation3)

                    return jsonify({'message': final_response[0]})
                else:
                    return jsonify({'error': "Not all parameters in JSON 1 are not null in JSON 2."})
            else:
                return jsonify({'message': reply})
        else:
            return jsonify({'error': 'Invalid JSON data'})


def generate_chat_response(conversation):
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=conversation
    )
    reply = response.choices[0].message['content']
    json_start = reply.find("{")
    json_end = reply.find("}") + 1
    json_string = reply[json_start:json_end]
    print(reply)
    print("****************************")

    return [reply, json_string]


def generate_request(prompt):
    print(prompt)
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=prompt
    )
    reply = response.choices[0].message['content']
    json_start = reply.find("{")
    json_end = reply.find("}") + 1
    json_string = reply[json_start:json_end]
    print(reply)
    return json.loads(json_string)


def generate_conversation_for_request_generate(param1, param2):
    return param1 + [message for message in param2 if message['role'] == 'user']


def external_api_call(response_request, url):
    json_payload = json.dumps(response_request)
    curl_command = f'curl --request POST "{url}" --header "Content-Type: application/json" --data \'{json_payload}\''
    response = subprocess.run(curl_command, capture_output=True, text=True, shell=True)
    response_data = json.loads(response.stdout)
    human_readable_json = json.dumps(response_data, indent=2)
    return human_readable_json


def json_validation(json1, json2):
    data1 = json.loads(json.dumps(json1))
    data2 = json.loads(json.dumps(json2))
    all_not_null = True
    for key, value in data1.items():
        if value == "":
            if data2[key] == "":
                all_not_null = False
                break
    return all_not_null


if __name__ == '__main__':
    app.run()

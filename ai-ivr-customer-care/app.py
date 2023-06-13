from flask import Flask, request, jsonify
import openai
import re
import json
import subprocess

# Create an instance of the Flask class
app = Flask(__name__)

openai.api_key = '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'

trans = [
    {'role': 'system', 'content': 'your task is to translate the given text to Bengali and response only with the '
                                  'translation'
                                  'and no explanation needed.Reply only in bengali.'}
]
conversation = [
    {'role': 'system',
     'content': 'Act as Robi'
                'Customer care support. When User say start conversation. you can ask This is robi customer care how '
                'you can'
                'help.User will normally ask for "I want to know apps subscribed for my number." to do this you have '
                'to trigger api named APP_LIST_API which have number/msisdn parameter. if it missing ask for '
                'number/msisdn. Now say'
                'wait to customer and must response as "APP_LIST_API,<number>".'},
    {'role': 'system', 'content': 'If the user asks anything else, you can respond with "IGNORED".'},
    {'role': 'system',
     'content': 'If user ask "I want to unsubscribed from <app_name>" ,you can response as "APP_UNREG_API,'
                '<number>".Then response as waiting.'},
    {'role': 'system', 'content': 'If you are ready to act as Robi customer care support, please reply with "Yes".'}
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
                'understandable sentence based on the details of response JSON'}
]

app_list_check_api_URL = "http://127.0.0.1:8083/api/applist"
app_list_check_sample_request = {
    "msisdn": ""
}

unsubscribed_api_URL = "http://127.0.0.1:8083/api/unreg"
unsubscribed_api_URL_sample_request = {
    "app_name": "",
    "msisdn": ""
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
            #translatedValue = translate_to_english(trans, user_question)
            conversation.append({'role': 'user', 'content': user_question})

            response = generate_chat_response(conversation)
            conversation.append({'role': 'assistant', 'content': response})
            serialized_conversation = [{'role': conv['role'], 'content': conv['content']} for conv in conversation]

            if "APP_LIST_API" in response:
                conversation_for_request_generate = generate_conversation_for_request_generate(conversation2,
                                                                                               conversation)
                conversation_for_request_generate.append(
                    {'role': 'user', 'content': f'''"sample json - {app_list_check_sample_request}"'''})

                response_request = generate_request(conversation_for_request_generate)

                if json_validation(app_list_check_sample_request, response_request):

                    human_readable_json = external_api_call(response_request, app_list_check_api_URL)

                    conversation3.append({'role': 'user', 'content': f'JSON RESPONSE {human_readable_json}'})
                    # last_system_entry = next(
                    #     conv['content'] for conv in reversed(conversation) if conv['role'] == 'system')
                    # conversation3.append({'role': 'user', 'content': f'Question {last_system_entry}'})
                    final_response = generate_chat_response(conversation3)
                    #banga_reply = translate_to_banga(trans, final_response)
                    print(final_response)
                    print("****************************")
                    return jsonify({'message': final_response})
                else:
                    return jsonify({'message': "Not all parameters in JSON 1 are not null in JSON 2."})
            elif "APP_UNREG_API" in response:
                conversation_for_request_generate = generate_conversation_for_request_generate(conversation2,
                                                                                               conversation)
                conversation_for_request_generate.append(
                    {'role': 'user', 'content': f'''"sample json - {unsubscribed_api_URL_sample_request}"'''})

                response_request = generate_request(conversation_for_request_generate)

                if json_validation(unsubscribed_api_URL_sample_request, response_request):

                    human_readable_json = external_api_call(response_request, unsubscribed_api_URL)

                    conversation3.append({'role': 'user', 'content': f'JSON RESPONSE {human_readable_json}'})
                    last_system_entry = next(
                        conv['content'] for conv in reversed(conversation) if conv['role'] == 'system')
                    conversation3.append({'role': 'user', 'content': f'Question {last_system_entry}'})
                    final_response = generate_chat_response(conversation3)
                    #banga_reply = translate_to_banga(trans, final_response)
                    print(final_response)
                    print("****************************")
                    return jsonify({'message': final_response})
                else:
                    return jsonify({'message': "Request json validation failed"})
            else:
                #banga_reply = translate_to_banga(trans, response)
                print(response)
                print("****************************")
                return jsonify({'message': response})
        else:
            return jsonify({'message': 'Invalid JSON data'})


def generate_chat_response(conversation):
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=conversation
    )
    reply = response.choices[0].message['content']

    return reply


def translate_to_banga(conversation, userMSg):
    temp = conversation
    temp.append({'role': 'user', 'content': userMSg})
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=conversation
    )
    reply = response.choices[0].message['content']
    # print(reply)
    # print("****************************")
    return reply


def generate_request(prompt):
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=prompt
    )
    reply = response.choices[0].message['content']
    json_start = reply.find("{")
    json_end = reply.find("}") + 1
    json_string = reply[json_start:json_end]
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

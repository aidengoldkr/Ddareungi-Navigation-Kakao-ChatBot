from flask import Flask, request, jsonify
import requests
import threading
import time
import random

server = Flask(__name__)

def send_callback_message(start,end,callback_url):
    logic_response = requests.post('main.py api의 주소', json={"start": start,"end": end})
    logic_response_data = logic_response.json()
    print(logic_response_data)
    final_route = logic_response_data['result']
    print(final_route)
    print(type(final_route))
    carousel_list =[]
    if type(final_route) == list:
        for i in range(0,len(final_route),4):
            append_list = []
            for j in range(i,i+4):
                try:
                    append_list.append(final_route[j])
                except:
                    break

            itemcard_list = {
              "header": {
                "title": f"{start} 부터 {end} 까지의 경로"
              },
              "items": append_list
            }

            carousel_list.append(itemcard_list)

        message_json_format = {
            "version": "2.0",
            "template": {
                "outputs": [
                {
                    "carousel": {
                    "type": "listCard",
                    "items": carousel_list
                    }
                }
                ]
            }
        }
    
    else:
        message_json_format = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": final_route
                        }
                    }
                ]
            }
        
        }

    print(message_json_format)
    callback_response = requests.post(callback_url, json= message_json_format)
    print(callback_response.json())
            
@server.route('/message', methods=['POST'])
def send_message():
    skill_payload = request.json
    user_message = skill_payload["userRequest"]["utterance"]
    callback_url = skill_payload["userRequest"]["callbackUrl"]


    try:
        start = user_message.split(',')[0].strip()
        end = user_message.split(',')[1].strip()
        threading.Thread(target=send_callback_message, args=(start, end, callback_url)).start()

        wait_message = {
            "version": "2.0",
            "useCallback": True,
            "data": {
                "text": f"경로를 생성하고 있습니다 (약 {random.randint(7,10)}초 소요)"
            }
        }
        return jsonify(wait_message), 200
    
    except:
        error_message = {
            "version": "2.0",
            "useCallback": True,
            "data": {
                "text": "출발지,도착지 형태로 입력해주세요 (콤마 , 필수)"
            }
        }

        return jsonify(error_message), 200
    
    
if __name__ == "__main__":
    server.run(port=5000)
import os
import random
import uuid
import webbrowser
import pyperclip
import requests
import json
import time
import sys

# https://github.com/thonny/thonny/blob/master/thonny/plugins/github_copilot.py
CLIENT_ID = "Iv1.b507a08c87ecfe98"

BASE_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "editor-version": "Neovim/0.9.2",
    "editor-plugin-version": "copilot.lua/1.11.4",
    "User-Agent": "GithubCopilot/1.133.0",
}

ACCESS_TOKEN_SECRET_KEY = os.path.expanduser('~') + "/.github_copilot_access_token"

token = None
session_id = str(uuid.uuid4()) + str(round(time.time() * 1000))
machine_id = "".join([random.choice("0123456789abcdef") for _ in range(65)])

def setup():
    resp = requests.post(
        'https://github.com/login/device/code', 
        headers=BASE_HEADERS, 
        json={
            "client_id": CLIENT_ID, 
            "scope": "read:user"
        }
    )
    # Parse the response json, isolating the device_code, user_code, and verification_uri
    resp_json = resp.json()
    device_code = resp_json.get('device_code')
    user_code = resp_json.get('user_code')
    verification_uri = resp_json.get('verification_uri')

    # Print the user code and verification uri
    print(f'User code {user_code} has been copied to clipboard, please paste it into {verification_uri} to authenticate.')
    
    pyperclip.copy(user_code)
    webbrowser.open(verification_uri)
    
    while True:
        time.sleep(5)
        resp = requests.post(
            'https://github.com/login/oauth/access_token', 
            headers=BASE_HEADERS, 
            json={
                "client_id": CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            }
        )

        # Parse the response json, isolating the access_token
        resp_json = resp.json()
        access_token = resp_json.get('access_token')

        if access_token:
            break

    # Save the access token to a file
    with open(ACCESS_TOKEN_SECRET_KEY, 'w') as f:
        f.write(access_token)

    print('Authentication success!')

def get_token():
    global token
        # Check if the .copilot_token file exists
    while True:
        try:
            with open(ACCESS_TOKEN_SECRET_KEY, 'r') as f:
                access_token = f.read()
                break
        except FileNotFoundError:
            setup()
    # Get a session with the access token
    resp = requests.get(
        'https://api.github.com/copilot_internal/v2/token', 
        headers=BASE_HEADERS | {
            'authorization': f'token {access_token}',
        }
    )

    # Parse the response json, isolating the token
    resp_json = resp.json()
    token = resp_json.get('token')


def token_thread():
    global token
    while True:
        get_token()
        time.sleep(25 * 60)

def get_api_headers():
    return {
        "authorization": f"Bearer {token}",
        "x-request-id": str(uuid.uuid4()),
        "vscode-sessionid": session_id,
        "machineid": machine_id,
        "editor-version": "vscode/1.85.1",
        "editor-plugin-version": "copilot-chat/0.12.2023120701",
        "openai-organization": "github-copilot",
        "openai-intent": "conversation-panel",
        "content-type": "application/json",
        "user-agent": "GitHubCopilotChat/0.12.2023120701",
    }
def systemContent():
    return "\n".join([
        "You are a world-class Apple code reviewer.",
        "Keep your answers short and impersonal.",
        "Use Markdown formatting in your answers.",
        "Make sure to include the programming language name at the start of the Markdown code blocks.",
        "Avoid wrapping the whole response in triple backticks.",
        "You can only give one reply for each conversation turn.",
        "Minimize any other prose.",
        "The user is fed the results of the git diff", 
        "The user only asks you to identify the code that potentially causes the program to crash.",
        "The user will make sure the files are compiled and verified",
        "You don't care about compilation problems.",
        "You don't care about format problems.",
        "You don't care about syntax error.",
        "The first line of the diff is its timestamps.",
        "When outputting results, you should keep the original full diff content.",
        "Then add a comment $comment directly at the end of the line that could cause a crash in the following format: <potential crash> $comment </potential crash>",
        "Make sure you have replaced $comment with your comment.",
        "Make sure you are commenting in the same line as the code that is likely to cause the crash.",
    ])

def copilot(prompt):
    global token
    # If the token is None, get a new one
    if token is None or is_token_invalid(token):
        get_token()
    try:
        resp = requests.post(
            'https://api.githubcopilot.com/chat/completions', 
            headers=get_api_headers(), 
            json= {
                "messages": [
                    {
                        "role": "system",
                        "content": systemContent()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "intent": True,
                "n": 1,
                "stream": False,
                "temperature": 0.1,
                "model": "gpt-4o", # gpt-4o, gpt-3.5-turbo https://github.com/zed-industries/zed/blob/main/crates/copilot/src/copilot_chat.rs
                "top_p": 1,
                "max_tokens": 128000,
            }
        )
    except requests.exceptions.ConnectionError:
        print("Connection error")
        return ''
    
    messages_by_code = {
        401: "Unauthorized. Make sure you have access to Copilot Chat.",
        500: "Internal server error. Try again later.",
        400: "Your prompt has been rejected by Copilot Chat.",
        419: "You have been rate limited. Try again later.",
    }
    if resp.status_code != 200:
        message = messages_by_code[resp.status_code]
        if message != None:
            print("resp", message)
        else:
            print("resp", resp)

    json_completion = json.loads(resp.text)
    return json_completion.get('choices')[0].get('message').get('content')

# Check if the token is invalid through the exp field
def is_token_invalid(token):
    if token is None or 'exp' not in token or extract_exp_value(token) <= time.time():
        return True
    return False

def extract_exp_value(token):
    pairs = token.split(';')
    for pair in pairs:
        key, value = pair.split('=')
        if key.strip() == 'exp':
            return int(value.strip())
    return None

def printWithColor(text):
    # ANSI escape codes for colors
    RED = '\033[91m'
    RESET = '\033[0m'

    # Replace <potential crash> </potential crash> with red color
    start_tag = '<potential crash>'
    end_tag = '</potential crash>'
    
    while start_tag in text and end_tag in text:
        start_index = text.index(start_tag)
        end_index = text.index(end_tag) + len(end_tag)
        colored_text = RED + text[start_index + len(start_tag):text.index(end_tag)] + RESET
        text = text[:start_index] + colored_text + text[end_index:]

    print(text)

def main():
    # Get the port to listen on from the command line
    if len(sys.argv) < 2:
        print('Usage: python api.py diff')
        exit(1)
    else:
        prompt = sys.argv[1]

    # Get the completion from the copilot function
    completion = copilot(prompt)
    printWithColor(completion)

if __name__ == '__main__':
    main()
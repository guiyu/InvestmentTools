import json
import os


def save_token(token_file, token):
    with open(token_file, 'w') as f:
        json.dump({'token': token}, f)


def load_token(token_file):
    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            data = json.load(f)
            return data.get('token')
    return None
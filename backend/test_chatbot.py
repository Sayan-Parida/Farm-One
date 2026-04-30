from ml.farmbot_chat import get_chat_response

if __name__ == '__main__':
    print('Testing FarmBot...')
    resp = get_chat_response('Can I grow wheat here?')
    print('Response:')
    print(resp)

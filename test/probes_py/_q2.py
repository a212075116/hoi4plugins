import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
print(json.dumps(send({'op':'ping'}), ensure_ascii=False))

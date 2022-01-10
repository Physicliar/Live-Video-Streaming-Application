import json
mes = {"name": "Oyku", "dict":{"x":"y", "z":"t"}}
encoded = json.dumps(mes)
decoded = json.loads(encoded)
print(decoded["dict"]["z"])
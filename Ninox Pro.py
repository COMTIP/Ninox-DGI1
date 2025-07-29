import requests

TEAM_ID = "6dA5DFvfDTxCQxpDF"
DB_ID = "yoq1qy9euurq"
TABLE_ID = "d3c82d50-60d4-11f0-9dd2-0154422825e5"
API_KEY = "TU_API_KEY"

url = f"https://api.ninoxdb.de/v1/teams/{TEAM_ID}/databases/{DB_ID}/tables/{TABLE_ID}/records"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    print("Conexión exitosa ✅")
    print(response.json())  # Para ver los datos
else:
    print(f"Error {response.status_code}: {response.text}")




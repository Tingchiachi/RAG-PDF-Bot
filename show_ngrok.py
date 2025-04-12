# show_ngrok.py
import time
import requests

time.sleep(3)

try:
    tunnels = requests.get("http://ngrok:4040/api/tunnels").json()["tunnels"]
    for tunnel in tunnels:
        if tunnel["proto"] == "https":
            public_url = tunnel["public_url"]
            config = tunnel["config"]
            local_addr = config.get("addr", "http://localhost:5000")

            print(f"Ngrok Public URL (for LINE Webhook): {public_url}/callback")
            print(f"Ngrok UI    → http://localhost:4040")

except Exception as e:
    print("無法取得 ngrok URL:", e)
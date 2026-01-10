import time
import requests
import random
import sys
import json
import threading

BASE_URL = "http://mutupipe.westus2.cloudapp.azure.com:3000/api/"
PROXY_FILE = "proxies.txt"

# ================= PROXY ================= #

def save_proxies_to_file(proxies, count, filename='proxies.txt'):
    try:
        with open(filename, 'w') as file:
            for proxy in proxies:
                if proxy:
                    file.write(f"{proxy}\n")
        print(f"Successfully saved {count} proxies to {filename}.")
    except Exception as e:
        print(f"Error: {e}")

def savepr(time_out=20):
    api_url = f"https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&anonymity=all&timeout={time_out}&proxy_format=protocolipport&format=text"
    pr = requests.get(api_url).text.split("\n")
    save_proxies_to_file(pr, len(pr))

def read_proxies():
    with open(PROXY_FILE, "r") as f:
        return [p.strip() for p in f if p.strip()]

def verify_proxy_alive(proxy, retries=1, delay=5):
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(
                BASE_URL + "version-check",
                proxies=proxy,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if "result" in data:
                    print(f"Proxy alive (attempt {attempt})")
                    return True
        except Exception as e:
            print(f"Proxy check failed (attempt {attempt}): {e}")

        if attempt < retries:
            time.sleep(delay)

    return False

def pick_working_proxy(fetch_new_if_empty=True):
    """
    Pick a working proxy from proxies.txt
    If all fail or file is empty, optionally fetch new list
    """
    proxies = read_proxies()
    random.shuffle(proxies)

    for proxy_string in proxies:
        proto, _ = proxy_string.split("://", 1)
        proxy = {proto + ":": proxy_string}

        print("Checking proxy:", proxy_string)
        time.sleep(4)  # brief pause before check
        if verify_proxy_alive(proxy):
            print("Using proxy:", proxy_string)
            return proxy, proxy_string

    if fetch_new_if_empty:
        print("No alive proxies found. Fetching new proxy list...")
        savepr()
        time.sleep(3)
        return pick_working_proxy(fetch_new_if_empty=False)

    raise RuntimeError("No alive proxies available even after fetching new list")

# ================= API HELPERS ================= #

def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return {"_raw": resp.text}

def api_get(endpoint, headers=None, proxy=None, timeout=15):
    r = requests.get(
        BASE_URL + endpoint,
        headers=headers or {},
        proxies=proxy,
        timeout=timeout,
    )
    return safe_json(r)

def api_post(endpoint, headers=None, data=None, proxy=None, timeout=15):
    r = requests.post(
        BASE_URL + endpoint,
        headers=headers or {},
        data=data,
        proxies=proxy,
        timeout=timeout,
    )
    return safe_json(r)

def api_put(endpoint, headers=None, data=None, proxy=None, timeout=15):
    r = requests.put(
        BASE_URL + endpoint,
        headers=headers or {},
        data=data,
        proxies=proxy,
        timeout=timeout,
    )
    return safe_json(r)

# ================= TOKEN CHECK ================= #

def is_token_invalid(resp):
    return isinstance(resp, dict) and resp.get("retCode") == 4 and resp.get("retMessage") == "Token Invalid"

# ================= AUTH ================= #

def sign_in(password, proxy, retries=5):
    for attempt in range(1, retries + 1):
        try:
            print(f"Signing in... attempt {attempt}/{retries}")

            ver = api_get("version-check", proxy=proxy)
            if "result" not in ver:
                raise RuntimeError(f"version-check blocked: {ver}")

            version = ver["result"]["version_android"]
            time.sleep(2)
            headers = {
                "token": password,
                "versionCode": str(version),
            }

            resp = api_post("signIn", headers=headers, proxy=proxy)

            if is_token_invalid(resp):
                print(f"SIGN-IN BLOCKED RESPONSE (Token Invalid), retrying after 3s...")
                time.sleep(3)
                continue

            if "result" not in resp:
                print("SIGN-IN BLOCKED RESPONSE:", resp)
                print("Backing off for 10 minutes...")
                time.sleep(10 * 60)
                continue

            return resp["result"]["token"]

        except Exception as e:
            print(f"Sign-in error: {e}")
            time.sleep(5)

    raise RuntimeError("SIGNIN_FAILED")

# ================= WORKLOAD ================= #

def get_coin(token, proxy):
    resp = api_get("member", headers={"token": token}, proxy=proxy)
    if "result" not in resp:
        raise RuntimeError(f"member failed: {resp}")
    return resp["result"]["coin"]

def get_video(token, proxy):
    resp = api_get("video", headers={"token": token}, proxy=proxy)
    if is_token_invalid(resp):
        raise RuntimeError("TOKEN_INVALID")
    if "result" not in resp:
        raise RuntimeError(f"video fetch blocked: {resp}")
    return resp["result"]["videoId"], resp["result"]["playSecond"]

def claim_reward(token, video_id, proxy):
    payload = json.dumps({
        "id": video_id,
        "playCount": 0,
        "playSecond": 0,
        "boost": 0,
        "status": ""
    })

    resp = api_put(
        "video",
        headers={
            "token": token,
            "Content-Type": "application/json; charset=UTF-8"
        },
        data=payload,
        proxy=proxy
    )

    if is_token_invalid(resp):
        raise RuntimeError("TOKEN_INVALID")

    if "result" not in resp:
        raise RuntimeError(f"reward blocked: {resp}")

    return resp["result"]["coin"]

# ================= MAIN LOOP ================= #

def run(password):
    proxy, proxy_str = pick_working_proxy()
    print("Session proxy:", proxy_str)

    token = None
    while token is None:
        token = sign_in(password, proxy)
        time.sleep(5)
    
    print("Token acquired successfully")

    coin = get_coin(token, proxy)
    print("Starting coin balance:", coin)

    total_earned = 0
    error_count = 0

    while True:
        try:
            video_id, watch_time = get_video(token, proxy)
            print("Watching for", watch_time, "seconds")
            time.sleep(watch_time + 1)

            new_coin = claim_reward(token, video_id, proxy)
            earned = new_coin - coin
            coin = new_coin
            total_earned += earned

            print("Earned:", earned, "| Total:", total_earned)
            error_count = 0

        except RuntimeError as e:
            if str(e) == "TOKEN_INVALID":
                print("Token invalid, re-signing in...")
                token = None
                while token is None:
                    token = sign_in(password, proxy)
                print("New token acquired, resuming...")
                continue

            error_count += 1
            print("Workload error:", e)

            if error_count >= 4:
                print("Too many errors. Rotating proxy and cooling down 30 minutes...")
                proxy, proxy_str = pick_working_proxy()
                print("New session proxy:", proxy_str)
                token = None
                error_count = 0
                time.sleep(3 * 60)
            else:
                time.sleep(120)


# ================= THREAD WORKER ================= #

def run_with_password(password):
    """Worker function to run a single password session"""
    try:
        run(password)  # your existing run() function
    except Exception as e:
        print(f"[ERROR] {password}: {e}")

# ================= MULTI-THREAD ENTRY ================= #

def run_all_passwords(password_list):
    threads = []

    for pw in password_list:
        t = threading.Thread(target=run_with_password, args=(pw,))
        t.start()
        threads.append(t)
        time.sleep(random.randint(10,20))  # small stagger to avoid API spike

    for t in threads:
        t.join()

# ================= MAIN ================= #

if __name__ == "__main__":
    # List of passwords
    password_list = [
    '9ad14420a63411ee8dec29e7b2d7d8ec', 'b0115460a63411ee8dec29e7b2d7d8ec',
    'cf203a10a63411ee8dec29e7b2d7d8ec', 'b0521f80a4d711ee8dec29e7b2d7d8ec',
    'f9ea0dc0a63411ee8dec29e7b2d7d8ec', '21f550d0a53c11ee8dec29e7b2d7d8ec',
    '3ac6da30a93711ee8dec29e7b2d7d8ec', '37ec0070afbc11eeb6ec9f4e674dc15b',
    '2709d2d0b4f011eeb6ec9f4e674dc15b', 'a00c4220b4f111eeb6ec9f4e674dc15b', 
    '7f60c8a0b4df11eeb6ec9f4e674dc15b', 'ed23c840b4f011eeb6ec9f4e674dc15b',
    '51470170b4f111eeb6ec9f4e674dc15b', 'ac15ba4047f811ed9bb601573df1ee27',
    '429235c0d1ca11eca19befd8b74558ba', 'f3161e40a63311ee8dec29e7b2d7d8ec',
    '397a7fb0d1e811eca462957b5204fdf1', '36894cf0e54411f091a1d35742e4bdca',
]

    if not password_list:
        print("ERROR: Provide at least one password")
        sys.exit(1)

    run_all_passwords(password_list)
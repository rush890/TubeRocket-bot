import time
import requests
import random
import json
import sys
import uuid
from multiprocessing import Process, Manager
import logging
from logging.handlers import RotatingFileHandler

LOG_FILE = "runtime.log"

logger = logging.getLogger("tube")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=2 * 1024 * 1024,   # 2MB
    backupCount=2
)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)

handler.setFormatter(formatter)
logger.addHandler(handler)

# ================= CONFIG ================= #
BASE_URL = "http://mutupipe.westus2.cloudapp.azure.com:3000/api/"
PROXY_FILE = "proxies.txt"
DEVICE_FILE = "devices.json"
TOKEN_FILE = "tokens.json"

DEVICE_MODELS = [
    "OPPO CPH1859",
    "Redmi Note 9",
    "SM-A505F",
    "Vivo Y20",
    "Realme RMX2020"
]

# ================= UTILS ================= #

def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return {"_raw": resp.text}

# ================= PROXY ================= #

def read_proxies():
    try:
        with open(PROXY_FILE, "r") as f:
            return [p.strip() for p in f if p.strip()]
    except:
        return []

def verify_proxy_alive(proxy, retries=2, delay=5):
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(BASE_URL + "version-check", proxies=proxy, timeout=10)
            if resp.status_code == 200 and "result" in resp.json():
                logger.info(f"[Proxy alive] {proxy} (attempt {attempt})")
                return True
        except Exception as e:
            logger.info(f"[Proxy failed] {proxy} (attempt {attempt}): {e}")
        if attempt < retries:
            time.sleep(delay)
    return False

def pick_working_proxy():
    proxies = read_proxies()
    random.shuffle(proxies)
    for proxy_string in proxies:
        proto, _ = proxy_string.split("://", 1)
        proxy = {proto + ":": proxy_string}
        if verify_proxy_alive(proxy):
            return proxy, proxy_string
    raise RuntimeError("No alive proxies found")

# ================= DEVICE ================= #

def random_device_profile():
    return {
        "android": str(random.choice([28, 29, 30])),
        "device": random.choice(DEVICE_MODELS),
        "locale": "IN",
        "deviceToken": str(uuid.uuid4()) + ":APA91b" + uuid.uuid4().hex,
        "sensors": {
            "accelerometer": {"values": [round(random.uniform(-1,1),3),
                                          round(random.uniform(5,10),3),
                                          round(random.uniform(7,10),3)]},
            "gyroscope": {"values": [round(random.uniform(-0.05,0.05),5),
                                      round(random.uniform(-0.05,0.05),5),
                                      round(random.uniform(-0.05,0.05),5)]},
            "light": {"values": [random.randint(0,10)]},
            "proximity": {"values": [5.0]}
        }
    }

def load_devices():
    try:
        with open(DEVICE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_devices(devices):
    with open(DEVICE_FILE, "w") as f:
        json.dump(devices, f, indent=2)

def get_device_for_password(password):
    devices = load_devices()
    if password not in devices:
        devices[password] = random_device_profile()
        save_devices(devices)
        logger.info(f"[New device] created for password {password}")
    return devices[password]

# ================= TOKEN CACHE ================= #

def load_tokens():
    try:
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_tokens(tokens):
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

def get_token_for_password(password, proxy):
    tokens = load_tokens()
    token = tokens.get(password)

    # Check if token exists and is still valid
    if token:
        try:
            resp = requests.get(BASE_URL + "member", headers={"token": token}, proxies=proxy, timeout=10)
            data = safe_json(resp)
            if "result" in data:
                return token
            else:
                logger.info(f"[Token expired] for {password}")
        except:
            logger.info(f"[Token check failed] for {password}")

    # Sign in to get new token
    new_token = sign_in(password, proxy)
    if new_token:
        tokens[password] = new_token
        save_tokens(tokens)
    return new_token

# ================= API ================= #

def api_get(endpoint, headers=None, proxy=None, timeout=15):
    r = requests.get(BASE_URL + endpoint, headers=headers or {}, proxies=proxy, timeout=timeout)
    return safe_json(r)

def api_post(endpoint, headers=None, data=None, proxy=None, timeout=15):
    r = requests.post(BASE_URL + endpoint, headers=headers or {}, data=data, proxies=proxy, timeout=timeout)
    return safe_json(r)

def api_put(endpoint, headers=None, data=None, proxy=None, timeout=15):
    r = requests.put(BASE_URL + endpoint, headers=headers or {}, data=data, proxies=proxy, timeout=timeout)
    return safe_json(r)

# ================= AUTH ================= #

# ================= AUTH ================= #

def sign_in(password, proxy):
    device = get_device_for_password(password)

    # version-check should already be proxy-verified, but still validate once
    ver = api_get("version-check", proxy=proxy)
    if "result" not in ver:
        logger.info(f"[version-check blocked]: {ver}")
        return None

    headers = {
        "token": password,
        "versionCode": str(ver["result"]["version_android"]),
        "android": device["android"],
        "device": device["device"],
        "locale": device["locale"],
        "deviceToken": device["deviceToken"],
        "sensors": json.dumps(device["sensors"]),
        "User-Agent": "okhttp/3.12.0"
    }

    # ---- retry with SAME proxy ----
    for attempt in range(1, 4):
        try:
            logger.info(f"[SIGN-IN] Attempt {attempt}/3")

            resp = requests.post(
                BASE_URL + "signIn",
                headers=headers,
                data="",                 # mobile app sends empty body
                proxies=proxy,
                timeout=15
            )

            data = safe_json(resp)

            if "result" in data:
                logger.info("[Sign-in success]")
                return data["result"]["token"]

            # explicit token invalid / blocked
            logger.info(f"[SIGN-IN FAILED] attempt {attempt}: {data}")

        except Exception as e:
            logger.info(f"[SIGN-IN ERROR] attempt {attempt}: {e}")

        # wait before next attempt
        if attempt < 3:
            time.sleep(5)

    # ---- permanently blocked after 3 tries ----
    logger.info("[SIGN-IN BLOCKED] Marking account as blocked after 3 failed attempts")
    return None

# ================= WORKLOAD ================= #

def get_coin(token, proxy):
    resp = api_get("member", headers={"token": token}, proxy=proxy)
    if "result" not in resp:
        raise RuntimeError(f"member failed: {resp}")
    return resp["result"]["coin"]

def get_video(token, proxy):
    resp = api_get("video", headers={"token": token}, proxy=proxy)
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
    resp = api_put("video", headers={"token": token,"Content-Type":"application/json; charset=UTF-8"},
                   data=payload, proxy=proxy)
    if "result" not in resp:
        raise RuntimeError(f"reward blocked: {resp}")
    return resp["result"]["coin"]

# ================= MAIN WORKER ================= #

def run(password):
    proxy, proxy_str = pick_working_proxy()
    logger.info(f"[Session proxy] {proxy_str}")

    token = get_token_for_password(password, proxy)
    if not token:
        logger.info(f"[Failed] Cannot get token for {password}")
        return

    coin = get_coin(token, proxy)
    logger.info(f"[Starting coin] {coin}")

    total_earned = 0
    error_count = 0

    while True:
        try:
            video_id, watch_time = get_video(token, proxy)
            logger.info(f"[Watching] {watch_time}s")
            time.sleep(watch_time + 1)

            new_coin = claim_reward(token, video_id, proxy)
            earned = new_coin - coin
            coin = new_coin
            total_earned += earned
            logger.info(f"[Earned] {earned} | Total: {total_earned}")
            error_count = 0

        except Exception as e:
            logger.info(f"[Error] {e}")
            error_count += 1
            if error_count >= 3:
                logger.info("[Cooling down 30 min due to repeated errors]")
                time.sleep(20*60)
                error_count = 0
            else:
                time.sleep(120)

# ================= MULTI-PASSWORD ================= #

def run_all(password_list):
    jobs = []
    for pwd in password_list:
        p = Process(target=run, args=(pwd,))
        p.start()
        jobs.append(p)
        time.sleep(random.randint(10,20))

    for j in jobs:
        j.join()

# ================= ENTRY ================= #

if __name__ == "__main__":
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
        logger.info("ERROR: Provide at least one password")
        sys.exit(1)

    run_all(password_list)
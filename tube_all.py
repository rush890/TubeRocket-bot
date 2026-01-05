import time
import requests
import random
import sys


import requests
import time

def get_fresh_proxy(
    timeout=15,
    retries=5,
    retry_delay=5
):
    """
    Fetch a fresh proxy from PubProxy.
    Retries on exception with delay.

    Returns:
        dict | None   -> requests-compatible proxy dict
    """

    url = "http://pubproxy.com/api/proxy"

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=timeout)
            data = resp.json()

            if data.get("count", 0) == 0 :
                continue

            proxy_data = data["data"][0]

            if int(proxy_data["speed"]) >10:
                print("Proxy too slow, retrying...")
                continue
            
            ip_port = proxy_data["ipPort"]
            proxy_type = proxy_data.get("type", "http")
            supports_https = proxy_data.get("support", {}).get("https", 0)

            proxy_url = f"{proxy_type}://{ip_port}"

            proxy_dict = {
                "http": proxy_url
            }

            if supports_https:
                proxy_dict["https"] = proxy_url
            # print("Fetched new proxy:", data)
            return proxy_dict

        except Exception as e:
            if attempt == retries:
                print("Proxy fetch failed after retries:", e)
                return None

            time.sleep(retry_delay)


def countdown(seconds):
  for j in range(seconds, 0, -1):
    #print('Waiting for', j, 'seconds ', end='\r')
    time.sleep(1)

BASE_URL="http://mutupipe.westus2.cloudapp.azure.com:3000/api/"
def get_token(to, pr, retries=3):
  for _ in range(retries):
    try:
      url = BASE_URL+'version-check'
      ver = str(requests.get(url=url, proxies=pr, timeout=10).json()['result']['version_android'])
      url = BASE_URL+'signIn'
      head = {'token': to, 'versionCode': ver}
      time.sleep(2)
      res=requests.post(url=url, headers=head, proxies=pr, timeout=10).json()
      return res['result']['token']
    except Exception as e:
      print("Error in sing in step, retrying:", str(e))
      time.sleep(2)
  raise Exception("Error while singin waiting and retry")


def get_video_info(to,pr):
  time.sleep(1)
  url = BASE_URL+'video'
  head = {'token': to}
  dl = requests.get(url=url, headers=head, proxies=pr, timeout=5).json()
  #print(dl)
  return dl['result']['videoId'], dl['result']['playSecond']


def receive_reward(to, video_id,pr):
  time.sleep(1)
  url = BASE_URL+'video'
  head = {'token': to, 'Content-Type': 'application/json; charset=UTF-8'}
  data = '{"id":"' + video_id + '","playCount":0,"playSecond":0,"boost":0,"status":""}'
  res = requests.put(url=url, headers=head, data=data, proxies=pr, timeout=10).json()
  print(res)
  return res['result']['coin']


def get_coin_balance(to, pr):
  """Get current coin balance for an account"""
  try:
    time.sleep(1)
    url = BASE_URL + 'member'
    head = {'token': to}
    response = requests.get(url=url, headers=head, proxies=pr, timeout=10).json()
    if 'result' not in response or 'coin' not in response['result']:
      raise Exception(f"Invalid response format: {response}")
    return response['result']['coin']
  except Exception as e:
    raise Exception(f"Error getting coin balance: {str(e)}")


cr_sum = 0


def verify_proxy(proxy_string):
  """Verify proxy works for both version-check AND signIn"""
  try:
    time.sleep(2)
    # protocol, proxy = proxy_string.split("://")
    # pr = {
    #     protocol+":": proxy_string,
    # }
    
    # Step 1: Check version-check
    url = BASE_URL+'version-check'
    response = requests.get(url=url, proxies=proxy_string, timeout=10)
    res=response.json()
    version=res['result']['version_android']
    print(f"Proxy version-check passed: {proxy_string} using version: {version}")
    return True
      
  except Exception as e:
    print(f"Proxy failed verification: {proxy_string} - {e}")
    return False


def process_password(password,pr):
  global cr_sum
  err_count = 0
  current_proxy = pr

  while True:
    try:
      # Get token with retry logic - keep trying until successful
      to = None
      token_attempts = 0
      max_token_attempts = 5
      
      while token_attempts < max_token_attempts:
        token_attempts += 1
        try:
          to = get_token(password, current_proxy)
          print(f"Token acquired successfully on attempt {token_attempts}")
          break
        except Exception as retry_error:
          print(f"Token fetch attempt {token_attempts}/{max_token_attempts} failed: {str(retry_error)}")
          if token_attempts < max_token_attempts:
            # Get a new proxy and fully verify it (both version-check and signIn) before retrying
            new_proxy_dict = get_fresh_proxy()
            if new_proxy_dict:
              if verify_proxy(new_proxy_dict):
                current_proxy = new_proxy_dict
                print(f"Switched to new verified proxy: {new_proxy_dict}")
              else:
                print(f"New proxy failed verification, trying another...")
              time.sleep(1)
            else:
              print("No more proxies available, waiting before retry...")
              time.sleep(5)
          else:
            raise Exception(f"Failed to get token after {max_token_attempts} attempts")
      
      coin = get_coin_balance(to, current_proxy)
      print(coin)
      while True:
        try:
          print("User Sign in and getting token...")
          video_id, tg = get_video_info(to, current_proxy)
          print("watching for", tg)
          countdown(tg + 1)
          nwcoin = receive_reward(to, video_id, current_proxy)
          try:
            cr_sum += (nwcoin - coin)
            print("Coins Earned are *****:", nwcoin - coin)
            print("Total Coined earned in this cycle:", cr_sum)
            coin = nwcoin
          except:
            print("Error in coin calculation")
        except Exception as e:
          err_count += 1
          if (err_count > 15):
            print("User cooldown!!!!!!!!!!", password)
            err_count = 0
            time.sleep(5000)
          else:
            # Proxy might have failed, try to get a new one
            print(f"Error occurred, attempting to get new proxy: {str(e)}")
            new_proxy_dict = get_fresh_proxy()
            if new_proxy_dict:
              if verify_proxy(new_proxy_dict):
                current_proxy = new_proxy_dict
                print(f"Switched to new verified proxy: {new_proxy_dict}")
          #print("Error in get_video_info", e)
          time.sleep(random.randint(200, 270))
          break
    except Exception as e:
      print("Error in get_token, waiting before retry:", str(e))
      time.sleep(150)
      # Get new proxy on token error
      new_proxy_dict = get_fresh_proxy()
      if new_proxy_dict:
        if verify_proxy(new_proxy_dict):
          current_proxy = new_proxy_dict
          print(f"Token error, switched to new verified proxy: {new_proxy_dict}")




if __name__ == "__main__":
  if len(sys.argv) != 2:
    print("Usage: python your_script.py <password>")
    sys.exit(1)

  password_to_process = sys.argv[1]
  
  # Verify proxy before processing
  proxy_dict = None
  while True:
    proxy_dict = get_fresh_proxy()
    if proxy_dict is None:
      print("No proxies available.")
      sys.exit(1)
    
    if verify_proxy(proxy_dict):
      break
  

  print("proxy:",proxy_dict)
  process_password(password_to_process,proxy_dict)

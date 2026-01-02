import time
import requests
import random
import sys

from app import savepr


def read_proxies(file_path):
  with open(file_path, 'r') as file:
    proxies = [line.strip() for line in file.readlines()]
  return proxies


def save_proxies(file_path, proxies):
  with open(file_path, 'w') as file:
    for proxy in proxies:
      file.write(proxy + '\n')


def get_random_proxy():
  proxy_file="proxies.txt"
  proxies = read_proxies(proxy_file)

  if not proxies:
    print("No proxies available.")
    return

  # Randomly pick a proxy
  chosen_proxy = random.choice(proxies)

  # Remove the chosen proxy from the list
  proxies.remove(chosen_proxy)
  # Save the updated list of proxies back to the file
  save_proxies(proxy_file, proxies)
  # print(f"Processing with proxy: {chosen_proxy}")
  return chosen_proxy


def countdown(seconds):
  for j in range(seconds, 0, -1):
    #print('Waiting for', j, 'seconds ', end='\r')
    time.sleep(1)

BASE_URL="http://mutupipe.westus2.cloudapp.azure.com:3000/api/"
def get_token(to,pr):
  url = BASE_URL+'version-check'
  ver = str(requests.get(url=url, proxies=pr).json()['result']['version_android'])
  url = BASE_URL+'signIn'
  head = {'token': to, 'versionCode': ver}
  time.sleep(1)
  return requests.post(url=url, headers=head, proxies=pr).json()


def get_video_info(to,pr):
  url = BASE_URL+'video'
  head = {'token': to}
  dl = requests.get(url=url, headers=head, proxies=pr).json()
  #print(dl)
  return dl['result']['videoId'], dl['result']['playSecond']


def receive_reward(to, video_id,pr):
  time.sleep(2)
  url = BASE_URL+'video'
  head = {'token': to, 'Content-Type': 'application/json; charset=UTF-8'}
  data = '{"id":"' + video_id + '","playCount":0,"playSecond":0,"boost":0,"status":""}'
  res = requests.put(url=url, headers=head, data=data, proxies=pr).json()
  print(res)
  return res['result']['coin']


def get_coin_balance(to, pr):
  """Get current coin balance for an account"""
  try:
    url = BASE_URL + 'member'
    head = {'token': to}
    response = requests.get(url=url, headers=head, proxies=pr).json()
    if 'result' not in response or 'coin' not in response['result']:
      raise Exception(f"Invalid response format: {response}")
    return response['result']['coin']
  except Exception as e:
    raise Exception(f"Error getting coin balance: {str(e)}")


cr_sum = 0


def verify_proxy(proxy_string, password):
  """Verify proxy works for both version-check AND signIn"""
  try:
    time.sleep(2)
    protocol, proxy = proxy_string.split("://")
    pr = {
        protocol+":": proxy_string,
    }
    
    # Step 1: Check version-check
    url = BASE_URL+'version-check'
    response = requests.get(url=url, proxies=pr, timeout=10)
    res=response.json()
    version=res['result']['version_android']
    print(f"Proxy version-check passed: {proxy_string}")
    
    # Step 2: Verify signIn also works with this proxy
    time.sleep(1)
    url = BASE_URL+'signIn'
    head = {'token': password, 'versionCode': str(version)}
    sign_in_response = requests.post(url=url, headers=head, proxies=pr, timeout=10)
    sign_in_result = sign_in_response.json()
    
    if 'result' in sign_in_result and 'token' in sign_in_result['result']:
      print(f"Proxy fully verified (both version-check and signIn): {proxy_string}")
      return True
    else:
      print(f"Proxy failed signIn: {proxy_string}")
      return False
      
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
          to = get_token(password, current_proxy)['result']['token']
          print(f"Token acquired successfully on attempt {token_attempts}")
          break
        except Exception as retry_error:
          print(f"Token fetch attempt {token_attempts}/{max_token_attempts} failed: {str(retry_error)}")
          if token_attempts < max_token_attempts:
            # Get a new proxy and fully verify it (both version-check and signIn) before retrying
            new_proxy_string = get_random_proxy()
            if new_proxy_string:
              if verify_proxy(new_proxy_string, password):
                protocol, proxy = new_proxy_string.split("://")
                current_proxy = {protocol+":": new_proxy_string}
                print(f"Switched to new verified proxy: {new_proxy_string}")
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
            new_proxy_string = get_random_proxy()
            if new_proxy_string:
              if verify_proxy(new_proxy_string, password):
                protocol, proxy = new_proxy_string.split("://")
                current_proxy = {protocol+":": new_proxy_string}
                print(f"Switched to new verified proxy: {new_proxy_string}")
          #print("Error in get_video_info", e)
          time.sleep(random.randint(200, 270))
          break
    except Exception as e:
      print("Error in get_token, waiting before retry:", str(e))
      time.sleep(150)
      # Get new proxy on token error
      new_proxy_string = get_random_proxy()
      if new_proxy_string:
        if verify_proxy(new_proxy_string, password):
          protocol, proxy = new_proxy_string.split("://")
          current_proxy = {protocol+":": new_proxy_string}
          print(f"Token error, switched to new verified proxy: {new_proxy_string}")




if __name__ == "__main__":
  if len(sys.argv) != 2:
    print("Usage: python your_script.py <password>")
    sys.exit(1)

  password_to_process = sys.argv[1]
  
  # Verify proxy before processing
  proxy_string = None
  while True:
    proxy_string = get_random_proxy()
    if proxy_string is None:
      print("No proxies available, waiting 2 min and fetching new roxy list...")
      time.sleep(120)
      savepr(40)
      continue
    
    if verify_proxy(proxy_string, password_to_process):
      break
  
  protocol, proxy = proxy_string.split("://")
  pr = {
      protocol+":": proxy_string,
  }
  print("proxy:",pr)
  process_password(password_to_process,pr)

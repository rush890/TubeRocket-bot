import time
import requests
import random
import sys


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
  try:
    ver = str(requests.get(url=url, proxies=pr).json()['result']['version_android'])
  except:
    print("Retry without proxy....")
    ver = str(requests.get(url=url).json()['result']['version_android'])
  
  url = BASE_URL+'signIn'
  head = {'token': to, 'versionCode': ver}
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


cr_sum = 0


def verify_proxy(proxy_string):
  try:
    protocol, proxy = proxy_string.split("://")
    pr = {
        protocol+":": proxy_string,
    }
    url = BASE_URL+'version-check'
    response = requests.get(url=url, proxies=pr, timeout=10)
    response.json()
    print(f"Proxy verified: {proxy_string}")
    return True
  except Exception as e:
    print(f"Proxy failed: {proxy_string} - {e}")
    return False


def process_password(password,pr):
  global cr_sum
  err_count = 0

  while True:
    try:
      to = get_token(password,pr)['result']['token']
      coin = (requests.get(url=BASE_URL+'member',
                           headers={
                               'token': to
                           }, proxies=pr).json()['result']['coin'])
      print(coin)
      while True:
        try:
          video_id, tg = get_video_info(to,pr)
          print("watching for", tg)
          countdown(tg + 1)
          nwcoin = receive_reward(to, video_id,pr)
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
          #print("Error in get_video_info", e)
          time.sleep(random.randint(200, 270))
          break
    except Exception as e:
      print("Error in get_token",e)
      time.sleep(150)




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
      print("No proxies available.")
      sys.exit(1)
    
    if verify_proxy(proxy_string):
      break
  
  protocol, proxy = proxy_string.split("://")
  pr = {
      protocol+":": proxy_string,
  }
  print("proxy:",pr)
  process_password(password_to_process,pr)

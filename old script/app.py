import subprocess, time, requests,random
from replit_keep_alive import keep_alive
keep_alive()

# List of passwords
user_passwords = [
    '9ad14420a63411ee8dec29e7b2d7d8ec', 'b0115460a63411ee8dec29e7b2d7d8ec',
    'cf203a10a63411ee8dec29e7b2d7d8ec', 'b0521f80a4d711ee8dec29e7b2d7d8ec',
    'f9ea0dc0a63411ee8dec29e7b2d7d8ec', '21f550d0a53c11ee8dec29e7b2d7d8ec',
    '3ac6da30a93711ee8dec29e7b2d7d8ec', '37ec0070afbc11eeb6ec9f4e674dc15b',
    '2709d2d0b4f011eeb6ec9f4e674dc15b', 'a00c4220b4f111eeb6ec9f4e674dc15b',
    '7f60c8a0b4df11eeb6ec9f4e674dc15b', 'ed23c840b4f011eeb6ec9f4e674dc15b',
    '51470170b4f111eeb6ec9f4e674dc15b', 'ac15ba4047f811ed9bb601573df1ee27',
    '429235c0d1ca11eca19befd8b74558ba', 'f3161e40a63311ee8dec29e7b2d7d8ec',
    '397a7fb0d1e811eca462957b5204fdf1'
]


def save_proxies_to_file(proxies, count, filename='proxies.txt'):
  try:
    with open(filename, 'w') as file:
      for proxy in proxies:
        if(proxy):
          file.write(f"{proxy}")
          
    print(f"Successfully saved {count} proxies to {filename}.")
  except Exception as e:
    print(f"Error: {e}")


def savepr(time_out=20):
  api_url = f"https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&anonymity=all&timeout={time_out}&proxy_format=protocolipport&format=text"
  prx = []
  pr = requests.get(api_url).text
  pr = pr.split("\n")
  # print("Found proxies", len(pr))
  save_proxies_to_file(pr,len(pr))


def get_random_wait_time():
  return random.uniform(20 * 60, 40 * 60)


print("----------- TubeRocket Automation Started... -----------")
# Run process_password function for each password in a separate process
while True:
  print("Fetching proxies")
  savepr()
  processes = []
  for password in user_passwords:
    command = ['python', 'tube_all.py', password]
    process = subprocess.Popen(command)
    processes.append(process)
    time.sleep(10)

  # Generate a random wait time
  wait_time = get_random_wait_time()

  print(f"Waiting for {wait_time / 60:.2f} minutes before stopping processes.")
  time.sleep(wait_time)

  # Stop all processes
  for process in processes:
    process.terminate()

  print("Processes stopped. Restarting.")

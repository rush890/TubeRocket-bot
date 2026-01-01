import time
import requests
import random
import json
from datetime import datetime

# List of user passwords (from app.py)
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

BASE_URL = "http://mutupipe.westus2.cloudapp.azure.com:3000/api/"
COIN_HISTORY_FILE = "coin_history.json"

# Functions from tube_all.py
def read_proxies(file_path):
    with open(file_path, 'r') as file:
        proxies = [line.strip() for line in file.readlines()]
    return proxies


def get_token(password, proxy_dict):
    """Get token using password and proxy"""
    url = BASE_URL + 'version-check'
    try:
        ver = str(requests.get(url=url, proxies=proxy_dict, timeout=10).json()['result']['version_android'])
    except:
        print("Retry without proxy....")
        ver = str(requests.get(url=url, timeout=10).json()['result']['version_android'])
    
    url = BASE_URL + 'signIn'
    head = {'token': password, 'versionCode': ver}
    return requests.post(url=url, headers=head, proxies=proxy_dict, timeout=10).json()


def get_coins(token, proxy_dict):
    """Get coin balance for an account using token and proxy"""
    url = BASE_URL + 'member'
    head = {'token': token}
    response = requests.get(url=url, headers=head, proxies=proxy_dict, timeout=10).json()
    return response['result']['coin']


def format_proxy(proxy_string):
    """Format proxy string into proxy dictionary"""
    if not proxy_string or "://" not in proxy_string:
        return None
    try:
        protocol, proxy = proxy_string.split("://")
        return {protocol + ":": proxy_string}
    except:
        return None


def verify_proxy(proxy_string):
    """Verify if proxy is working"""
    try:
        protocol, proxy = proxy_string.split("://")
        pr = {
            protocol + ":": proxy_string,
        }
        url = BASE_URL + 'version-check'
        response = requests.get(url=url, proxies=pr, timeout=10)
        response.json()
        print(f"Proxy verified: {proxy_string}")
        return True
    except Exception as e:
        print(f"Proxy failed: {proxy_string} - {e}")
        return False


def load_coin_history():
    """Load previous coin history from JSON file"""
    try:
        with open(COIN_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_coin_history(history):
    """Save coin history to JSON file"""
    try:
        with open(COIN_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        print(f"\n✓ Coin history saved to {COIN_HISTORY_FILE}")
    except Exception as e:
        print(f"Error saving coin history: {e}")


def get_total_coins():
    """Calculate total coins across all accounts"""
    total_coins = 0
    total_earned = 0
    account_coins = {}
    
    # Load previous coin history
    coin_history = load_coin_history()
    
    # Read proxies from file
    try:
        proxies_list = read_proxies('proxies.txt')
        proxies_list = [p for p in proxies_list if p]  # Remove empty lines
    except:
        print("Error: Could not read proxies.txt file")
        return None

    print(f"Found {len(proxies_list)} proxies")
    print(f"Checking {len(user_passwords)} accounts...\n")
    
    for idx, password in enumerate(user_passwords, 1):
        try:
            # Get a random proxy for this account and verify it
            proxy_string = None
            proxy_dict = None
            
            if proxies_list:
                # Try to find a working proxy
                for attempt in range(min(5, len(proxies_list))):
                    proxy_string = random.choice(proxies_list)
                    if verify_proxy(proxy_string):
                        proxy_dict = format_proxy(proxy_string)
                        break
                    proxies_list.remove(proxy_string)
            
            if not proxy_dict:
                print(f"[{idx}/{len(user_passwords)}] No working proxies, using direct connection")
            
            print(f"[{idx}/{len(user_passwords)}] Processing account {idx}...", end=" ")
            
            # Get token using password and proxy
            token_response = get_token(password, proxy_dict)
            token = token_response['result']['token']
            
            # Get coins using token and proxy
            current_coins = get_coins(token, proxy_dict)
            account_id = password[:8]
            
            # Calculate coins earned since last check
            previous_coins = coin_history.get(account_id, {}).get('coins', 0)
            coins_earned = current_coins - previous_coins
            
            account_coins[account_id] = {
                'coins': current_coins,
                'previous_coins': previous_coins,
                'coins_earned': coins_earned,
                'timestamp': datetime.now().isoformat()
            }
            
            total_coins += current_coins
            total_earned += coins_earned
            
            print(f"✓ Current: {current_coins} | Earned: {coins_earned}")
            
        except Exception as e:
            print(f"\n✗ Error: {type(e).__name__}: {str(e)}")
            continue
        
        time.sleep(1)  # Delay between requests
    
    return total_coins, total_earned, account_coins

def save_proxies_to_file(proxies, filename='proxies.txt'):
  try:
    with open(filename, 'w') as file:
      for proxy in proxies:
        if(proxy):
          file.write(f"{proxy}")
    print(f"Proxies saved successfull Xy to {filename}")
  except Exception as e:
    print(f"Error: {e}")

def savepr():
  api_url = "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&anonymity=all&timeout=10&proxy_format=protocolipport&format=text"
  prx = []
  print("starting")
  pr = requests.get(api_url).text
  pr = pr.split("\n")
  print("Found proxies", len(pr))
  save_proxies_to_file(pr)


if __name__ == "__main__":
    print("=" * 60)
    print("TOTAL COINS CHECKER")
    print("=" * 60 + "\n")
    savepr()
    result = get_total_coins()
    
    if result:
        total_coins, total_earned, account_coins = result
        
        # Save current coin data for future comparison
        history_to_save = {}
        for account_id, data in account_coins.items():
            history_to_save[account_id] = {
                'coins': data['coins'],
                'timestamp': data['timestamp']
            }
        save_coin_history(history_to_save)
        
        print("\n" + "-" * 60)
        print("Coins per Account:")
        print("-" * 60)
        for account_id, data in account_coins.items():
            print(f"\n{account_id}...")
            print(f"  Current Balance: {data['coins']}")
            print(f"  Previous Balance: {data['previous_coins']}")
            print(f"  Earned: {data['coins_earned']}")
            print(f"  Last Updated: {data['timestamp']}")
            
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"\nTotal Coins Across All Accounts: {total_coins}")
        print(f"Total Coins Earned (Since Last Check): {total_earned}")
        print(f"Number of Accounts Checked: {len(account_coins)}")
        
    else:
        print("Failed to retrieve coin information")

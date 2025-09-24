import ujson
import request
import utime


def http_get_json(url, timeout):
    
    resp = request.get(url, timeout=timeout)
    if resp is None:
        raise Exception("[HTTP] No response")
        print("no reponse")
    
    
    text = resp.text
    obj=''
    for i in text:
        obj+=i
        utime.sleep_ms(10)
    print("*****")
    print("*****")
    print("*****")   
    try:
        json = ujson.loads(obj)
        return json
    except Exception as e:
        print("[HTTP] Error parsing JSON:", e)
        return None
    return None
def ensure_network(timeout=60):
    print("[NET] Waiting for network ...")
    ck = checkNet.CheckNetwork("BG95_OTA", "1.0")
    stage, sub = ck.wait_network_connected(timeout)
    ok = (stage == 3 and sub == 1)
    print("[NET] stage, sub =", stage, sub, "OK?" , ok)
    return ok
if __name__ == "__main__":
    
    # Connexion réseau
    backoff = 5
    MAX_BACKOFF = 60
    while not ensure_network(60):
        print("[NET] retry in", backoff, "sec")
        utime.sleep(backoff)
        backoff = min(MAX_BACKOFF, backoff * 2)

    # Minimal manual test: set URL below and run this script on the device.
    TEST_URL1 = "https://ota-local-server.onrender.com/update/867123456789012"
    

    manifest1 = http_get_json(TEST_URL1,100)
    print("manifest1 [value]: ",manifest1)
    


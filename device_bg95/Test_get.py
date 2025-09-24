import ujson
import request


def http_get_json(url, timeout=REQUEST_TIMEOUT):
    try:
        resp = request.get(url, timeout=timeout, decode=False)
        if resp is None:
            raise Exception("No response")
            print("no reponse")
        content = resp.content  # maintenant ce sont des bytes
        resp.close()
        return ujson.loads(content)
    except Exception as e:
        print("[HTTP] GET error:", e)
        return None


if __name__ == "__main__":
    # Minimal manual test: set URL below and run this script on the device.
    TEST_URL = "https://ota-local-server.onrender.com/update/867123456789012"

    manifest = http_get_json(TEST_URL)
    if not manifest:
        print("[Error] No manifest / HTTP error")
        
    print("[Success] Manifest:", manifest)

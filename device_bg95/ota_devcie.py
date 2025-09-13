
# QuecPython – Poll OTA endpoint every 6 hours and apply update if available.
import utime, ujson, uos
import checkNet, modem
from misc import Power

# Réseau & téléchargements
import request            # HTTP/HTTPS client (QuecPython)
import fota               # Firmware OTA
import app_fota           # SOTA / user file upgrade

# ---------------------------
# META PROJET (optionnel)
# ---------------------------
PROJECT_NAME = "QuecPython_Fota_example"
PROJECT_VERSION = "1.0.0"

# ---------------------------
# CONFIG
# ---------------------------
UPDATE_BASE_URL = "http://ec7b332f9190.ngrok-free.app/update"     # <-- à adapter
REPORT_URL      = "http://ec7b332f9190.ngrok-free.app/report"     # <-- à adapter (endpoint de statut)
POLL_INTERVAL_SEC = 30                       # 6h
JITTER_SEC = 1                                        # +/- 60s pour désynchroniser
CA_CERT_PATH = "/usr/ca.crt"                           # déployer votre CA ici (PEM)
STATE_PATH = "/usr/ota_state.json"                     # persistance simple
STATUS_PATH = "/usr/ota-status.json"                  # journal d'état

APN = "internet"            # si nécessaire pour FOTA
IP_TYPE = 0                 # 0: IPv4 (selon firmware)
REQUEST_TIMEOUT = 30        # sec HTTP

# ---------------------------
# LOGGING (console + fichier)
# ---------------------------
LOG_PATH = "/usr/ota.log"
LOG_MAX_BYTES = 200 * 1024     # 200 Ko
LOG_BACKUPS = 2                # ota.log.1 et ota.log.2

try:
    import builtins
except:
    builtins = __import__("builtins")
_original_print = builtins.print  # garder l'original

def _fmt_ts(ts=None):
    # ts -> "YYYY-MM-DD HH:MM:SS"
    try:
        if ts is None:
            ts = utime.time()
        y, m, d, hh, mm, ss, _, _ = utime.localtime(ts)
        return "%04d-%02d-%02d %02d:%02d:%02d" % (y, m, d, hh, mm, ss)
    except:
        return str(ts or now())

def _file_size(path):
    try:
        st = uos.stat(path)
        # MicroPython stat tuple: (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) selon port
        # Souvent index 6 = size
        return st[6] if len(st) > 6 else 0
    except:
        return 0

def _rotate_logs():
    try:
        # supprimer le plus ancien
        old2 = LOG_PATH + ".%d" % LOG_BACKUPS
        try:
            uos.remove(old2)
        except:
            pass
        # décaler .1 -> .2, etc.
        for i in range(LOG_BACKUPS - 1, 0, -1):
            src = LOG_PATH + ".%d" % i
            dst = LOG_PATH + ".%d" % (i + 1)
            try:
                uos.rename(src, dst)
            except:
                pass
        # fichier courant -> .1
        try:
            uos.rename(LOG_PATH, LOG_PATH + ".1")
        except:
            pass
    except Exception as e:
        _original_print("[LOG] rotate error:", e)

def _append_log_line(line):
    try:
        # rotation si nécessaire
        if _file_size(LOG_PATH) > LOG_MAX_BYTES:
            _rotate_logs()
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")
        return True
    except Exception as e:
        # on n'empêche jamais la console d'afficher
        _original_print("[LOG] write error:", e)
        return False

def _tee_print(*args, **kwargs):
    # 1) afficher en console
    _original_print(*args, **kwargs)
    # 2) écrire la même ligne dans le fichier (format horodaté)
    try:
        msg = " ".join([str(a) for a in args])
        ts = _fmt_ts()
        _append_log_line("[%s] %s" % (ts, msg))
    except Exception as e:
        _original_print("[LOG] tee error:", e)

# redirige print vers tee (console + fichier)
builtins.print = _tee_print

print("=== OTA client starting ===", PROJECT_NAME, PROJECT_VERSION)

# ---------------------------
# UTILS FICHIERS
# ---------------------------
def read_text(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except:
        return None

def write_text(path, s):
    try:
        with open(path, "w") as f:
            f.write(s)
        return True
    except Exception as e:
        print("write_text error:", e)
        return False

def load_state():
    s = read_text(STATE_PATH)
    if not s:
        return {}
    try:
        return ujson.loads(s)
    except:
        return {}

def save_state(d):
    try:
        write_text(STATE_PATH, ujson.dumps(d))
    except Exception as e:
        print("save_state error:", e)

def now():
    return utime.time()

def sleep_with_jitter(base_sec, jitter_sec):
    # évite que tous les devices frappent en même temps
    jitter = (utime.ticks_ms() % (2 * jitter_sec)) - jitter_sec
    dur = base_sec + jitter
    if dur < 10:
        dur = 10
    print("Sleep", dur, "sec")
    utime.sleep(dur)

# ---------------------------
# STATUT OTA (LOCAL + SERVEUR)
# ---------------------------
def save_status_local(payload):
    """Enregistre le dernier statut OTA dans /usr/ota-status.json (overwrite)."""
    try:
        payload["_ts"] = now()
        ok = write_text(STATUS_PATH, ujson.dumps(payload))
        print("[STATUS] saved:", ok, payload)
    except Exception as e:
        print("[STATUS] save error:", e)

def send_status_server(payload, ca_pem=None):
    """Envoie le statut OTA au serveur (HTTP POST)."""
    try:
        headers = {"Content-Type": "application/json"}
        data = ujson.dumps(payload)
        if ca_pem:
            resp = request.post(REPORT_URL, data=data, headers=headers, timeout=REQUEST_TIMEOUT, ca=ca_pem)
        else:
            resp = request.post(REPORT_URL, data=data, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp:
            _ = resp.text
            resp.close()
        print("[STATUS] reported to server")
        return True
    except Exception as e:
        print("[STATUS] report error:", e)
        return False

def record_and_report(status, detail=None, update_type=None, version=None, extra=None):
    """Crée un statut standardisé, l'écrit localement et le poste au serveur."""
    payload = {
        "imei": modem.getDevImei(),
        "project": PROJECT_NAME,
        "project_version": PROJECT_VERSION,
        "status": status,        # 'no_update' | 'fota_start' | 'fota_ok' | 'fota_fail' | 'sota_start' | 'sota_ok' | 'sota_fail' | ...
        "detail": detail,
        "type": update_type,     # 'fota' | 'sota' | None
        "target_version": version,
    }
    if extra and isinstance(extra, dict):
        payload.update(extra)

    save_status_local(payload)
    ca_pem = read_text(CA_CERT_PATH)
    send_status_server(payload, ca_pem)

# ---------------------------
# NETWORK BOOTSTRAP
# ---------------------------
def ensure_network(timeout=60):
    print("[NET] Waiting for network ...")
    ck = checkNet.CheckNetwork("BG95_OTA", "1.0")
    stage, sub = ck.wait_network_connected(timeout)
    ok = (stage == 3 and sub == 1)
    print("[NET] stage, sub =", stage, sub, "OK?" , ok)
    return ok

# ---------------------------
# HTTP GET (update manifest)
# ---------------------------
def http_get_json(url, ca_pem=None, timeout=REQUEST_TIMEOUT):
    try:
        if ca_pem:
            resp = request.get(url, timeout=timeout, ca=ca_pem)
        else:
            resp = request.get(url, timeout=timeout)
        if resp is None:
            raise Exception("No response")
        text = resp.text
        resp.close()
        return ujson.loads(text)
    except Exception as e:
        print("[HTTP] GET error:", e)
        return None

# ---------------------------
# APPLY UPDATES
# ---------------------------
def do_fota(fw_url, target_version=None):
    print("[FOTA] Start:", fw_url)
    record_and_report("fota_start", detail="download begin", update_type="fota", version=target_version)
    try:
        fo = fota.fota()
        # Config APN si nécessaire
        try:
            fo.apn_set(fota_apn=APN, ip_type=IP_TYPE)
        except Exception as e:
            print("[FOTA] apn_set warn:", e)

        # Callback de progression -> on enregistre quelques jalons (sans spam réseau)
        def cb(args):
            try:
                status = args[0]
                progress = args[1]
                print("[FOTA] status:", status, "progress:", progress)
                if progress in (0, 25, 50, 75, 100):
                    save_status_local({
                        "imei": modem.getDevImei(),
                        "project": PROJECT_NAME,
                        "project_version": PROJECT_VERSION,
                        "status": "fota_progress",
                        "detail": str(status),
                        "type": "fota",
                        "target_version": target_version,
                        "progress": progress,
                        "_ts": now()
                    })
            except Exception as _:
                pass

        rc = fo.httpDownload(url1=fw_url, callback=cb)
        print("[FOTA] httpDownload rc =", rc)
        if rc == 0:
            record_and_report("fota_ok", detail="download ok; will apply on reboot", update_type="fota", version=target_version)
            return True
        else:
            record_and_report("fota_fail", detail="download rc=%s" % rc, update_type="fota", version=target_version)
            return False
    except Exception as e:
        print("[FOTA] exception:", e)
        record_and_report("fota_fail", detail="exception: %s" % e, update_type="fota", version=target_version)
        return False

def do_sota(file_list, target_version=None):
    # file_list: [{ "url": "...", "file_name": "..."}, ...]
    print("[SOTA] Files:", file_list)
    record_and_report("sota_start", detail="download begin", update_type="sota", version=target_version,
                      extra={"files_count": len(file_list)})
    try:
        af = app_fota.new()
        failures = af.bulk_download(file_list)
        if failures and len(failures) > 0:
            print("[SOTA] failures:", failures)
            record_and_report("sota_fail", detail="download failures", update_type="sota", version=target_version,
                              extra={"failures": failures})
            return False
        # Pose le flag et redémarre pour appliquer l’update
        record_and_report("sota_ok", detail="download ok; set_update_flag & reboot", update_type="sota", version=target_version)
        af.set_update_flag()
        print("[SOTA] set_update_flag OK -> restarting...")
        utime.sleep(2)
        Power.powerRestart()
        return True  # ne revient normalement pas
    except Exception as e:
        print("[SOTA] exception:", e)
        record_and_report("sota_fail", detail="exception: %s" % e, update_type="sota", version=target_version)
        return False

# ---------------------------
# MAIN POLLING LOGIC
# ---------------------------
def poll_once():
    imei = "867123456789012" # modem.getDevImei()
    url = "{}/{}".format(UPDATE_BASE_URL.rstrip("/"), imei)
    print("[POLL] GET", url)

    ca_pem = read_text(CA_CERT_PATH)
    manifest = http_get_json(url, ca_pem)
    if not manifest:
        print("[POLL] No manifest / HTTP error")
        record_and_report("no_manifest", detail="http error or empty", update_type=None)
        return False
    
    print("[POLL] Manifest:", manifest)

    # Anti-boucle: comparer avec dernier "applied_version" ou "last_seen_version"
    st = load_state()
    last_version = st.get("last_version")

    has_update = manifest.get("has_update", False)
    mtype = manifest.get("type", "fota")
    version = manifest.get("version")

    # Si le serveur expose une version et qu'on l'a déjà appliquée, on s'arrête
    if not has_update:
        print("[POLL] No update")
        st["last_check"] = now()
        save_state(st)
        record_and_report("no_update", detail="manifest had no update", update_type=None, version=version)
        return True

    if version and last_version == version:
        print("[POLL] Version already applied:", version)
        st["last_check"] = now()
        save_state(st)
        record_and_report("already_applied", detail="same version", update_type=mtype, version=version)
        return True

    # Exécuter l’update selon le type
    ok = False
    if mtype == "fota":
        fw_url = manifest.get("url")
        if not fw_url:
            print("[POLL] Missing url for FOTA")
            record_and_report("fota_fail", detail="missing url", update_type="fota", version=version)
            return False
        ok = do_fota(fw_url, target_version=version)

    elif mtype == "sota":
        files = manifest.get("files") or []
        if not files:
            print("[POLL] Missing files for SOTA")
            record_and_report("sota_fail", detail="missing files", update_type="sota", version=version)
            return False
        ok = do_sota(files, target_version=version)

    else:
        print("[POLL] Unknown type:", mtype)
        record_and_report("unknown_type", detail=str(mtype), update_type=None, version=version)
        return False

    # Enregistrer l’état si succès (pour ne pas retélécharger en boucle)
    if ok:
        st["last_version"] = version or st.get("last_version")
        st["last_applied_at"] = now()
        save_state(st)
        print("[POLL] Update OK")
    else:
        print("[POLL] Update FAILED")

    return ok

def main():
    # Connexion réseau
    backoff = 5
    MAX_BACKOFF = 60
    while not ensure_network(60):
        print("[NET] retry in", backoff, "sec")
        utime.sleep(backoff)
        backoff = min(MAX_BACKOFF, backoff * 2)

    # Boucle de polling
    while True:
        try:
            poll_once()
        except Exception as e:
            print("[MAIN] exception in poll:", e)
            record_and_report("poll_exception", detail=str(e), update_type=None)

        # Attente 6h +/- jitter
        sleep_with_jitter(POLL_INTERVAL_SEC, JITTER_SEC)

if __name__ == "__main__":
    main()

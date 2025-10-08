import request
import ujson
import uos
import utime
import checkNet

LOG_FILE = "/usr/log.json"
MAX_SIZE = 10 * 1024  # 10 kb
def delete_file():
    try:
        # Récupérer les infos du fichier
        info = uos.stat(LOG_FILE)
        file_size = info[6]  # La taille en octets (index 6)

        print("Taille du fichier :", file_size, "octets")

        # Vérifier si la taille dépasse 4 KB
        if file_size > MAX_SIZE:
            print("⚠️ Taille > 4KB, suppression du fichier...")
            uos.remove(LOG_FILE)
            print("Fichier supprimé avec succès.")
        else:
            print("✅ Taille correcte, pas de suppression.")

    except OSError:
        # Le fichier n’existe pas
        print("Le fichier lg.json n'existe pas encore.")
def log_message(msg):
    delete_file()
    # Créer un log avec temps + message
    t = utime.localtime()
    log_entry = {
        "time": "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            t[0], t[1], t[2], t[3], t[4], t[5]
        ),
        "message": msg
    }
    
    # Ajouter le log en JSON + retour à la ligne
    with open(LOG_FILE, "a") as f:   # "a" = append
        f.write("\n" + ujson.dumps(log_entry))


def send_logs(url=None, delete_after=0):
    DEFAULT_URL = "172.236.29.24:5000/logs/upload"
    delete_file()
    def ensure_network(timeout=100):
       print("[NET] Waiting for network ...")
       ck = checkNet.CheckNetwork("BG95_OTA", "1.0")
       stage, sub = ck.wait_network_connected(timeout)
       ok = (stage == 3 and sub == 1)
       print("[NET] stage, sub =", stage, sub, "OK?" , ok)
       return ok
    
    backoff = 5
    MAX_BACKOFF = 60
    while not ensure_network(60):
        print("[NET] retry in", backoff, "sec")
        utime.sleep(backoff)
        backoff = min(MAX_BACKOFF, backoff * 2)
    
    try:
        # Lire le fichier log.json
        with open(LOG_FILE, "r") as f:
            logs = f.read()

        # Vérifier que ce soit du JSON valide
        
           # Découpage manuel avec split("\n")
        entries = [line.strip() for line in logs.split("\n") if line.strip()]
        
           # Conversion JSON ligne par ligne
        logs_json = [ujson.loads(entry) for entry in entries]
        print(logs_json)
        
        # Déterminer l’URL à utiliser
        final_url = url if url else DEFAULT_URL

        # Envoyer au serveur via POST
        headers = {"Content-Type": "application/json"}
        response = request.post(final_url, headers=headers, data=ujson.dumps(logs_json))

        if response.status_code == 200:
            print("Logs envoyés avec succès ")
            # Supprimer le fichier si delete_after = 1
            if delete_after == 1:
                try:
                    uos.remove(LOG_FILE)
                    print("Fichier log supprimé après envoi ")
                except Exception as e:
                    print("Impossible de supprimer le fichier:", e)
        else:
            print("Erreur lors de l’envoi:", response.status_code, response.text)

        response.close()

    except Exception as e:
        print("Erreur:", e)

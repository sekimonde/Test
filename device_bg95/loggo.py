import sys
import ujson  # ou json si tu es en CPython*
import utime

LOG_FILE = "/usr/log.json"

def log_message(msg):
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
        f.write("\n" + ujson.dumps(log_entry) + "\n")

# Exemple :
log_message("Premier message")
log_message("Deuxième message")

class StdoutCatcher:
    def __init__(self, json_file):
        self.json_file = json_file
        self.messages = []

    def write(self, message):
        # ignorer les lignes vides
        if message.strip():
            self.messages.append(message.strip())
            # enregistrer dans le JSON
            with open(self.json_file, "w") as f:
                ujson.dump(self.messages, f)

    def flush(self):
        pass  # nécessaire pour compatibilité avec sys.stdout

# --- Rediriger stdout vers notre catcher ---
try:
    catcher = StdoutCatcher("/usr/logs.json")
    sys.stdout = catcher
except Exception as e:
    print("Erreur lors de la redirection de stdout:", e)
    log_message("Erreur lors de la redirection de stdout: " + str(e))
# --- Exemple ---
print("Message 1")
utime.sleep(130)
log_message('autre message de log ou d\'erreur')

# Les messages sont capturés dans catcher.messages et sauvegardés dans /usr/logs.json

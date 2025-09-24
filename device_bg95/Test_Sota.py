import app_fota
from misc import Power


fota = app_fota.new()


download_list = [
    {
        "url": "https://ota-local-server.onrender.com/files/app.bin",
        "file_name": "/usr/app.bin"
    },
    {
        "url": "https://developer.quectel.com/en/wp-content/uploads/sites/2/2025/06/Quectel_EC800KEG800K_Series_QuecOpen_Reference_Design_V1.2.pdf",
        "file_name": "/usr/QuecDoc.pdf"
    }
]


result = fota.bulk_download(download_list)

if result is None:
    print(" Téléchargement réussi")
    fota.set_update_flag()
    print(" Re. pour appliquer la mise à jour")
    
else:
    print(" Échec du téléchargement :", result)

# main.py
import utime
import log
import checkNet
import sys
sys.path.append('/usr')
import network
import usocket
# from mqtt import MqttClient
# from umqtt import MQTTClient
import mqtts

# =======================
# إعدادات المشروع
# =======================
PROJECT_NAME = "QuecPython_MQTT_SSL"
PROJECT_VERSION = "1.0.0"



# إعدادات MQTT
MQTT_CLIENT_ID = "kezfzlkkgpeke447"
MQTT_SERVER = "www.devicespeak.com"  # غيّر إلى عنوان الـ MQTT Broker الحقيقي
MQTT_PORT = 8883
MQTT_USER = "DS1"    # أدخل اسم المستخدم الخاص بالـ MQTT
MQTT_PASSWORD = "DS1comtrend7931"  # أدخل كلمة المرور الخاصة بالـ MQTT
#MQTT_TOPIC_SUB = b"DeviceSpeak/quectel"
MQTT_TOPIC_PUB = b"DeviceSpeak/DS2"
MQTT_MESSAGE = b"Hello from QuecPython SSL!"
MQTT_TOPIC_SUB = b"bg95/command"
# مسار شهادة SSL
CA_CERT_PATH = "/usr/cart.pem"
# إعدادات MQTT
# MQTT_CLIENT_ID = "bg95_sota_client"
# MQTT_SERVER = "g116ba30.ala.us-east-1.emqxsl.com"  # غيّر إلى عنوان الـ MQTT Broker الحقيقي
# MQTT_PORT = 8883
# MQTT_USER = "sekki"    # أدخل اسم المستخدم الخاص بالـ MQTT
# MQTT_PASSWORD = "sekisat"  # أدخل كلمة المرور الخاصة بالـ MQTT
# #MQTT_TOPIC_SUB = b"DeviceSpeak/quectel"
# MQTT_TOPIC_PUB = b"DeviceSpeak/DS2"
# MQTT_MESSAGE = b"Hello from QuecPython SSL!"
# MQTT_TOPIC_SUB = b"bg95/command"
# # مسار شهادة SSL
# CA_CERT_PATH = "/usr/ca.pem"
# =======================
# تهيئة اللوجر
# =======================
net_log = log.getLogger("Net")
# mqtt_log = log.getLogger("MQTT")

# =======================
# كائن الشبكة (التحقق من الاتصال)
# =======================
checknet = checkNet.CheckNetwork(PROJECT_NAME, PROJECT_VERSION)



def net_init():
    """تهيئة الشبكة والاتصال بالإنترنت"""
    net_log.info("📡 بدء الاتصال بالشبكة...")

    if not network.setup_apn():
        net_log.error("❌ فشل إعداد APN")
        return False

    if not network.connect_network(timeout=60):
        net_log.error("❌ فشل الاتصال بالشبكة")
        return False

    net_log.info("✅ تم الاتصال بالشبكة بنجاح")

    # اختبار DNS للتأكد من وجود اتصال إنترنت فعلي
    try:
        ip = usocket.getaddrinfo(MQTT_SERVER, MQTT_PORT)
        net_log.info("✅ IP {}: {}".format(MQTT_SERVER, ip))
        if (ip == None):
            return False

    except Exception as e:
        net_log.error("❌ لا يوجد اتصال فعلي بالإنترنت: %s" % e)
        return False

    return True

def mqtt_init():
    """تهيئة MQTT والاتصال بالوسيط"""
    # global mqtt

    utime.sleep(5)  # تأخير بسيط قبل البدء
    checknet.poweron_print_once()
    checknet.wait_network_connected()
    mqtts.mqtt_start(
        clientid=MQTT_CLIENT_ID,
        server=MQTT_SERVER,
        port=MQTT_PORT,
        user=MQTT_USER,
        password=MQTT_PASSWORD,
        keepalive=30,
        ssl=True,
        ca_cert_path=CA_CERT_PATH,
        reconn=False,
        Topic=MQTT_TOPIC_SUB
    )
    mqtts.mqtt_loop_forever()

    # mqtts.publish(MQTT_TOPIC_PUB,MQTT_MESSAGE)


# =======================
# نقطة البداية
# =======================

if __name__ == "__main__":
    if net_init():
        mqtt_init()
    else:
        net_log.error("⚠️ فشل في تهيئة الشبكة. تم إيقاف البرنامج.")

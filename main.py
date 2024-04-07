from machine import ADC, Timer, Pin
import utime
import network
import socket
from time import sleep
from dht import DHT11
import json  # Dieser Import fehlte




# Initialisierung des ADC4 für den Onboard-Temperatursensor
sensor_temp = ADC(4)
conversion_factor = 3.3 / (65535)

def format_datetime_custom(dt):
    year, month, day, hour, minute, second, _, _ = dt
    return "{:04d}/{:02d}/{:02d}-{:02d}:{:02d}:{:02d}".format(year, month, day, hour, minute, second)

# Initialisierung des DHT11-Sensors
dht11_sensor = DHT11(Pin(14, Pin.IN, Pin.PULL_UP))

# Funktion zum Schreiben in eine CSV-Datei
def write_csv(filename, date, onboard_temp, external_temp, humidity):
    with open(filename, 'a') as csvfile:
        csvfile.write(f"{date},{onboard_temp},{external_temp},{humidity}\n")

# Funktion zum Schreiben in eine HTML-Datei
def write_html(filename, onboard_temp, external_temp, humidity):
    with open(filename, 'w') as htmlfile:
        htmlfile.write(f"""<html>
<head>
<title>Temperatur und Luftfeuchtigkeitsanzeige</title>
<style>
body {{
    font-family: 'Arial', sans-serif;
    background-color: #333;
    color: #eee;
    margin: 0;
    padding: 20px;
}}
h1 {{
    color: #ff9800;
}}
table {{
    width: 100%;
    border-collapse: collapse;
}}
th, td {{
    text-align: left;
    padding: 8px;
    border-bottom: 1px solid #ddd;
}}
th {{
    background-color: #555;
    color: #fff;
}}
tr:hover {{background-color: #444;}}
</style>
</head>
<body>
<h1>Aktuelle Messwerte</h1>
<table>
<tr>
    <th>Datum und Uhrzeit</th>
    <td>{format_datetime_custom(utime.localtime())}</td>
</tr>
<tr>
    <th>Onboard Temperatur</th>
    <td>{onboard_temp} °C</td>
</tr>
<tr>
    <th>Externe Temperatur</th>
    <td>{external_temp} °C</td>
</tr>
<tr>
    <th>Luftfeuchtigkeit</th>
    <td>{humidity} %</td>
</tr>
</table>
</body>
</html>""")



# Funktion zum Starten des Servers
def start_server():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print('Server gestartet. Warte auf Verbindung...')
    return s

def send_404(client):
    response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\n404 Not Found"
    client.send(response.encode("utf-8"))
    client.close()

# Funktion zum Empfangen und Verarbeiten von Anfragen
def handle_requests(s):
    while True:
        cl, addr = s.accept()
        print('Client verbunden von', addr)
        request = cl.recv(1024).decode("utf-8")
        request_line = request.split("\r\n")[0]
        method, path, _ = request_line.split(" ")

        if method == "GET":
            if path == "/":
                send_html_page(cl)
            elif path == "/api/sensordata":  # Hinzufügen dieses Pfads
                send_sensor_data(cl)
            else:
                send_404(cl)  # Du musst sicherstellen, dass diese Funktion implementiert ist.
        cl.close()

def send_sensor_data(client):
    data = {
        "onboard_temp": latest_onboard_temp,
        "external_temp": latest_external_temp,
        "humidity": latest_humidity
    }
    response = json.dumps(data)
    client.send(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + response.encode('utf-8'))
    client.close()

# Funktion zum Senden der HTML-Seite
def send_html_page(client):
    # Stelle sicher, dass diese Funktion die zuletzt gemessenen Werte verwendet,
    # die von `read_sensors_and_write_to_csv` aktualisiert wurden.
    # Angenommen, `latest_onboard_temp`, `latest_external_temp` und `latest_humidity`
    # sind die globalen Variablen, die die neuesten Werte speichern.
    
    # HTML-Seite mit den neuesten Messwerten erstellen
    write_html('index.html', latest_onboard_temp, latest_external_temp, latest_humidity)
    
    # Öffnen der index.html Datei und Senden als HTTP-Antwort
    with open('index.html', 'rb') as f:
        response = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + f.read()
        client.send(response)
    client.close()


# Timer für die Temperaturmessung alle 3 Sekunden initialisieren
# Globale Variablen für die zuletzt gemessenen Werte
latest_onboard_temp = None
latest_external_temp = None
latest_humidity = None

def read_sensors_and_write_to_csv(timer):
    global latest_onboard_temp, latest_external_temp, latest_humidity
    # Aktuelle Uhrzeit erfassen
    current_time = utime.localtime()
    date = format_datetime_custom(current_time)
    
    # Onboard-Temperatur-Sensor als Dezimalzahl lesen und umrechnen
    read_onboard = sensor_temp.read_u16()
    voltage = read_onboard * conversion_factor
    onboard_temp = 27 - (voltage - 0.706) / 0.001721
    
    # DHT11-Sensor lesen (mit Fehlerbehandlung, falls notwendig)
    try:
        dht11_sensor.measure()
        external_temp = dht11_sensor.temperature()
        humidity = dht11_sensor.humidity()
    except OSError:
        # Optionale Fehlerbehandlung
        print("Fehler beim Lesen des DHT11-Sensors")
        return
    
    # Aktualisiere globale Variablen mit den neuesten Werten
    latest_onboard_temp = onboard_temp
    latest_external_temp = external_temp
    latest_humidity = humidity
    
    # Printen der Daten in der Ausgabe
    print("Datum: ", date)
    print("Onboard Temperatur (°C): ", onboard_temp)
    print("Externe Temperatur (°C): ", external_temp)
    print("Luftfeuchtigkeit (%): ", humidity)
    
    # Schreibe die Daten in die CSV-Datei und aktualisiere ggf. die HTML-Seite
    write_csv('Temperatur_und_Luftfeuchtigkeit.csv', date, onboard_temp, external_temp, humidity)
    # Die write_html Funktion nicht hier aufrufen, da sie bei Serveranfragen aufgerufen wird

def send_html_page(client):
    # Verwende die globalen Variablen für die Antwort
    if latest_onboard_temp is not None and latest_external_temp is not None and latest_humidity is not None:
        write_html('index.html', latest_onboard_temp, latest_external_temp, latest_humidity)
        # Öffnen der index.html Datei und Senden als HTTP-Antwort
        with open('index.html', 'rb') as f:
            response = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + f.read()
            client.send(response)
    else:
        # Senden einer Fehlermeldung oder einer Warte-Seite, falls keine Daten verfügbar sind
        pass
    client.close()

# Timer für die Messung aller Sensordaten alle 3 Sekunden initialisieren
temperature_timer = Timer(-1)
temperature_timer.init(period=5000, mode=Timer.PERIODIC, callback=read_sensors_and_write_to_csv)

# WLAN-Verbindung herstellen
ssid = "Livebox-D876"
password = "cWukttZUsmr9tHaokP"
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)
max_wait = 10
while max_wait > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    max_wait -= 1
    print('Warten auf Verbindung...')
    sleep(1)

if wlan.status() != 3:
    raise RuntimeError('Netzwerkverbindung fehlgeschlagen')
else:
    print('Verbunden')
    status = wlan.ifconfig()
    print('IP-Adresse:', status[0])

# Starten des Servers und Behandeln von Anfragen
server = start_server()
handle_requests(server)




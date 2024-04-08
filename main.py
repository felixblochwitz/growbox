from machine import ADC, Timer, Pin
import utime
import network
import socket
from time import sleep
import json  # Dieser Import fehlte

# Initialisierung des ADC4 für den Onboard-Temperatursensor
sensor_temp = ADC(4)
conversion_factor = 3.3 / (65535)

def format_datetime_custom(dt):
    year, month, day, hour, minute, second, _, _ = dt
    return "{:04d}/{:02d}/{:02d}-{:02d}:{:02d}:{:02d}".format(year, month, day, hour, minute, second)

def read_csv(filename, n=5):
    with open(filename, 'r') as file:
        lines = []
        for line in file:
            if len(lines) >= n:
                lines.pop(0)
            lines.append(line.strip())
    data = []
    for line in lines:
        date, onboard_temp = line.split(',')[:2]  # Anpassung hier
        data.append({
            "date": date,
            "onboard_temp": float(onboard_temp),
        })
    return data

# Anpassung der Funktion zum Schreiben in eine CSV-Datei
def write_csv(filename, date, onboard_temp):
    with open(filename, 'a') as csvfile:
        csvfile.write(f"{date},{onboard_temp}\n")  # Entfernen von external_temp und humidity

def send_csv_data(client):
    print("here")
    data = read_csv('Temperatur_und_Luftfeuchtigkeit.csv', 5)  # Lese die letzten 5 Zeilen
    response = json.dumps(data)
    client.send(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + response.encode('utf-8'))
    client.close()
        
def send_sensor_data(client):
    data = {
        "onboard_temp": latest_onboard_temp,
        "external_temp": latest_external_temp,
        "humidity": latest_humidity
    }
    response = json.dumps(data)
    client.send(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + response.encode('utf-8'))
    client.close()

# Globale Variablen für die zuletzt gemessenen Werte
latest_onboard_temp = None

def read_sensors_and_write_to_csv(timer):
    global latest_onboard_temp, latest_external_temp, latest_humidity
    # Aktuelle Uhrzeit erfassen
    current_time = utime.localtime()
    date = format_datetime_custom(current_time)
    
    # Onboard-Temperatur-Sensor als Dezimalzahl lesen und umrechnen
    read_onboard = sensor_temp.read_u16()
    voltage = read_onboard * conversion_factor
    onboard_temp = 27 - (voltage - 0.706) / 0.001721
    
    
    # Aktualisiere globale Variablen mit den neuesten Werten
    latest_onboard_temp = onboard_temp

    
    # Printen der Daten in der Ausgabe
    print("Datum: ", date)
    print("Onboard Temperatur (°C): ", onboard_temp)

    # Schreibe die Daten in die CSV-Datei und aktualisiere ggf. die HTML-Seite
    write_csv('Temperatur_und_Luftfeuchtigkeit.csv', date, onboard_temp)
    # Die write_html Funktion nicht hier aufrufen, da sie bei Serveranfragen aufgerufen wird




# Angepasste Funktion zum Schreiben in eine HTML-Datei
def write_html(filename, onboard_temp):
    with open(filename, 'w') as htmlfile:
        htmlfile.write(f"""<html>
<head>
<title>Temperaturanzeige</title>
<!-- Stildefinitionen bleiben gleich -->
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


def send_html_page(client):
    # Verwende die globale Variable für die Antwort
    if latest_onboard_temp is not None:
        write_html('index.html', latest_onboard_temp)
        # Öffnen der index.html Datei und Senden als HTTP-Antwort
        with open('index.html', 'rb') as f:
            response = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + f.read()
            client.send(response)
    else:
        # Senden einer Fehlermeldung oder einer Warte-Seite, falls keine Daten verfügbar sind
        pass

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
            elif path == "/api/sensordata":
                send_sensor_data(cl)
            elif path == "/api/csvdata":  # Neue Bedingung für die CSV-Daten
                send_csv_data(cl)  # Du musst diese Funktion implementieren
            else:
                send_404(cl)
        cl.close()

        
    client.close()




# Timer für die Temperaturmessung alle 3 Sekunden initialisieren
# Globale Variablen für die zuletzt gemessenen Werte
latest_onboard_temp = None
latest_external_temp = None
latest_humidity = None


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

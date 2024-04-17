from machine import ADC, Timer, Pin
import utime
import network
import socket
from time import sleep
import json  # Dieser Import fehlte

def format_datetime_custom(dt):
    year, month, day, hour, minute, second, _, _ = dt
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(year, month, day, hour, minute, second)

#### code for csv creation and sending
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
    max_rows = 100
    with open(filename, "r") as csv_file:
        lines = csv_file.readlines()

    if len(lines) >= max_rows:
        lines = lines[-(max_rows-1):]

    with open(filename, 'w') as csv_file:
        for line in lines:
            csv_file.write(line)
        csv_file.write(f"{date},{onboard_temp}\n")  # Entfernen von external_temp und humidity

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
    write_csv('data/measurements.csv', date, onboard_temp)
    # Die write_html Funktion nicht hier aufrufen, da sie bei Serveranfragen aufgerufen wird

def send_csv_data(client):
    data = read_csv('Temperatur_und_Luftfeuchtigkeit.csv', 5)  # Lese die letzten 5 Zeilen
    response = json.dumps(data)
    client.send(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + response.encode('utf-8'))
    client.close()

        
#### sending sensor data to api
def send_sensor_data(client):
    from datetime import datetime
    
    data = {
        "date_time": datetime.now().strfmt("%Y-%d-%m %H:%M:%S"),
        "onboard_temp": latest_onboard_temp
    }
    response = json.dumps(data)
    client.send(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + response.encode('utf-8'))
    client.close()



# Funktion zum Starten des Servers
def start_server():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print('Server gestartet. Warte auf Verbindung...')
    return s

        
#### creating and sending html page to server
def write_html(filename, onboard_temp):
    with open(filename, "r") as f:
        html_template = f.read()
        datetime_str = format_datetime_custom(utime.localtime())
        html_output = html_template.replace("{onboard_temp}", str(onboard_temp))
        html_output = html_output.replace("{datetime}", datetime_str)
        return html_output

def generate_response(content_type, content):
    response = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: {}\r\n"
        "Content-Length: {}\r\n"
        "\r\n"
        "{}"
    )
    return response.format(content_type, len(content), content)


def send_html_page(client):
    # Verwende die globale Variable für die Antwort
    if latest_onboard_temp is not None:
        html_output = write_html('assets/index.html', latest_onboard_temp)
        # Öffnen der index.html Datei und Senden als HTTP-Antwort
        response = generate_response("text/html", html_output)
        client.send(response)
    else:
        # Senden einer Fehlermeldung oder einer Warte-Seite, falls keine Daten verfügbar sind
        pass

def send_file(client, file_path):
    import os
    try:
        with open(file_path, "r") as file:
            content = file.read()
            if file_path.endswith(".css"):
                content_type = "text/css"
            elif file_path.endswith(".js"):
                content_type = "text/javascript"
            elif file_path.endswith(".csv"):
                content_type = "text/csv"
            else:
                content_type = "text/plain"
            response = generate_response(content_type, content)
            client.send(response.encode())
    except FileNotFoundError:
        send_404(client)

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
            elif path.startswith("/assets/"):
                file_path = path[1:] # remove leading "/"
                send_file(cl, file_path)
            elif path.startswith("/data/"):
                file_path = path[1:]
                send_file(cl, file_path)
            elif path == "/api/sensordata":
                send_sensor_data(cl)
            elif path == "/api/csvdata":  # Neue Bedingung für die CSV-Daten
                send_csv_data(cl)  # Du musst diese Funktion implementieren
            else:
                send_404(cl)
        cl.close()

        
    client.close()

# Initialisierung des ADC4 für den Onboard-Temperatursensor
sensor_temp = ADC(4)
conversion_factor = 3.3 / (65535)


# Timer für die Temperaturmessung alle 3 Sekunden initialisieren
# Globale Variablen für die zuletzt gemessenen Werte
latest_onboard_temp = None
latest_external_temp = None
latest_humidity = None


# Timer für die Messung aller Sensordaten alle 3 Sekunden initialisieren
temperature_timer = Timer(-1)
temperature_timer.init(period=5000, mode=Timer.PERIODIC, callback=read_sensors_and_write_to_csv)

# WLAN-Verbindung herstellen
ssid = "FRITZ!Box 5530 MY"
password = "99727768816312159273"
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.scan()
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

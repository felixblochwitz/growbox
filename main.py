from machine import ADC, Timer, Pin
import utime
import network
import socket
from time import sleep
import json
import dht


def create_time_stamp_string():
    current = utime.localtime()
    year, month, day, hour, minute, second, _, _ = current
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        year, month, day, hour, minute, second
    )


# Initialisieren des DHT22-Sensors
sensor = dht.DHT22(machine.Pin(15))

# Initialisiere die ADCs für die Bodenfeuchtigkeitssensoren
adc1 = ADC(Pin(28))
adc2 = ADC(Pin(27))


def read_soil_moisture():
    value1 = adc1.read_u16()
    value2 = adc2.read_u16()
    moisture_percentage1 = (1 - value1 / 65535) * 100
    moisture_percentage2 = (1 - value2 / 65535) * 100
    return moisture_percentage1, moisture_percentage2


def read_csv(filename, n=5):
    with open(filename, "r") as file:
        lines = file.readlines()[-n:]
    data = []
    for line in lines:
        parts = line.strip().split(",")
        date, onboard_temp, external_temp, humidity, soil_moisture1, soil_moisture2 = (
            parts
        )
        data.append(
            {
                "date": date,
                "onboard_temp": float(onboard_temp),
                "external_temp": float(external_temp),
                "humidity": float(humidity),
                "soil_moisture1": float(soil_moisture1),
                "soil_moisture2": float(soil_moisture2),
            }
        )
    return data

def write_csv(
    filename,
    date,
    onboard_temp,
    external_temp,
    humidity,
    soil_moisture1,
    soil_moisture2,
):
    max_rows = 100
    with open(filename, "r") as csv_file:
        lines = csv_file.readlines()

    if len(lines) >= max_rows:
        lines = lines[-(max_rows - 1) :]

    with open(filename, "w") as csv_file:
        for line in lines:
            csv_file.write(line)
        csv_file.write(
            f"{date},{onboard_temp}, {external_temp}, {humidity}, {soil_moisture1}, {soil_moisture2}\n"
        )

def read_sensors_and_write_to_csv(timer):
    global latest_onboard_temp, latest_external_temp, latest_humidity, latest_soil_moisture1, latest_soil_moisture2
    date = create_time_stamp_string()

    read_onboard = sensor_temp.read_u16()
    voltage = read_onboard * conversion_factor
    onboard_temp = 27 - (voltage - 0.706) / 0.001721

    # Runden der Onboard-Temperatur
    onboard_temp = round(onboard_temp)

    sensor.measure()
    external_temp = sensor.temperature()
    humidity = sensor.humidity()

    # Runden der externen Temperatur und Luftfeuchtigkeit
    external_temp = round(external_temp)
    humidity = round(humidity)

    soil_moisture1, soil_moisture2 = read_soil_moisture()

    # Runden der Bodenfeuchtigkeitswerte
    soil_moisture1 = round(soil_moisture1)
    soil_moisture2 = round(soil_moisture2)

    latest_onboard_temp = onboard_temp
    latest_external_temp = external_temp
    latest_humidity = humidity
    latest_soil_moisture1 = soil_moisture1
    latest_soil_moisture2 = soil_moisture2

    print(f"Datum: {date}")
    print(f"Onboard Temperatur (°C): {onboard_temp}")
    print(f"Externe Temperatur (°C): {external_temp}")
    print(f"Luftfeuchtigkeit (%): {humidity}")
    print(f"Bodenfeuchtigkeit 1 (%): {soil_moisture1}")
    print(f"Bodenfeuchtigkeit 2 (%): {soil_moisture2}")

    write_csv(
        "Temperatur_und_Luftfeuchtigkeit.csv",
        date,
        onboard_temp,
        external_temp,
        humidity,
        soil_moisture1,
        soil_moisture2,
    )


def send_csv_data(client):
    data = read_csv("Temperatur_und_Luftfeuchtigkeit.csv", 5)
    response = json.dumps(data)
    client.send(
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n"
        + response.encode("utf-8")
    )
    client.close()


def send_sensor_data(client):
    data = {
        "onboard_temp": latest_onboard_temp,
        "external_temp": latest_external_temp,
        "humidity": latest_humidity,
        "soil_moisture1": latest_soil_moisture1,
        "soil_moisture2": latest_soil_moisture2,
    }
    response = json.dumps(data)
    client.send(
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n"
        + response.encode("utf-8")
    )
    client.close()


def start_server():
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("Server gestartet. Warte auf Verbindung...")
    return s


def write_html(
    filename, onboard_temp, external_temp, humidity, soil_moisture1, soil_moisture2
):
    with open(filename, "r") as f:
        html_template = f.read()
        datetime_str = create_time_stamp_string()
        html_output = html_template.replace("{datetime}", datetime_str)

        # Hier runden wir die Werte, bevor wir sie in das HTML einfügen
        html_output = html_output.replace("{onboard_temp}", str(round(onboard_temp)))
        html_output = html_output.replace("{external_temp}", str(round(external_temp)))
        html_output = html_output.replace("{humidity}", str(round(humidity)))
        html_output = html_output.replace(
            "{soil_moisture1}", str(round(soil_moisture1))
        )
        html_output = html_output.replace(
            "{soil_moisture2}", str(round(soil_moisture2))
        )

        return html_output


def generate_html_response(content):
    response = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html\r\n"
        "Content-Length: {}\r\n"
        "\r\n"
        "{}"
    )
    print(response)
    return response.format(len(content), content)


def send_html_page(client):
    if (
        latest_onboard_temp is not None
        and latest_external_temp is not None
        and latest_soil_moisture1 is not None
        and latest_soil_moisture2 is not None
        and latest_humidity is not None
    ):
        html_output = write_html(
            "index.html",
            latest_onboard_temp,
            latest_external_temp,
            latest_humidity,
            latest_soil_moisture1,
            latest_soil_moisture2,
        )
        response = generate_html_response(html_output)
        client.send(response)
    else:
        response = "HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nInternal Server Error: Sensor data missing"
        client.send(response.encode("utf-8"))
    client.close()


def send_404(client):
    response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\n404 Not Found"
    client.send(response.encode("utf-8"))
    client.close()


def handle_requests(s):
    while True:
        cl, addr = s.accept()
        print("Client verbunden von", addr)
        request = cl.recv(1024).decode("utf-8")
        request_line = request.split("\r\n")[0]
        method, path, _ = request_line.split(" ")

        if method == "GET":
            if path == "/":
                send_html_page(cl)
            elif path == "/api/sensordata":
                send_sensor_data(cl)
            elif path == "/api/csvdata":
                send_csv_data(cl)
            else:
                send_404(cl)
        cl.close()


sensor_temp = ADC(4)
conversion_factor = 3.3 / (65535)

latest_onboard_temp = None
latest_external_temp = None
latest_humidity = None
latest_soil_moisture1 = None
latest_soil_moisture2 = None

temperature_timer = Timer(-1)
temperature_timer.init(
    period=5000, mode=Timer.PERIODIC, callback=read_sensors_and_write_to_csv
)

ssid = "FRITZ!Box 7530 OW"
password = "monkey-gin!"
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.scan()
wlan.connect(ssid, password)
max_wait = 10

while max_wait > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    max_wait -= 1
    print("Warten auf Verbindung...")
    sleep(1)

if wlan.status() != 3:
    raise RuntimeError("Netzwerkverbindung fehlgeschlagen")
else:
    print("Verbunden")
    status = wlan.ifconfig()
    print("IP-Adresse:", status[0])

server = start_server()
handle_requests(server)

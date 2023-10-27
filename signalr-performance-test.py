import logging
import re
import time
from signalrcore.hub_connection_builder import HubConnectionBuilder
import urllib3
import multiprocessing

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
server_url = ""  # input server url
hub_name = "/"  # input hub name
num_executions = 1
time_to_stay_connected_in_seconds = 10


class VariableLoggingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.latest_log_message = None

    def emit(self, record):
        log_message = self.format(record)
        # Limit the line length to 200 characters
        if len(log_message) > 200:
            log_message = log_message[:197] + "..."
        with open("log.txt", "a") as log:
            log.write(log_message + "\n")
        # only log the response from an invoke
        if log_message.startswith('DEBUG:SignalRCoreClient:{"type":3'):
            with open("log_condensed.txt", "a") as log:
                log.write(log_message + "\n")


handler = VariableLoggingHandler()
logging.basicConfig(level=logging.DEBUG, handlers=[handler])


def execute_script(instance_number):
    # create an unique invocationId
    invoc = str(instance_number) + "0000000-0000-0000-0000-000000000000"
    connection_url = server_url + hub_name
    hub_connection = HubConnectionBuilder()\
        .with_url(connection_url, options={"verify_ssl": False}) \
        .with_automatic_reconnect({
            "type": "interval",
            "keep_alive_interval": 10,
            "intervals": [1, 3, 5, 6, 7, 87, 3]
        }).build()
    print("Hub connection created")

    def on_open():
        print(f"Connection {instance_number} created")
        send_invoke_method_name()

    def send_invoke_method_name():
        payload = []
        payload.append({"": ""})  # add/create json

        def invoke_method_name_callback(response):
            # example, to retrieve data from the logging. in this example an access_code
            access_code = find_access_code(invoc)
            if access_code:
                print(
                    f"Received a CompletionMessage. Access Code: {access_code}")
                send_invoke_second_method_name(access_code)
            else:
                print("Access Code not found in the log.")

        hub_connection.send("method_name", payload,
                            invoke_method_name_callback, invoc)
        print("method_name request sent")

    def send_invoke_second_method_name(access_code):
        payload = []
        payload.append({"accessCode": access_code})  # add/create json
        hub_connection.send("second_method_name_response", payload)

    def second_method_name_response(response):
        print("second_method_name message recieved")

    hub_connection.on("second_method_name_response",
                      second_method_name_response)

    hub_connection.on_open(on_open)
    hub_connection.start()

    time.sleep(time_to_stay_connected_in_seconds)
    hub_connection.stop()

# method to find data in log. invocation_id is needed for making sure data retrieved is from same thread (multithreading)


def find_access_code(invocation_id):
    with open("log_condensed.txt", "r") as log_file:
        log_contents = log_file.read()

    # find the accessCode associated with the invocationId in the log file using regex. change accordingly.
    pattern = r'"type":3,"invocationId":"' + \
        re.escape(invocation_id) + \
        r'","result":{"example":"[^"]+","accessCode":"(\d+)"'
    match = re.search(pattern, log_contents)
    if match:
        access_code = match.group(1)
        return access_code
    else:
        return None


if __name__ == "__main__":
    with open("log.txt", "w"):
        pass
    with open("log_condensed.txt", "w"):
        pass

    processes = []

    for i in range(num_executions):
        process = multiprocessing.Process(target=execute_script, args=(i,))
        processes.append(process)
        process.start()

        # Wait for x seconds after every x connections
        if (i + 1) % 10 == 0:
            time.sleep(5)

    for process in processes:
        process.join()

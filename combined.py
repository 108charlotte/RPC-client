# https://docs.python.org/3/library/xmlrpc.html
import xmlrpc.client
import xmlrpc.server
import time
import json
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import threading

# client
def run_client(): 
    with xmlrpc.client.ServerProxy("http://localhost:8000") as proxy: 
        while True: 
            proxy.heartbeat(json.dumps({"student_name": "charlotte", "timestamp": int(time.time())}))
            time.sleep(10) # 10 second sleep before sending another heartbeat ping

# server
def run_server(): 
    with SimpleXMLRPCServer(('localhost', 8000)) as server: 
        server.register_introspection_functions()

        def heartbeat(json_string): 
            context = json.load(json_string)
            name = context["student_name"]
            timestamp = context["timestamp"]
            if time.time() - timestamp < 43200: # 12 hours equivalent in epoch seconds
                print(f"received successful request from {name} at {timestamp}")
                return 0 # for success
            return 1 # for failiure

        server.register_function(heartbeat, "heartbeat")
        server.serve_forever()

# https://www.geeksforgeeks.org/python/multithreading-python-set-1/
client_thread = threading.Thread(target=run_client)
server_thread = threading.Thread(target=run_server)

client_thread.start()
server_thread.start()

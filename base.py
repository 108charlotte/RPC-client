import xmlrpc.client
import time
import json
import threading
import random
from xmlrpc.server import SimpleXMLRPCServer
# note: :%y+ to copy to clipboard
# BASE database: 
# - gossip abt database entries
# - if conflict, choose newest timestamp

node_ports = [6363, 6364, 6365, 6366]
local_ip_addr = "127.0.0.1"
fail_chance = 0.2
db_sample_size = 10

class Server: 
    def __init__(self, port): 
        # includes key, value, timestamp.
        self.database = []
        self.port = port

    def read_all(self): 
        print(f"Server responding to read all request with: {self.database}")
        return self.database

    def start_sync_processes(self): 
        while True: 
            self.send_selection_sync()
            time.sleep(5)

    def send_selection_sync(self): 
        address = self.port
        while self.port == address: 
            address = random.choice(node_ports)

        print(f"Background sync from {self.port}: beginning selection send to {address}")
        database_selection = random.sample(self.database, min(db_sample_size, len(self.database)))

        try: 
            address = local_ip_addr + ":" + str(address)
            with xmlrpc.client.ServerProxy("http://" + str(address)) as proxy: 
                responses = []
                for item in database_selection: 
                    print(f"Sending write to {address} from {str(self.port)}")
                    response = proxy.write(json.dumps(item)) # write will only write if valid and if timestamp newer than current
                    print(f"Received response {str(response)}")
                    responses.append(response)
                return responses
        except Exception as e: 
            print(f"Background sync error {e}")
            return []

    def write(self, json_string): 
        print("-------------------------------------------------------------------------------------------------------------------------")
        context = json.loads(json_string)
        try: 
            key = context['key']
            value = context['value']
            timestamp = context['timestamp']
            print(f"SERVER: write received write request with key: {key}, value: {value}, and timestamp: {timestamp}")
        except Exception as e: # malformed data
            print(f"SERVER: write received write request with malformed data, returning {e}")
            return 1

        if key is None or value is None or timestamp is None: 
            print(f"SERVER: write received write request with malformed data")
            return 1
        
        if random.random() < fail_chance: 
            print(f"SERVER: write returning fail due to random chance")
            return 1
                
        for i, item in enumerate(self.database): 
            if item['key'] == key: 
                if not self.database[i]['writing']: 
                    self.database[i]['writing'] = True

                    if timestamp < item['timestamp']: 
                        print(f"SERVER: write returning fail bc timestamp older than current one in db")
                        self.database[i]['writing'] = False # done trying to write
                        return 1 # reject change bc old TODO: not sure if this is the right course of action
                    else:
                        self.database[i] = {'key': key, 'value': value, 'timestamp': timestamp, 'writing': False}
                        return 0
                else: 
                    print("SERVER: write failing because other write in progress")
                    return 1

        # item not found in db if hasn't returned yet, so add to db
        self.database.append({'key': key, 'value': value, 'timestamp': timestamp, 'writing': False})
        return 0

    def start(self): 
        global local_ip_addr
        with SimpleXMLRPCServer((local_ip_addr, self.port)) as server: 
            server.register_introspection_functions()
            server.register_function(self.write, "write")
            server.register_function(self.read_all, "read_all")
            server.serve_forever()

def run_client(): 
    options = ["hihi", "r u alive?", "i'm alive", 6, 9]
    while True: 
        try: 
            to_write = random.randint(0, 1) == 0
            port_to_send_to = random.choice(node_ports)
            address = local_ip_addr + ":" + str(port_to_send_to)
            with xmlrpc.client.ServerProxy(("http://" + address)) as proxy: 
                if to_write: 
                    key = random.choice(options)
                    value = random.choice(options)
                    timestamp = int(time.time())
                    print(f"Client: sending to http://{address}: key: {key}, value: {value}, timestamp: {timestamp}")
                    response = proxy.write(json.dumps({'key': key, 'value': value, 'timestamp': timestamp}))
                else: 
                    response = proxy.read_all()
                print("-------------------------------------------------------------------------------------------------------------------------")
                print(f"Client received response: {response}")
        except Exception as e: 
            print(f"Client received exception: {e}")
        time.sleep(2)

def run_server(index:int): # this doesn't rly need its own func anymore
    server = Server(node_ports[index])
    threading.Thread(target=server.start_sync_processes, daemon=True).start()
    server.start()

    
def start_all_servers(): 
    global local_ip_addr
    for i in range(len(node_ports)): 
        print(f"Starter: creating server {i+1} at port: {node_ports[i]} at ip: {local_ip_addr}")
        threading.Thread(target=run_server, args=(i,), daemon=True).start()
    print("-------------------------------------------------------------------------------------------------------------------------")

start_all_servers()
#threading.Thread(target=run_client, daemon=True).start()
run_client()

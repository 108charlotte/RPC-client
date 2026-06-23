import xmlrpc.client
import time
import json
import threading
import random
import socketserver
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
 

node_ports = [6363, 6364, 6365]
local_ip_addr = "127.0.0.1"
fail_chance = 0.2

class Server: 
    def __init__(self, port): 
        # includes key, value, timestamp, write_quorum_loading, and quorum_count. the first 3 are always passed, the last is set when updating. 
        self.database = []
        self.port = port # feels like I need to store this, but not sure how to use it for this approach lol

    def read_all(self, propagate:bool=True): 
        # reset local database quorum count
        for i in range(len(self.database)):
            self.database[i]['quorum_count'] = 0

        if propagate: 
            responses = self.get_read_quorum()
            self.database = responses # update to most recent/agreed upon data
            print(f"Responses: {responses}")
            return responses
        else: 
            return self.database

    def get_read_quorum(self): 
        global node_ports
        global local_ip_addr
        print("-------------------------------------------------------------------------------------------------------------------------")

        client_addresses = [local_ip_addr + ":" + str(port) for port in node_ports]
        unique_items = []
        for item in self.database:
            item["quorum_count"] = 1
            unique_items.append(item)
        print(f"Quorum: found {len(unique_items)} unique items in this server's db")
        for address in client_addresses: 
            if str(self.port) in address: 
                db = self.read_all(False)
            else: 
                db = self.send_read_to_ip(address, False)
            for item in db: 
                try: 
                    index = unique_items.index(item)
                    unique_items[index]["quorum_count"] += 1
                except ValueError: 
                    unique_items.append(item)
        print(f"Quorum: found {len(unique_items)} unique items total")
        min_val_for_consensus = len(node_ports) / 2
        to_return = []
        for item in unique_items: 
            if item["quorum_count"] > min_val_for_consensus: 
                to_return.append(item)
        print(f"Quorum: returning {to_return} from read operation")
        return to_return

    def send_read_to_ip(self, address, propagate:bool=True): 
        print(f"Quorum: beginning read info send to {address}, propagate: {propagate}")
        try: 
            with xmlrpc.client.ServerProxy("http://" + address) as proxy: 
                response = proxy.read_all(propagate)
                return response
        except Exception as e: 
            print(f"Quorum: read error {e}")
            return []

    def send_write_to_ip(self, address, key, value, timestamp, propagate:bool=True): 
        print(f"Quorum: beginning write info send, propagate: {propagate}")
        try: 
            with xmlrpc.client.ServerProxy("http://" + address) as proxy: 
                response = proxy.write(json.dumps({'key': key, 'value': value, 'timestamp': timestamp, 'propagate': propagate}))
                return response
        except Exception as e: 
            print(f"Quorum: write error {e}")
            return 0

    def update_db_after_response(self, json_string, response:int): # super duper not secure, but if I stored my_response it wouldn't work for new items, or I would just store every single item in every single db along with how it responded, which would not be ideal, so I'm doing this for now
        print("-------------------------------------------------------------------------------------------------------------------------")
        try: 
            context = json.loads(json_string)
            key = context['key']
            value = context['value']
            timestamp = context['timestamp']

            updated = False
            for i, item in enumerate(self.database): 
                if updated: 
                    break
                if item['key'] == key: 
                    if response == 0: # quorum liked it and I liked it (since this is getting sent to me) - then make the change
                        self.database[i]['value'] = value
                        self.database[i]['timestamp'] = timestamp
                        print(f"Successfully updated the value of {key} to {value} with {timestamp}")
                    self.database[i]['write_quorum_loading'] = False
                    updated = True
            if not updated and response == 0: # value not found in db
                self.database.append(context)
                print(f"Could not find key in db, so added")
            return 0
        except Exception as e: 
            print(f"Force updating db returned error {e}")
            return 1

    def get_write_quorum(self, json_string): 
        global node_ports
        global local_ip_addr

        print("-------------------------------------------------------------------------------------------------------------------------") 
        data = json.loads(json_string)
        client_addresses = [local_ip_addr + ":" + str(port) for port in node_ports]
        responses = []
        for address in client_addresses: 
            print(f"Getting write response from {address} using key: {data['key']}, value: {data['value']}, timestamp: {data['timestamp']}, propagate: {False}...")
            if str(self.port) in address: 
                response = self.write(json.dumps({'key': data['key'], 'value': data['value'], 'timestamp': data['timestamp'], 'propagate': False}))
            else: 
                response = self.send_write_to_ip(address, data['key'], data['value'], data['timestamp'], False) # propagate should always be false when trying to get quorum from others
            print(f"Response from {address}: {response}")
            print("-------------------------------------------------------------------------------------------------------------------------")
            responses.append({'port': address, 'value': response})
        return responses

    def write(self, json_string): 
        # updating write quorum loading to true
        print("-------------------------------------------------------------------------------------------------------------------------")
        context = json.loads(json_string)
        propagate = context['propagate'] # if context['propagate'] else True # True by default
        if propagate: 
            print(f"SERVER: received propagate write request")
            responses = self.get_write_quorum(json_string)
            print(f"Responses: {responses}")
            total = sum([r['value'] for r in responses]) # responses = dictionary
            response = 0 if total > len(node_ports) / 2 else 1
            print(f"Writing, received {responses} from quorum")
            to_inform = [r['port'] for r in responses if r['value'] == 0]
            for server in to_inform: 
                try: 
                    with xmlrpc.client.ServerProxy("http://" + server) as proxy: 
                        force_write_response = proxy.update_db_after_response(json.dumps(context), response)
                        print(f"Force write to {server} responded with {force_write_response}")
                except Exception as e: 
                    print(f"Force write to {server} returned error {e}")
                    return 1
            return 0
        else: 
            try: 
                key = context['key']
                value = context['value']
                timestamp = context['timestamp']
                print(f"SERVER: write received non-propagate request with key: {key}, value: {value}, and timestamp: {timestamp}")
            except Exception as e: # malformed data
                print(f"SERVER: write received non-propagate request with malformed data, returning {e}")
                return 1

            if key is None or value is None or timestamp is None: 
                print(f"SERVER: write received non-propagate request with malformed data, returning {e}")
                return 1
            
            if random.random() < fail_chance: 
                print(f"SERVER: write returning fail due to random chance")
                return 1
            
            for i, item in enumerate(self.database): 
                if item['key'] == key: 
                    if not self.database[i]['write_quorum_loading']: 
                        self.database[i]['write_quorum_loading'] = True

                        if timestamp < item['timestamp']: 
                            print(f"SERVER: write returning fail bc timestamp older than current one in db")
                            return 1 # reject change bc old TODO: not sure if this is the right course of action
                    else: 
                        print("SERVER: write failing because other write in progress")
                        return 0
            return 0 # no 1s returned, nothing failed

    def run_self(self): 
        global local_ip_addr
        with SimpleXMLRPCServer((local_ip_addr, self.port)) as server: 
            server.register_introspection_functions()
            server.register_function(write, "write")
            server.register_function(read_all, "read_all")
            server.register_function(update_db_after_response, "update_db_after_response")
            server.serve_forever()

def run_client(): 
    options = ["hihi", "r u alive?", "i'm alive", 6, 9, None]
    while True: 
        try: 
            to_write = random.randint(0, 1) == 0
            port_to_send_to = random.choice(node_ports)
            address = local_ip_addr + ":" + str(port_to_send_to)
            if to_write: 
                key = random.choice(options)
                value = random.choice(options)
                timestamp = time.time()
            with xmlrpc.client.ServerProxy(("http://" + address)) as proxy: 
                if to_write: 
                    key = random.choice(options)
                    value = random.choice(options)
                    timestamp = time.time()
                    response = proxy.write(json.dumps({'key': key, 'value': value, 'timestamp': timestamp, 'propagate': True}))
                else: 
                    response = proxy.read_all()
                print(f"Client received response: {response}")
        except Exception as e: 
            print(f"Client received exception: {e}")
        time.sleep(10)

def run_server(index:int): 
    server = Server(node_ports[index])

def start_all_servers(): 
    global local_ip_addr
    for i in range(len(node_ports)): 
        print(f"Starter: creating server {i} at {node_ports[i]} at ip: {local_ip_addr}")
        threading.Thread(target=run_server, args=(i,), daemon=True).start()

start_all_servers()
#threading.Thread(target=run_client, daemon=True).start()
run_client()

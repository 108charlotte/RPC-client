import xmlrpc.client
import time
import json
from xmlrpc.server import SimpleXMLRPCServer
import threading
import random


node_ports = [6363, 6364, 6365]
local_ip_addr = "0.0.0.0"

# includes key, value, timestamp, quorum_loading. the first 3 are always passed, the last is set when updating. 
database = []

fail_chance = 0.2


def read_all(json_string): 
    pass

def send_write_to_ip(address, key, value, timestamp, propagate:bool=True): # true by default
    try: 
        with xmlrpc.client.ServerProxy(address) as proxy: 
            response = proxy.write(json.dumps({"key": key, "value": value, "timestamp": int(timestamp), "propagate": propagate}))
    except Exception as e: 
        print(f"Quorum: info sent - {address}, {key}, {value}, {timestamp}")
        print(f"Quorum: error {e}")
        response = 0
    return response

def update_db_after_response(json_string, response:int): # super duper not secure, but if I stored my_response it wouldn't work for new items, or I would just store every single item in every single db along with how it responded, which would not be ideal, so I'm doing this for now
    global database
    try: 
        context = json.loads(json_string)
        key = context['key']
        value = context['value']
        timestamp = context['timestamp']

        updated = False
        for i, item in enumerate(database): 
            if updated: 
                break
            if item['key'] == key: 
                if response == 0: # quorum liked it and I liked it (since this is getting sent to me) - then make the change
                    database[i]['value'] = value
                    database[i]['timestamp'] = timestamp
                    print(f"Successfully updated the value of {key} to {value} with {timestamp}")
                database[i]['quorum_loading'] = False
                updated = True
        if not updated and response == 0: # value not found in db
            database.append(context)
            print(f"Could not find key in db, so added")
        return 0
    except Exception as e: 
        print(f"Force updating db returned error {e}")
        return 1

def get_write_quorum(json_string): 
    global node_ports
    global local_ip_addr
    
    data = json.loads(json_string)
    client_addresses = ["http://" + local_ip_addr + ":" + str(port) for port in node_ports]
    responses = []
    for address in client_addresses: 
        print(f"Getting write response from {address} using key: {data['key']}, value: {data['value']}, timestamp: {data['timestamp']}, propagate: {False}...")
        response = send_write_to_ip(address, data['key'], data['value'], data['timestamp'], False) # propagate should always be false when trying to get quorum from others
        print(f"Response from {address}: {response}")
        responses.append({'port': address, 'value': response})
    return responses

def write(json_string): 
    context = json.loads(json_string)
    propagate = context['propagate'] if context['propagate'] else True # True by default
    if propagate: 
        print(f"SERVER: received propagate write request")
        responses = get_write_quorum(json_string)
        print(f"Responses: {responses}")
        total = sum([response['value'] for response in responses]) # returns a dictionary
        response = 0 if total > len(node_ports) / 2 else 1
        to_inform = [response['address'] for response in responses if response['value'] == 0]
        for server in to_inform: 
            try: 
                with xmlrpc.client.ServerProxy(server) as proxy: 
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
            print(f"SERVER: received non-propagate request with key: {key}, value: {value}, and timestamp: {timestamp}")
        except Exception as e: # malformed data
            print(f"SERVER: received non-propagate request with malformed data, returning {e}")
            return 1
        
        if random.random() < fail_chance: 
            print(f"SERVER: returning fail due to random chance")
            return 1
        
        for item in database: 
            if item['key'] == key: 
                if timestamp < item['timestamp']: 
                    print(f"SERVER: returning fail bc timestamp older than current one in db")
                    return 1 # reject change bc old TODO: not sure if this is the right course of action
        return 0 # no 1s returned, nothing failed

def send_updates_to_db(): 
    global local_ip_addr
    global node_ports
    keys = ["hi", "hahaha", "why", "r u serious", None]
    values = ["0", "1", "3", "50", None]
    client_addresses = ["http://" + local_ip_addr + ":" + str(port) for port in node_ports]

    for i in range(5): 
        send_to = i % len(node_ports)
        print(f"Sender: sending {client_addresses[send_to]}, {keys[i]}, {values[i]}, and {int(time.time())}")
        send_write_to_ip(client_addresses[send_to], keys[i], values[i], int(time.time()), True)
        time.sleep(2)

def run_server(index:int): 
    global local_ip_addr
    with SimpleXMLRPCServer((local_ip_addr, node_ports[index])) as server: 
        server.register_introspection_functions()
        server.register_function(write, "write")
        server.register_function(read_all, "read_all")
        server.serve_forever()

def start_all_servers(): 
    for i in range(len(node_ports)): 
        print(f"Starter: creating server {i}")
        server = threading.Thread(target=run_server, args=(i,), daemon=True).start()

start_all_servers()
send_updates_to_db() # not sure if I can call this after

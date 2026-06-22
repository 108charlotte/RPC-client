# 3 node ACID database server
# accept RPCs for write {key: ___, value: _____, timestamp: _____} and read_all {}, which prints the db contents
# servers need to propogate writes to each other, if both servers reject a write attempt, what do you do? what abt one server? need to communicate back w/ original node that accepted it? 
# all read_all needs to return a consistent set of keys and values? 
# - require a quorum? 
# assume that there can be @ least 1 node in 3-node system that doesn't approve of a write; if 2/3 approve, you can still accept it; make sure u try to read from @ least 2 nodes, any successful transaction should be from one of those two nodes
# read - one node hits up another node to get other data, then produce combined result
# write - requires @ least 1 other node to approve write before finalized

import xmlrpc.client
import time
import json
from xmlrpc.server import SimpleXMLRPCServer
import threading
import random

# receives write --> attempt to propagate
# - majority of nodes to be in agreement abt write before finalized
# - if 1 other agrees w/ it (has seen request + stored in key-value store)
# - node receiving propogated write request, doesn't need to propagate it
# - how to know if receiving propogated request: optional is propagate true/false - true or just blank initially
# run 3 opies of client/server script on separate ports of your machine
# - reject with a 20% probability for write attempts
# only 1 process can run @ a time
# temporary variable abt conflicting write in progress

# currently designed for all running on the same computer
# TODO: add updating key flag
node_ports = ['6363', '6364', '6365']
ip_addr = "162.247.87.196"

database = []
fail_chance = 0.2

def send_write_to_ip(address, key, value, timestamp, propagate:bool=True): # true by default
    try: 
        with xmlrpc.client.ServerProxy(address) as proxy: 
            response = proxy.write(json.dumps({"key": key, "value": value, "timestamp": int(timestamp), "propagate": propagate}))
    except Exception as e: 
        print(f"Quorum: info send - {address}, {key}, {value}, {timestamp}")
        print(f"Quorum: error {e}")
        response = 0
    return response

def get_ip_db(address): 
    try: 
        with xmlrpc.client.ServerProxy(address) as proxy: 
            response = proxy.read_all()
    except Exception as e: 
        print(f"Quorum: error {e}")
        response = []
    return response

# horrible time complexity
def get_read_quorum(): 
    global database
    global node_ports

    client_addresses = ["http://" + ip_addr + ":" + port for port in node_ports]
    unique_items = []
    for item in database:
        item["quorum_count"] = 1
        unique_items.append(item)
    print(f"Quorum: found {len(unique_items)} unique items in this server's db")
    for address in client_addresses: 
        db = get_ip_db(address)
        for item in db: 
            index = unique_items.index(item)
            if index != -1: 
                unique_items[index]["quorum_count"] += 1
            else: 
                unique_items.append(item)
    print(f"Quorum: found {len(unique_items)} unique items total")
    min_val_for_consensus = len(node_ports) / 2
    to_return = []
    for item in unique_items: 
        if item["quorum_count"] > min_val_for_consensus: 
            to_return.append(item)
    print(f"Quorum: returning {to_return} from read operation")
    return to_return

def get_write_quorum(json_string):
    global node_ports
    global ip_addr
    
    data = json.dumps(json_string)
    client_addresses = ["http://" + ip_addr + ":" + port for port in node_port]
    sum_responses = 0
    for address in client_addresses: 
        # includes this server
        response = send_write_to_ip(address, data['key'], data['value'], data['timestamp'], False) # propagate should always be false when trying to get quorum from others
        sum_responses += response
        if sum_responses > len(node_ports) / 2: 
            print(f"Quorum: reached majority of {sum_responses} out of {len(node_ports)} servers")
            return 0 # reached majority, can stop early
    print(f"Quorum: did not reach majority, had only {sum_responses} out of {len(node_ports)} servers")
    return 1 # if majority not reached in loop

def write(json_string): 
    context = json.loads(json_string)
    this_server_response = True # default value
    try: 
        key = context['key']
        value = context['value']
        timestamp = context['timestamp']
        propagate = context['propagate'] if context['propagate'] else True # true by default
        print(f"SERVER: received request with key: {key}, value: {value}, and timestamp: {timestamp}; instructions to propagate: {propagate}")
        # since I'm processing it, set propagate key to false
        context['propagate'] = False

    except Exception as e: 
        if propagate is not None and not propagate: # if I don't need to propagate
            print(f"SERVER: Server threw exception {e}")
            return 1
        else: # if None or true
            this_server_response = False

    if random.random() < fail_chance: 
        print(f"SERVER: Returning fail due to random chance")
        if propagate is None or propagate: 
            this_server_response = False
    
    # get quorum to see if other nodes agree
    should_write = get_quorum(json_string, this_node_port, this_server_response)
    if should_write: 
        try: 
            # TODO: this won't work if the response is malformed, since this server doesn't have all the info
            if key in database: # not sure if this syntax is right? 
                database[key] = value
            else: 
                database.append(json_string[:3]) # don't put propagate in db
            return 0
        except Exception as e: 
            print(f"SERVER: Server threw exception {e}")
    return 1

def send_updates_to_db(): 
    keys = ["hi", "hahaha", "why", "r u serious", None]
    values = ["0", "1", "3", "50", None]
    client_addresses = ["http://" + ip_addr + ":" + port for port in node_ports]

    for i in range(5): 
        send_to = i % len(node_ports)
        print(f"Sender: sending {client_addresses[send_to]}, {keys[i]}, {values[i]}, and {time.time()}")
        send_write_to_ip(client_addresses[send_to], keys[i], values[i], time.time()) # no propagate flag for rn
        time.sleep(5)

def run_server(index:int): 
    with SimpleXMLRPCServer((ip_addr, int(node_ports[index]))) as server: 
        server.register_introspection_functions()
        server.register_function(write, "write")
        server.register_function(get_read_quorum, "read_all")
        server.serve_forever()

def start_all_servers(): 
    for i in range(len(node_ports)): 
        print(f"Starter: creating server {i}")
        server = threading.Thread(target=run_server, args=(i,), daemon=True).start()

start_all_servers()
send_updates_to_db() # not sure if I can call this after

# https://docs.python.org/3/library/xmlrpc.html
import xmlrpc.client
import time
import json
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import threading
import difflib
import socket

socket.setdefaulttimeout(5)

server_name = "Charlotte"
server_ip_addr = "141.165.50.133"

start_server_to_ping = "141.165.50.153"

client_list = []
num_heartbeats_sent = 0 # used for deciding when to stop pinging start server

def send_heartbeat_to_ip(ip_dest, student_name, timestamp, ip_address, string_identifier): 
    try: 
        with xmlrpc.client.ServerProxy("http://" + ip_dest + ":6363") as proxy: 
            print()
            if string_identifier != "CLIENT": 
                print(f"{string_identifier}: Sending heartbeat with name: {student_name}, timestamp: {timestamp}, and ip address: {ip_address} to {ip_dest}")
            error = proxy.heartbeat(json.dumps({"student_name": student_name, "timestamp": int(timestamp), "ip_address": ip_address}))
            print(f"{string_identifier}: Sent heartbeat to {ip_dest}, server returned code {error}")
    except Exception as e: 
        print(f"{string_identifier}: Error - {e}")

def get_alphabetical_next_index_from_me(): 
    global client_list
    client_names = [client["student_name"] for client in client_list]
    after_me_alphabetically = [name for name in client_names if name > server_name]
    closest = difflib.get_close_matches(server_name, after_me_alphabetically, 1)
    client_index = 0
    for i, client in enumerate(client_list): 
        if client["student_name"] == closest: 
            client_index = i
            break
    return client_index
    
def purge_client_list(): 
    global client_list
    # go through client list and remove anything with a timestamp over 1 min old EXCEPT for my own client
    client_list = [client for client in client_list if abs(client["timestamp"] - time.time()) < 60]
    print(f"\nSERVER: New client list, old timestamps removed: {client_list}")
    

def get_next_client_index(curr_index): 
    global client_list
    return (curr_index + 1) % len(client_list)

# client
def run_client(): 
    global num_heartbeats_sent
    global client_list
    while True: 
        print(f"\nRUNNING CLIENT")
        purge_client_list()
        if num_heartbeats_sent < 2: 
            ip_addr_to_send_to = start_server_to_ping
            send_heartbeat = True
        else: 
            if len(client_list) >= 1: 
                ip_addr_to_send_to = client_list[get_alphabetical_next_index_from_me()]["ip_address"]
                send_heartbeat = True
            else: 
                print(f"CLIENT: No one available to heartbeat to")
                send_heartbeat = False
        
        if send_heartbeat: 
            print(f"CLIENT: Sending my own heartbeat to {ip_addr_to_send_to}")
            threading.Thread(target=send_heartbeat_to_ip, args=(ip_addr_to_send_to, "Charlotte", time.time(), server_ip_addr, "CLIENT"), daemon=True).start()
            # send_heartbeat_to_ip(ip_addr_to_send_to, "Charlotte", time.time(), server_ip_addr, "CLIENT")
            num_heartbeats_sent += 1

        time.sleep(10) # 10 second sleep before sending another heartbeat ping/checking if anyone available to send heartbeat ping to

# server
def heartbeat(json_string): 
    global client_list
    context = json.loads(json_string)
    name = context["student_name"]
    timestamp = int(context["timestamp"])
    ip_addr = context["ip_address"]
    print("\nRUNNING SERVER")
    print(f"SERVER: Received heartbeat with name: {name}, timestamp: {timestamp}, ip_addr: {ip_addr}")
    
    if name == "Charlotte": 
        print(f"\nSERVER: Someone sent Charlotte to herself, don't propagate")
        return 0
    
    if abs(time.time() - timestamp) < 20:
        print(f"SERVER: Timestamp {timestamp} valid for {name} at {ip_addr}")
        all_ip_addrs = [client["ip_address"] for client in client_list]
        # need to include timestamps and update
        if not ip_addr in all_ip_addrs: # ip address not already in list, then add to list along with name
            client_list.append({"ip_address": ip_addr, "student_name": name, "timestamp": timestamp})
            # sort: https://stackoverflow.com/questions/72899/how-can-i-sort-a-list-of-dictionaries-by-a-value-of-the-dictionary-in-python
            client_list = sorted(client_list, key=lambda d: d["student_name"])
            print(f"SERVER: Added {ip_addr} for {name} at {timestamp} to client_list")
            print(f"SERVER: {len(client_list)} people in client list: {client_list}")
        else: 
            # update timestamp of existing entry
            print(f"SERVER: Client exists in client list, updating client timestamp...")
            client_index = next((index for (index, d) in enumerate(client_list) if d["ip_address"] == ip_addr), None)
            if client_index is None: 
                print(f"SERVER: BUG - client index not found in list")
                return 1
            else: 
                client_list[client_index]["timestamp"] = timestamp
    else: 
        print(f"SERVER: Received invalid timestamp from {name} at {ip_addr} - {timestamp} was {abs(timestamp - time.time())} off")
        return 1
    
    purge_client_list()

    # send info to next in chain
    next_index = get_alphabetical_next_index_from_me()
    next_item = client_list[next_index]
    if next_item["ip_address"] == ip_addr: 
        old_item = next_item
        next_index = get_next_client_index(next_index)
        next_item = client_list[next_index]
        print(f"SERVER: Skipping {old_item['student_name']} to go to {next_item['student_name']}")
       
    if next_item["ip_address"] == ip_addr: 
        print(f"SERVER: too few people in network, not forwarding")
        return 1
    
    print(f"SERVER: forwarding {name} to {next_item['student_name']} (sending to IP: {next_item['ip_address']})")
    threading.Thread(target=send_heartbeat_to_ip, args=(next_item["ip_address"], name, timestamp, ip_addr, "SERVER"), daemon=True).start()
    # response = send_heartbeat_to_ip(next_item["ip_address"], name, timestamp, ip_addr, "SERVER")
    return 0

def run_server(): 
    with SimpleXMLRPCServer(('141.165.50.133', 6363)) as server: 
        server.register_introspection_functions()
        server.register_function(heartbeat, "heartbeat")
        server.serve_forever()

# https://www.geeksforgeeks.org/python/multithreading-python-set-1/
client_thread = threading.Thread(target=run_client)
server_thread = threading.Thread(target=run_server)

client_thread.start()
server_thread.start()

client_thread.join()
server_thread.join()

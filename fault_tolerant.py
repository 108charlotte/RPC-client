# https://docs.python.org/3/library/xmlrpc.html
import xmlrpc.client
import time
import json
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import threading
import difflib.get_close_matches

server_name = "Charlotte"
server_ip_addr = "141.165.50.133"

start_server_to_ping = "141.165.50.162"

client_list = []
num_heartbeats_sent = 0 # used for deciding when to stop pinging start server

def send_heartbeat_to_ip(ip_dest, student_name, timestamp, ip_address, string_identifier): 
    try: 
        with xmlrpc.client.ServerProxy("http://" + ip_dest + ":6363") as proxy: 
            print()
            print(f"{string_identifier}: Sending heartbeat to {ip_dest}")
            error = proxy.heartbeat(json.dumps({"student_name": student_name, "timestamp": timestamp, "ip_address": ip_address}))
            print(f"{string_identifier}: Sent heartbeat to {ip_dest}, server returned code {error}")
            return "Success"
    except Exception as e: 
        return e

def get_alphabetical_next_index_from_me(): 
    client_names = [client["student_name"] for client in client_list]
    after_me_alphabetically = [name for name in client_names if name > server_name]s
    closest = difflib.get_close_matches(server_name, after_me_alphabetically, 1)
    client_index = 0
    for i, client in enumerate(client_list): 
        if client["student_name"] == closest: 
            client_index = i
            break
    return client_index

def get_next_client_index(curr_index): 
    return (curr_index + 1) % len(client_list)

# client
def run_client(): 
    # choose who to ping based on who is live
    if len(client_list) > 1: 
        # assumes client list currently in order; every time a new client is added, it is put back in order
        my_position = next((index for (index, d) in enumerate(client_list) if d["student_name"] == "Charlotte"), None)
        if my_position is not None: 
            server_to_send_to = client_list[(my_position + 1) % len(client_list)]
            ip_addr_to_send = server_to_send_to["ip_address"]
    else: 
        if first_few_heartbeats: 
            ip_addr_to_send = start_server_to_ping
        else: 
            print("CLIENT: No one to send heartbeat to :(")
            send_heartbeat = False
    send_heartbeat = True
    while True: 
        print(f"\nRUNNING CLIENT")
        if num_heartbeats_sent < 3: 
            ip_addr_to_send_to = start_server_to_ping
            send_heartbeat = True
        else: 
            if len(client_list) > 1: 
                ip_addr_to_send_to = get_alphabetical_next_index_from_me()
                send_heartbeat = True
            else: 
                print(f"CLIENT: No one available to heartbeat to")
                send_heartbeat = False
        
        if send_heartbeat: 
            send_heartbeat_to_ip(ip_addr_to_send_to, "Charlotte", time.time(), server_ip_addr, "CLIENT")

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
    
    if abs(time.time() - timestamp) < 60:
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
            else: 
                client_list[client_index]["timestamp"] = timestamp
    else: 
        print(f"SERVER: Received invalid timestamp from {name} at {ip_addr} - {timestamp} was {abs(timestamp - time.time())} off")
    
    # go through client list and remove anything with a timestamp over 1 min old EXCEPT for my own client
    client_list = [client for client in client_list if abs(client["timestamp"] - time.time()) < 60]
    print(f"\nSERVER: New client list, old timestamps removed: {client_list}")

    # send info to next in chain
    next_index = get_alphabetical_next_index_from_me()
    next_item = client_list[next_index]
    if next_item["ip_address"] == ip_addr: 
        old_item = next_item
        next_index = get_next_client_index(next_index)
        next_item = client_list[next_index]
        print(f"SERVER: Skipping {old_item['student_name']} to go to {next_item['student_name']}")
    
    print(f"SERVER: forwarding {name} to {next_item['student_name']} (sending to IP: {next_item['ip_address']})")
    response = send_heartbeat_to_ip(next_item["ip_address"], name, timestamp, ip_addr, "SERVER")
    if response == "Success": 
        return 0
    return 1

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

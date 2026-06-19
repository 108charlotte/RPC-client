# https://docs.python.org/3/library/xmlrpc.html
import xmlrpc.client
import xmlrpc.server
import time
import json
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import threading

server_name = "Charlotte"
server_ip_addr = "141.165.50.133"

start_server_to_ping = "141.165.50.162"

client_list = [{"ip_address": server_ip_addr, "student_name": server_name, "timestamp": int(time.time())}] # put myself in client list
first_few_heartbeats = True

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

# client
def run_client(): 
    send_heartbeat = True
    # choose who to ping based on who is live
    if len(client_list) > 1: 
        # assumes client list currently in order; every time a new client is added, it is put back in order
        my_position = next((index for (index, d) in enumerate(client_list) if d["student_name"] == "Charlotte"), None)
        server_to_send_to = client_list[(my_position + 1) % len(client_list)]
        ip_addr_to_send = server_to_send_to["ip_address"]
    else: 
        if first_few_heartbeats: 
            ip_addr_to_send = start_server_to_ping
        else: 
            print("CLIENT: No one to send heartbeat to :(")
            send_heartbeat = False
    while send_heartbeat: 
        send_heartbeat_to_ip(ip_addr_to_send, "Charlotte", time.time(), server_ip_addr, "CLIENT")
        time.sleep(10) # 10 second sleep before sending another heartbeat ping

# server
def heartbeat(json_string): 
    global client_list
    context = json.loads(json_string)
    name = context["student_name"]
    timestamp = int(context["timestamp"])
    ip_addr = context["ip_address"]
    print()
    print(f"SERVER: Received heartbeat from name: {name}, timestamp: {timestamp}, ip_addr: {ip_addr}")
    
    if abs(time.time() - timestamp) < 60:
        print()
        print(f"SERVER: Timestamp {timestamp} valid for {name} at {ip_addr}")
        all_ip_addrs = [client["ip_address"] for client in client_list]
        # need to include timestamps and update
        if not ip_addr in all_ip_addrs: # ip address not already in list, then add to list along with name
            print(f"SERVER: IP address {ip_addr} not in client list")
            client_list.append({"ip_address": ip_addr, "student_name": name, "timestamp": timestamp})
            # sort: https://stackoverflow.com/questions/72899/how-can-i-sort-a-list-of-dictionaries-by-a-value-of-the-dictionary-in-python
            client_list = sorted(client_list, key=lambda d: d["student_name"])
            print(f"SERVER: Added {ip_addr} for {name} at {timestamp} to client_list")
            print(f"SERVER: {len(client_list)} people in client list: {client_list}")
            print()
        else: 
            # update timestamp of existing entry
            print(f"SERVER: Client exists in client list, updating client timestamp...")
            client_index = next((index for (index, d) in enumerate(client_list) if d["ip_address"] == ip_addr), None)
            if client_index is None: print(f"SERVER: BUG - client index not found in list")
            client_list[client_index]["timestamp"] = timestamp
    
    # go through client list and remove anything with a timestamp over 1 min old EXCEPT for my own client
    client_list = [client for client in client_list if abs(client["timestamp"] - time.time()) < 60 or client["student_name"] == "Charlotte"]
    print(f"SERVER: New client list, old timestamps removed: {client_list}")

    # send info to next in chain
    my_position = next((index for (index, d) in enumerate(client_list) if d["student_name"] == "Charlotte"), None)
    next_index = (my_position + 1) % len(client_list)
    next_item = client_list[next_index]
    if next_item["ip_address"] == ip_addr: 
        print(f"SERVER: Skipping {next_item['student_name']} to go to {client_list[(next_index + 1) % len(client_list)]['student_name']}")
        next_index = (next_index + 1) % len(client_list)
        next_item = client_list[next_index]
    
    print(f"SERVER: forwarding {name} to {next_item['student_name']} (sending to IP: {next_item['ip_address']})")
    error = send_heartbeat_to_ip(next_item["ip_address"], name, timestamp, ip_addr, "SERVER")
    if error == "Success": 
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

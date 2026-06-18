# https://docs.python.org/3/library/xmlrpc.html
import xmlrpc.client
import xmlrpc.server
import time
import json
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import threading

server_name = "Charlotte"
server_ip_addr = "141.165.50.133"

client_list = [{"ip_address": server_ip_addr, "student_name": server_name}] # put myself in client list
print(f"Client list: {client_list}")


# client
def run_client(): 
    with xmlrpc.client.ServerProxy("http://141.165.50.176:6363") as proxy: 
        while True: 
            error = proxy.heartbeat(json.dumps({"student_name": "Charlotte", "timestamp": int(time.time()), "ip_address": "141.165.50.133"}))
            print(f"Server returned code {error}")
            time.sleep(10) # 10 second sleep before sending another heartbeat ping

# server
# TODO: implement gossiping protocol: 
'''
- maintain client list (necessary for quorum) - all clients server has received heartbeats from
- when u get accepted heartbeat from someone else: send heartbeat to next node in the client list alphabetically to you in the list, loop back to beginning if @ end of alphabet
- toss if from yourself
- include ip_address in heartbeat
- include name in heartbeat payload
'''
def heartbeat(json_string): 
    global client_list
    print("RECEIVED HEARTBEAT")
    context = json.loads(json_string)
    name = context["student_name"]
    timestamp = context["timestamp"]
    ip_addr = context["ip_address"]
    print(f"Received name: {name}, timestamp: {timestamp}, ip_addr: {ip_addr}")
    print(f"Client list: {client_list}")
    
    if abs(time.time() - timestamp) < 60:
        print(f"received successful request from {name} at {timestamp}")
        all_ip_addrs = [client["ip_address"] for client in client_list]
        # need to include timestamps and update
        if not ip_addr in all_ip_addrs: # ip address not already in list, then add to list along with name
            print(f"IP address {ip_addr} not in client list")
            client_list.append({"ip_address": ip_addr, "student_name": name})
            # sort: https://stackoverflow.com/questions/72899/how-can-i-sort-a-list-of-dictionaries-by-a-value-of-the-dictionary-in-python
            client_list = sorted(client_list, key=lambda d: d["student_name"])
            print(f"Added {ip_addr} for {name} to client_list")
           
        # get index of name
        charlotte_index = next((index for (index, d) in enumerate(client_list) if d["student_name"] == "Charlotte"), None)
        # skip over node that heartbeat is from when u get next node alphabetically
        next_index = charlotte_index + 1 if charlotte_index >= len(client_list) else 0 # wrap around to beginning
        if client_list[next_index]["ip_address"] == ip_addr: 
            next_index = next_index + 1 if next_index >= len(client_list) else 0 # same as above, repetitive and should fix
        with xmlrpc.client.ServerProxy("http://" + client_list[next_index]["ip_address"] + ":6363") as proxy: 
            error = proxy.heartbeat(json.dumps({"student_name": name, "timestamp": timestamp, "ip_address": ip_addr}))
            print(f"Received {error} from {client_list[next_index]['ip_address']}")
        return 0
    return 1
            
def run_server(): 
    with SimpleXMLRPCServer(('141.165.50.133', 6363)) as server: 
        server.register_introspection_functions()
        print("SERVER ALIVE")
        server.register_function(heartbeat, "heartbeat")
        server.serve_forever()

# https://www.geeksforgeeks.org/python/multithreading-python-set-1/
client_thread = threading.Thread(target=run_client)
server_thread = threading.Thread(target=run_server)

client_thread.start()
server_thread.start()

client_thread.join()
server_thread.join()
# https://docs.python.org/3/library/xmlrpc.html
import xmlrpc.client
import time
import json

with xmlrpc.client.ServerProxy("http://141.165.50.132:6363") as proxy: 
    # print(proxy.system.listMethods())
    # help_message = proxy.system.methodHelp("heartbeat")
    # print(help_message)
    # call method
    # proxy.system.methodSignature("heartbeat")
    proxy.heartbeat(json.dumps({"student_name": "charlotte", "timestamp": int(time.time())}))
# server.system.listMethods()

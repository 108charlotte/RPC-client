# https://docs.python.org/3/library/xmlrpc.html
import xmlrpc.client
import time

with xmlrpc.client.ServerProxy("http://10.38.105.40", context={"student_name": "charlotte", "timestamp": time.time()}) as proxy: 
    print(proxy.system.listMethods())
    help_message = proxy.system.methodHelp("heartbeat")
    print(help_message)
    # call method
    # proxy.system.methodSignature("heartbeat")
    proxy.heartbeat()
# server.system.listMethods()
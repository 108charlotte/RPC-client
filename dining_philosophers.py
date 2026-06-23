import threading
import time
import random

# 5 philosopher threads and 5 forks
class Fork: 
    def __init__(self, name): 
        self.val = 0
        self.name = name
        self.lock = threading.Lock()

    def increase(self): 
        print(f"called increase, lock value is: {self.lock.locked()}")
        self.lock.acquire() 
        print(f"Locking, lock value is: {self.lock.locked()}")
        self.val += 1
        time.sleep(5)
        
        self.lock.release()
        time.sleep(2)
        print(f"Lock released + slept; lock value is: {self.lock.locked()}")

    def __str__(self): 
        return f"{self.name}: {self.val}"

philosophers = ["Joe", "Sarah", "Hanna", "Hi", "Charlotte"]

forks = [Fork("F1"), Fork("F2"), Fork("F3"), Fork("F4"), Fork("F5")]
# order relative to each other: F1 Joe F2 Sarah F3 Hannah F4 Hi F5 Charlotte

while True: 
    index = random.randint(0, len(philosophers)-1)
    fs = [forks[(index) % len(forks)], forks[(index - 1) % len(forks)]]
    f = random.choice(fs)
    print(f"Philosopher at {philosophers[index]} attempting to grab fork {str(f)}")
    fork_strings = ', '.join([str(fork) for fork in forks])
    print(f"Forks before philosopher action: {fork_strings}")
    # if already locked, should skip
    if not f.lock.locked(): # locked is false
        p = threading.Thread(target=f.increase)
        p.start()
    else: # if locked is true
        pass # print(f"Skipped fork bc of lock")
    print("------------------------------------------------------------------")

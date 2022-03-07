import os
import logging
from multiprocessing import Process
import time
import sys

class MULTIPROCESS(Process):
    def __init__(self, name, func, sleeptime):
        Process.__init__(self)
        self.name = name
        self.function = func
        self.sleeptime_sec = sleeptime
        print(self.args)

    def run(self):
        try:
            while True: 
                self.function(self.args)
                time.sleep(self.sleeptime_sec)
        except KeyboardInterrupt:
            #self.terminate()
            print("KeyboardInterrupted")
            #sys.exit(0)

#def workingfunction(self):
#    print("name:%s, argument:%s" % (self.name, self.count))
#    print("parent pid:%s, pid:%s" % (os.getppid(), os.getpid()))
#    print("")
#    self.count += 1
#    time.sleep(1)

#def main():
    #multiprocessing.log_to_stderr()
    #logger = multiprocessing.get_logger()
    #logger.setLevel(logging.DEBUG)

    #proc_visual_update = MultiProcessWorkerClass(name="visual_update", func=workingfunction, args=(0,))
    #proc_visual_update.start()

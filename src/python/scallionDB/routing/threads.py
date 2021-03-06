''' 
  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at
 
      http://www.apache.org/licenses/LICENSE-2.0
 
  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
 '''
 
import time
import zmq
import threading
import json
import traceback
import gc
import os
import shutil

from units import Worker, WorkerQueue, Message
from random import randint
from constants import *
from collections import Counter

from scallionDB.parser import parse_request
from scallionDB.core import evaluate, treebreaker

		
class BrokerThread(threading.Thread):

    def __init__(self, context, client_port, hi, hl, ewp, trees, 
	             saveCounter, saveLimit):
        super(BrokerThread, self).__init__()
        self.context = context
        self.client_port = str(client_port)
        self.BEAT_INTERVAL = hi
        self.BEAT_LIVENESS = hl
        self.EXPECTED_PERFORMANCE = ewp
        self.trees = trees
        self.saveCounter = saveCounter
        self.saveLimit = saveLimit

    def run(self):
	
        frontend = self.context.socket(zmq.ROUTER) # ROUTER
        backend = self.context.socket(zmq.ROUTER)  # ROUTER
        saveer = self.context.socket(zmq.DEALER)  # ROUTER
        frontend.bind("tcp://*:%s" %self.client_port) # For clients
        backend.bind("inproc://workers" )  # For workers
        saveer.bind("inproc://saveer" ) # For saveer
		
        frontend.setsockopt(zmq.LINGER, 0)
        backend.setsockopt(zmq.LINGER, 0)
        saveer.setsockopt(zmq.LINGER, 0)
		 
        poller = zmq.Poller()
        poller.register(frontend, zmq.POLLIN)
        poller.register(backend, zmq.POLLIN)
        poller.register(saveer, zmq.POLLIN)
        
        workers = WorkerQueue()
        mq = [] #non FIFO queue
        readTrees = []   
        writeTrees = set()
        heartbeat_at = time.time() + self.BEAT_INTERVAL
        
        while True:
            socks = dict(poller.poll(self.BEAT_INTERVAL * 1000))
            # Handle worker activity on backend
            if socks.get(backend) == zmq.POLLIN:
                # Use worker address for LRU routing
                frames = backend.recv_multipart()
                msg_type = frames[3]
                if msg_type != SDB_COMPLETE:
                    if msg_type == SDB_MESSAGE:
                        frontend.send_multipart(frames[1:])
                    elif msg_type == SDB_FAILURE:
                        tree = frames.pop()
                        readTrees.remove(tree)
                        if tree in writeTrees:
                            writeTrees.remove(tree)
                        frontend.send_multipart(frames[1:])
                    else:
                        address = frames[0]
                        workers.ready(Worker(address,self.EXPECTED_PERFORMANCE, 
					                         self.BEAT_LIVENESS))
       
                else:
                    tree = frames.pop()
                    frontend.send_multipart(frames[1:])
                    if tree in writeTrees:
                        if tree not in self.trees:
                            del self.saveCounter[tree]
                            readTrees.remove(tree)
                            writeTrees.remove(tree)                             
                        else:
                            self.saveCounter[tree] += 1
                            if self.saveCounter[tree] >= self.saveLimit:
                                frames[-1] = tree
                                saveer.send_multipart(frames)
                            else:
                                readTrees.remove(tree)
                                writeTrees.remove(tree)
                    else:
                        readTrees.remove(tree)

        
                # Send heartbeats to idle workers if it's time
                if time.time() >= heartbeat_at:
                    for worker in workers:
                        msg = [worker, SDB_HEARTBEAT]
                        backend.send_multipart(msg)
                    heartbeat_at = time.time() + self.BEAT_INTERVAL
        			
            #Work with existing queue first
            t = time.time()
            remove = []
            for msg in mq:
                if t > msg.expiry:
                    msg.frames[-1] = SDB_TIMEOUT
                    msg.frames.append("Resources busy")
                    frontend.send_multipart(msg.frames)
                    remove.append(msg)
                else:
                    if len(workers) > 0:
                        if msg.type == 'write':                     
                            if msg.tree not in readTrees:
                                writeTrees.add(msg.tree)
                            else:
                                continue
                        else:
                            if msg.tree in writeTrees:
                                continue							
                        readTrees.append(msg.tree)
                        msg.frames.insert(0,workers.next())

                        backend.send_multipart(msg.frames)
                        remove.append(msg)						
            for r in remove:
                mq.remove(r)   			
        			
            if socks.get(frontend) == zmq.POLLIN:
        	           			
                frames = frontend.recv_multipart()
                if len(frames) == 4:
                    timeout = int(frames.pop())*1e-3 - (self.EXPECTED_PERFORMANCE * 
        			                                    self.BEAT_LIVENESS) + time.time()
                else:
                    timeout = self.EXPECTED_PERFORMANCE + time.time()
                if timeout < 0:
                    frames[-1] = SDB_TIMEOUT
                    frames.append("Expected Timeout computed")
                    frontend.send_multipart(frames)                      
                else:
                    try:
                        parsed = parse_request(frames[-1])
                        type, tree = parsed['type'], parsed['tree']
                    except:
                        frames[-1] = SDB_FAILURE
                        frames.append(traceback.format_exc())
                        frontend.send_multipart(frames)
                        continue						
                    if not tree:
                        frames[-1] = SDB_NONTREE # for show statement
                        frames.append(json.dumps(self.trees.keys()))
                        frontend.send_multipart(frames)
                        continue
                    if len(workers) > 0:
                        if type == 'write':                     
                            if tree not in readTrees:
                                frames.insert(0, workers.next())
                                backend.send_multipart(frames)
                                writeTrees.add(tree)
                                readTrees.append(tree)
                            else:
                                msg = Message(frames, tree, timeout, type)
                                mq.append(msg)
                        else:
                            if tree in writeTrees:
                                msg = Message(frames, tree, timeout, type)
                                mq.append(msg)	
                            else:
                                readTrees.append(tree)
                                frames.insert(0, workers.next())
                                backend.send_multipart(frames)							
                    else:         
                        msg = Message(frames, tree, timeout, type)
                        mq.append(msg)
						
            if socks.get(saveer) == zmq.POLLIN: 
                frames = saveer.recv_multipart()
                treename = frames[-1]                              
                readTrees.remove(tree)
                writeTrees.remove(tree)        
                self.saveCounter[tree] = 0
            workers.purge()
			
class WorkerThread(threading.Thread):

    def __init__(self, context, hi, hl, interval, interval_max,
                	trees, chunksize, folder, commlog, errlog):
        super(WorkerThread, self).__init__()
        self.context = context
        self.BEAT_INTERVAL = hi
        self.BEAT_LIVENESS = hl
        self.INTERVAL_INIT = interval
        self.INTERVAL_MAX = interval_max
		
        self.worker = context.socket(zmq.DEALER) 	
        self.identity = "%04X-%04X" % (randint(0, 0x10000), randint(0, 0x10000))
        self.worker.setsockopt(zmq.IDENTITY, self.identity)
        self.worker.setsockopt(zmq.LINGER, 0)
        self.worker.connect("inproc://workers")
		
        self.poller = zmq.Poller()
        self.poller.register(self.worker, zmq.POLLIN)
		
        self.trees = trees
        self.chunksize = chunksize
        self.folder = folder
        self.commlog = commlog
        self.errlog = errlog
	 		
    def run(self):
        sdb_message = ['','',SDB_READY]
        self.worker.send_multipart(sdb_message)   
        liveness = self.BEAT_LIVENESS
        interval = self.INTERVAL_INIT
        
        heartbeat_at = time.time() + self.BEAT_INTERVAL

        cycles = 0
        while True:
            socks = dict(self.poller.poll(self.BEAT_INTERVAL * 1000))
        
            # Handle worker activity on backend
            if socks.get(self.worker) == zmq.POLLIN:
                #  Get message
                #  - 3+-part envelope + content -> request
                #  - 1-part HEARTBEAT -> heartbeat
                frames = self.worker.recv_multipart()
                if len(frames) == 3:
                    request = frames[-1]
                    parsed = parse_request(request)
                    type, tree = parsed['type'], parsed['tree']
                    frames.insert(2,SDB_MESSAGE)
                    try:
                        output = evaluate(self.trees,parsed,self.folder)
                        if isinstance(output, list):
                            if parsed['request'] == 'GET':
                                frames[-1] = '['
                                self.worker.send_multipart(frames)  
                                get = ''
                                for out in output:
                                    breaker = treebreaker(out)
                                    while True:
                                        if len(get) > self.chunksize:
                                            frames[-1] = get
                                            self.worker.send_multipart(frames)
                                            get = ''
                                            time.sleep(0.1)
                                        try:
                                            get += breaker.next()		
                                        except StopIteration:
                                            break
                                    frames[-1] = get
                                    self.worker.send_multipart(frames)
                                    get = ','	
                                frames[-1] = ']'
                                self.worker.send_multipart(frames)        									
                            else:
                                output = json.dumps(output)
                                frames[-1] = output
                                self.worker.send_multipart(frames)
                        else:
                            frames[-1] = output
                            self.worker.send_multipart(frames)
                        frames[-2] = SDB_COMPLETE
                        frames[-1] = tree
                        self.worker.send_multipart(frames)
                        del output
                        gc.collect()
                        self.commlog.info(request.replace('\n',' '))
                    except:
                        err = traceback.format_exc()
                        frames[-2] = SDB_FAILURE
                        frames[-1] = err
                        frames.append(tree)
                        self.worker.send_multipart(frames)
                        self.errlog.error(request.replace('\n',' '))						
     
                    liveness = self.BEAT_LIVENESS
                elif len(frames) == 1 and frames[0] == SDB_HEARTBEAT:
                    liveness = self.BEAT_LIVENESS
                interval = self.INTERVAL_INIT
            else:
                liveness -= 1
                liveness = max(liveness, 0)
                if liveness == 0:
                    self.errlog.warn("W: Heartbeat failure, can't reach queue.\
                     Reconnecting in %0.2fs..." % interval)
                    time.sleep(interval)
        
                    if interval < self.INTERVAL_MAX:
                        interval *= 2
                    else:
                        break
            if time.time() > heartbeat_at:
                heartbeat_at = time.time() + self.BEAT_INTERVAL
                hb_message = ['','',SDB_HEARTBEAT]
                self.worker.send_multipart(hb_message)
	
class SaverThread(threading.Thread):

    def __init__(self, context, trees, saveCounter, folder, fllog, errlog):
        super(SaverThread, self).__init__()
        self.context = context
        self.saveCounter = saveCounter
        self.trees = trees	
        self.folder = folder
		
        self.saveer = context.socket(zmq.DEALER) 	
        self.identity = "%04X-%04X" % (randint(0, 0x10000), randint(0, 0x10000))
        self.saveer.setsockopt(zmq.IDENTITY, self.identity)
        self.saveer.setsockopt(zmq.LINGER, 0)
        self.saveer.connect("inproc://saveer")
        self.poller = zmq.Poller()
        self.poller.register(self.saveer, zmq.POLLIN)
		
        self.fllog = fllog
        self.errlog = errlog
			
    def run(self):
        while True:
            socks = dict(self.poller.poll(500))   
            # Handle saveing activity 
            if socks.get(self.saveer) == zmq.POLLIN:
                frames = self.saveer.recv_multipart()
                treename = frames[-1]
                filename = os.path.join(self.folder, treename+'.tmp')
                try:
                    self.trees[treename].dump(filename)
                    newname = os.path.join(self.folder, treename+'.tree')
                    shutil.move(filename, newname)
                    self.fllog.info("Flushed tree %s successfully" %treename)
                except:
                    self.errlog.error("Flushing tree %s failed" %treename)               
                self.saveer.send_multipart(frames)
				
class LoaderThread(threading.Thread):

    def __init__(self, context, port, folder, conlogger):
        super(LoaderThread, self).__init__()
        self.context = context
        self.folder = folder
		
        self.loader = context.socket(zmq.DEALER) 	
        self.identity = "%04X-%04X" % (randint(0, 0x10000), randint(0, 0x10000))
        self.loader.setsockopt(zmq.IDENTITY, self.identity)
        self.loader.setsockopt(zmq.LINGER, 0)
        self.loader.connect("tcp://localhost:%s" %port)
        self.poller = zmq.Poller()
        self.poller.register(self.loader, zmq.POLLIN)
        self.logger = conlogger
		
	
    def run(self): 
        i = 0 
        j = 0
        sent = False
        while True:
            if not sent:
                for file in os.listdir(self.folder):
                    if file.endswith('.tree'):
                        treename = file.split('.tree')[0]
                        frames = [''," ".join(['LOAD', treename, 
		        		          os.path.join(self.folder, file)]),'1000000']
                        self.loader.send_multipart(frames)
                        i += 1
            if i == 0:
                self.logger.info("No existing trees to load")
            sent = True
            socks = dict(self.poller.poll(500)) 
            if socks.get(self.loader) == zmq.POLLIN:
                frames = self.loader.recv_multipart()
                if len(frames) == 3:
                    if frames[-2] != SDB_FAILURE:
                        self.logger.info("Loaded %d of %d TREE '%s' successfully" 
					                 %(j+1,i,frames[-1]))
                        j += 1
                    else:
                        self.logger.error(frames[-1])
            if j == i:
                return			

                
                				
		

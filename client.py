import socket
import sys
import json
import time
from threading import Thread


#Global config variable declaration with sane defaults
TCP_IP = '127.0.0.1'
TCP_PORT = 5555
BUFFER_SIZE = 100  # Usually 1024, but we need quick response
REPLY_DELAY = 7 #Send reply after waiting for 5 seconds. This could allow concurrent requests
REQUEST_DELAY = 10 #Send request after waiting for 5 seconds. This could allow concurrent requests
TOTAL_CLIENTS = 1
SEND_IT=False;
#Create a reply count dict with client numbers as tuple (reply_count, client count at that point)
#Set this client count when local request is made.
#Lamport protocol does NOT handle process failures so assume system is reliable and processes
#do not disconnect mid way. Assume you know number of clients before hand.
with open('config.json') as data_file:    
    data = json.load(data_file)
    TCP_IP = data['tcp_ip']
    TCP_PORT = data['tcp_port']
    REPLY_DELAY = data['reply_delay']
    REQUEST_DELAY = data['request_delay']
    TOTAL_CLIENTS = data['total_clients']



class Client:

    # Class for starting up a client

    def event_compare(self, x, y):
        # x is process Id and y is lamport clock
        # this method returns array sorted in ascending order
        if (x['key'][1] < y['key'][1]) or (x['key'][1] == y['key'][1] and x['key'][0] < y['key'][0]):
            return -1
        elif (x['key'][1] > y['key'][1]) or (x['key'][1] == y['key'][1] and x['key'][0] > y['key'][0]):
            return 1
        else:
            return 0

    def total_order(self):
        #Order events by event times and break ties using process Ids
        #Custom comparator defined in event_compare method
        self.queue = sorted(self.queue,cmp=self.event_compare)
        print 'Local queue after total ordering'
        print self.queue

    def __init__(self, id):
        self.id = id
        self.queue = []
        self.client_count = TOTAL_CLIENTS
        self.event_count = 0
        self.like_count = 0
        self.request_hash = {}
        self.send_state = 'request'
        self.send_queue = []
        self.tcpClient = socket.socket(socket.AF_INET,
                socket.SOCK_STREAM)
        try:
            self.tcpClient.connect((TCP_IP, TCP_PORT))
        except:
            print 'Unable to connect'
            sys.exit()
        self.setup()

    def setup(self):
        print 'You are in ! Send some Message!'
        sys.stdout.write('[Me] ')
        sys.stdout.flush()
        recv_thread = Thread(target=self.receivedata)
        recv_thread.setDaemon(True)
        recv_thread.start()
        send_thread = Thread(target=self.sendreplies)
        send_thread.setDaemon(True)
        send_thread.start()
        self.senddata()

    def access_resource(self):
        #This function would define the access resource method
        #Remove from local Queue
        removed_req = self.queue.pop(0)
        #Remove from request Hash
        #Key in hash is string so typecast
        self.request_hash.pop(str(removed_req['key'][1]))
        #Execute the corresponding event
        print 'Access resource called'
        #Once access is done.
        #Send release message to all clients
        #self.like_count += int(removed_req['msg'])       
        send_message = json.dumps({'id': self.id, 'type': 'critical_section',
        'msg': removed_req['msg'],'lamport': self.event_count})
        self.tcpClient.send(send_message)
        self.event_count += 1

    def release_resource(self,req):
        #Update like count from server response
        self.like_count = int(req['msg'])
        print 'Number of likes: '+str(self.like_count)
        print 'Now I am releasing the resource'
        send_message = json.dumps({'id': self.id, 'type': 'release',
        'msg': str(self.like_count), 'to': 'all', 'lamport': self.event_count})
        self.tcpClient.send(send_message)
        self.event_count += 1
        

    def accept_release(self,req):
        print 'Need to accept release now'
        #Remove from local Queue
        #Since this request would be at the head. Remove head.
        del self.queue[0]
        print 'Removed from local queue. State of local queue now. '
        print self.queue
        #Update the local number of likes sent along the release message
        num_likes = int(req['msg'])
        self.like_count = num_likes
        print 'Number of likes: '+str(self.like_count)
        #Assuming the queues are totally ordered and identical. I can just remove the head & be done with it
        #Things will get complicated if we consider dynamic processes that can join later
        #Consider that num of processes are fixed and we know total number of clients before hand
        #Also ensure that the clients disconnect gracefully as edge cases are not handled yet
        
        #Check if current head request is local and can go to critical section
        #Only if queue is not empty. Otherwise chill
        if len(self.queue) > 0:
            self.is_allowed()

    
    def send_all_replies(self):
        print 'Send all replies function called'
        print 'Send queue right now '
        print self.send_queue
        global SEND_IT
        SEND_IT=True;
        for repl in self.send_queue:
            print 'Need to send reply now to process '+str(repl[0])+' and event id '+str(repl[1])
            send_message = json.dumps({'id': self.id, 'type': 'reply',
        'msg': str(repl[1]), 'to': str(repl[0]), 'lamport': self.event_count})
            print "my sending message in reply.." + str(send_message)
            self.tcpClient.send(send_message)
            self.event_count += 1
            time.sleep(1)
        self.send_queue = []
        self.send_state = 'request'


    def send_reply(self,to_id,to_lamport):
        #Because I need to reply w.r.t to a particular event to a process. I set msg as event ID
        print 'Need to send reply now to process '+str(to_id)+' and event id '+str(to_lamport)
        sys.stdout.write('3\n')
        send_message = json.dumps({'id': self.id, 'type': 'reply',
        'msg': str(to_lamport), 'to': str(to_id), 'lamport': self.event_count})
        #Delay the reply by some time. This could allow receiving concurrent requests
        time.sleep(REPLY_DELAY)
        self.tcpClient.send(send_message)
        self.event_count += 1

    def is_allowed(self):
        #Check if the request at head of queue is local and has all replies
        #If yes, goes to critical section and sends replies
        #Need to parse event_id to int first coz key is (proc_id :: string,event_id :: int)
        first_req = self.queue[0]['key'] #Gets key of first req (proc_id,event_id)
        first_event = first_req[1]

        if str(first_event) in self.request_hash and self.request_hash[str(first_event)] == 0 and first_req[0] == self.id:
            #Request at head of queue and no other replies need
            print 'I can go to critical section now!'
            self.access_resource()

    def accept_reply(self,req):
        print 'Need to accept reply now'
        #Maintain reply counts some where
        #Receive resource if at head of queue
        #For reply messages msg attr would have lamport clock of process
        event_id = req['msg']
        print 'Request hash before and event id is '+event_id
        print self.request_hash
        self.request_hash[event_id] -= 1
        print 'Request hash after'
        print self.request_hash
        #time.sleep(REQUEST_DELAY)
        self.is_allowed()
        self.event_count += 1

    def accept_request(self,req):
        global SEND_IT
        print 'Need to accept request now'
        self.queue.append({'key': (req['id'],req['lamport']),'msg':req['msg']})
        #Order the FIFO Chanell
        self.total_order()
        print 'State of local queue right now..'
        print self.queue
        print 'Will have to send an ack here'
        self.send_state = 'reply'
        self.send_queue.append((req['id'],req['lamport']))
        self.event_count += 1
        print 'Send state set by accept request function : '+self.send_state

    def send_request(self,msg):
        print 'Need to send request now'
        #Append to local queue and increment local queue        
        self.queue.append({'key': (self.id,self.event_count),'msg':msg})
        #Order the FIFO Chanell
        self.total_order()
        print 'State of local queue right now..'
        print self.queue
        #Also add event to request hash
        #Total client counts right now
        print 'Total clients right now '+str(self.client_count)
        #Coerce the key to a string here! Important
        #Set an entry in request hash. 
        #This would serve as the counter of replies for a particular request. 
        #Each process would expect n-1 replies if there are n processes
        self.request_hash[str(self.event_count)] = self.client_count - 1
        print 'Request hash'
        print self.request_hash
        #Now send the message after delay
        send_message = json.dumps({'id': self.id, 'type': 'request',
        'msg': msg, 'to': 'all', 'lamport': self.event_count})
        time.sleep(REQUEST_DELAY)
        self.tcpClient.send(send_message)
        self.event_count += 1

    def receivedata(self):
        while 1 == 1:
            data =  self.tcpClient.recv(1024)
            if data:
                #print data
                decoded_data = json.loads(data)
                data = decoded_data['msg']
                request_type = decoded_data['type']
                if request_type == 'connect':
                    #Broadcasted a connect. Somebody connected. update number of clients
                    print 'Some client has joined'
                    #self.client_count += 1
                elif request_type == 'request':
                    print 'Got request from '+decoded_data['id']
                    self.accept_request(decoded_data)
                elif request_type == 'reply':
                    print 'Got reply from '+decoded_data['id']
                    self.accept_reply(decoded_data)
                elif request_type == 'release':
                    print 'Got to accept release from '+decoded_data['id']
                    self.accept_release(decoded_data)
                elif request_type == 'critical_section':
                    print 'Got to release held by '+decoded_data['id']
                    self.release_resource(decoded_data)
                #print 'I got a message from server'+data

    def sendreplies(self):
        global SEND_IT
        lock = False
        while 1==1:
            if self.send_state == 'reply':
                if SEND_IT == False and lock == False:
                    time.sleep(REPLY_DELAY)
                    lock = True
                    self.send_all_replies()
                    lock = False
                    SEND_IT = False


    def senddata(self):
        #Send the connect request first.
        welcome_message = json.dumps({'id': self.id, 'type': 'connect',
                'msg': 'hola', 'to': 'all'})
        self.tcpClient.send(welcome_message)
        while 1==1:
            #time.sleep(1)
            msg = sys.stdin.readline()
            msg = msg[:-1]  # omitting the newline
            if msg == 'exit':
                break
            if msg != '':
                self.send_request(msg)

            sys.stdout.write('[Me] ')
            sys.stdout.flush()
        #Out of while loop implies process wants to exit. Gracefully shut down
        self.tcpClient.send(json.dumps({'id':self.id,'type':'exit','msg':''}))

tcp_instance = Client(' '.join(sys.argv[1:]))
tcp_instance.tcpClient.close()


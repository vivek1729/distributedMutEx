#!/usr/bin/python
# -*- coding: utf-8 -*-

import socket
import json
from threading import Thread
import logging
import sys
import curses
import curses.textpad

#Global config variable declaration with sane defaults
host = 'localhost'
port = 5555


with open('config.json') as data_file:    
    data = json.load(data_file)
    host = data['tcp_ip']
    port = data['tcp_port']

logger= logging.getLogger(__name__)
logger.setLevel(logging.INFO)


#creating logger file
handler=logging.FileHandler('application.log')
handler.setLevel(logging.INFO)


formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)

clientDic={}
threads = []
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverSocket.bind((host, port))
logger.info('Application Connected at host '+ str(host) +' and at port '+ str(port))
serverSocket.listen(10)
likeCount=0;
        
class ClientThread(Thread):

    def __init__(self,ip,port,conn): 
        Thread.__init__(self) 
        self.ip = ip 
        self.port = port
        self.conn = conn
        print "[+] New server socket thread started for " + ip + ":" + str(port)
        logger.info('New Client\'s thread started')

    def run(self): 
            self.messagePassing();

    def sendAll(self):
        #print 'Server has started..Waiting for connections'
        for clientId in clientDic:
            if clientId != self.id:
                clientDic[clientId].send(self.received_data)

    def messagePassing(self):
    #print "Staring thread for client"
        #print "I am here too"
        logger.info('I have entered message passing')
        while True:
            try:
                self.received_data = self.conn.recv(2048)
                self.received_data_Json=json.loads(self.received_data)
                if(self.conn in clientDic.values()) :
                   logger.info(self.id+': an old client is sending message')
                   #print 'Old client sending message'
                else:
                    clientDic[self.received_data_Json['id']]=self.conn;
                    logger.info('It is a new Client !! Yippee !! ' + self.received_data_Json['id'] )  
                    #print 'Connected To ', self.received_data_Json['id']
                #print self.received_data
                self.received_data_Json=json.loads(self.received_data)
                self.id = self.received_data_Json['id']
                data=self.received_data_Json['msg']
                request_type=self.received_data_Json['type']

                if 'to' in self.received_data_Json:
                    receviers=self.received_data_Json['to']
                else:
                    receviers=None
                #Handling critical Section stuff
                if request_type == 'critical_section':
                    logger.info(self.id+' has entered Critical Section')
                    global likeCount
                    #Update likeCount in response and send it back
                    likeCount=likeCount+int(data);
                    print('Like Count Current : '+ str(likeCount))
                    self.received_data_Json['msg'] = str(likeCount)
                    self.conn.send(json.dumps(self.received_data_Json))

                if receviers == 'all' :
                    self.sendAll()
                elif receviers is not None:
                    clientDic[receviers].send(self.received_data)

            except Exception as e:
                print e
                print "Some Exception"
                break;
                self.conn.close()
                serverSocket.close()

def listenNewClients():
    while True:
        try:
            #print 'Server has started..Waiting for connection'
            (conn, (ip,port)) = serverSocket.accept()
        

            newthread = ClientThread(ip,port,conn)
            threads.append(newthread)
            newthread.start()
           
            #conn.settimeout(60)
        except:
                print 'Some problem !'
                conn.close()
                serverSocket.close()
                break;
def postApplication():
    
    #stdscr = curses.initscr()
    #stdscr.addstr("Diwali is an awesome festival \n" + str(likeCount));
    #stdscr.getch();
    #curses.endwin();
    
    sys.stdout.write('Diwali is an awesome festival \n')
    sys.stdout.write('Like Count' + str(likeCount) + '\n')
    
if __name__== "__main__" :
    postApplication()
    
    masterThread = Thread(target=listenNewClients)
    masterThread.start()
    threads.append(masterThread)
    
    for thread in threads:  # iterates over the threads
        thread.join()



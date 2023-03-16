#!/usr/bin/env python3

import threading
from datetime import datetime
#import re
import socket
from queue import Queue
from time import sleep

config = {
	'maxclients': 100,
	'maxpacketlen': 4096,
	'clientidle': 100,
	'listenport': 8423,
	'maxmessage' : 100,
	'rcv_status' : "",
	'snd_status' : "",
}

q=Queue(config['maxmessage'])

def send_udp():
	CLIENT_LIST = {}
	sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	while True:
		try:
			msg=q.get()
		except Exception as e:
			print("get queue error : {}\n".format(e))
		else:
			if msg[2][0:4].decode() == "NRL2" :
				packet_len, send_id, recv_id = (int.from_bytes(msg[2][4:6], byteorder='little', signed=False), msg[2][6:13].hex(), msg[2][13:20].hex())
				print("len={}, send={}, recv={}".format(packet_len, send_id, recv_id))
				CLIENT_LIST[send_id]=(msg[0], msg[1], int(datetime.now().timestamp()) )		#由系统自动判断是否已经有send_id，有就更新存活时间，没有就自动添加
				if recv_id in CLIENT_LIST :
					if int(datetime.now().timestamp()) - CLIENT_LIST[recv_id][2] <= config['clientidle']:
						try:
							sock.sendto(msg[2], (CLIENT_LIST[recv_id][0], CLIENT_LIST[recv_id][1]))
#							print("sended msg {} to {}:{}\n".format(msg, CLIENT_LIST[recv_id][0], CLIENT_LIST[recv_id],[1]))
						except Exception as e :
							print("send msg error : {}\n".format(e))
					else :
						del CLIENT_LIST[recv_id]
						print("delete client : {}, remain clients : {}".format(recv_id, len(CLIENT_LIST)))
			elif msg[2][0:4].decode() == "UDP2" :    #此功能未完成
				print("%s:%d Command %s" % (msg[0], msg[1], msg[2].decode()))
				if msg[2][4:].upper() == "CLIENTS" :
					sock.sendto("Clients %d, %s" % (len(CLIENT_LIST),CLIENT_LIST), (msg[0], msg[1]))
				elif msg[2][4:].upper() == "THREADS" :
					sock.sendto("rcv : %s, snd : %s " % (config["rcv_status"].isAlive(), config["snd_status"].isAlive),(msg[0], msg[1]))
	sock.close()

def recv_udp() :
	"""
	receive udp packet from client, markdown IP,port,iden,packet
	each message format is : 
		NRL2  4 byte 固定的 "NRL2"
		XX    2 byte 包长度 
		CPUID 7 byte 发送设备序列号
		CPUID 7 byte 接收设备序列号
	"""
	try:
		mSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		mSocket.bind(("",config['listenport'])) 
	except Exception as e:
		print("bind {} error {}".format(str(config['listenport']),e))
		return False
	print("Listening for UDP on port {}.\n".format( str(config['listenport'])))
	while True:
		msgContent, (remoteHost, remotePort) = mSocket.recvfrom(1024)
		msg=[remoteHost,remotePort,msgContent]
		print("msg : {}".format(msg))
		if msgContent[0:4].decode() in ("NRL2", "UDP2") :
			try:
				q.put(msg,block=False)
			except Exception as e:
				print("put msg to queue error : {}\n".format(e))
		else:
			print("Invalid msg")

if __name__ == '__main__':
	config["rcv_status"] = threading.Thread(target=recv_udp,name='recv_udp')
	config["snd_status"] = threading.Thread(target=send_udp,name='send_udp')

	while True:   #线程自动重启功能未完成
		if not config["rcv_status"].isAlive():
			config["rcv_status"].start()
			print("Start recv_udp thread : {}\n".format(str(datetime.now())))
		if not config["snd_status"].isAlive():
			config["snd_status"].start()
			print("Start send_udp thread : {}\n".format(str(datetime.now())))
		sleep(60)

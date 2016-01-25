import argparse
import socket
import argparse
import threading
import time
from gamestate import gamestate
"""
Some socket code taken from https://docs.python.org/2/howto/sockets.html, authored by Gordon McMillan."
"""

class web_agent:
	"""
	Provide an interface to a socket connected to a Khex agent 
	which looks like an ordinary Khex agent.
	"""
	def __init__(self, client):
		self.client = client
		self.name = self.sendCommand("name")

	def sendCommand(self, command):
		totalsent = 0
		while totalsent < len(command):
			sent = self.client.send(command[totalsent:])
			if sent == 0:
				raise RuntimeError("client disconnected")
			totalsent += sent
		chunks = []
        bytes_recd = 0
        while 1:
            chunk = self.client.recv(2048)
            if chunk == '':
                raise RuntimeError("client disconnected")
            chunks.append(chunk)
            if(chunk[-1]!='\n'):
            	break
        return ''.join(chunks)

def make_valid_move(game, agent, color):
	move = agent.sendCommand("genmove "+color)
	while(True):
		if(game.cell_color(move_to_cell(move))==game.PLAYERS["none"]):
			agent.sendCommand("valid")
			game.play(move_to_cell(move))
			break
		else:
			move = agent.sendCommand("occupied")

class moveThread(threading.Thread):
	def __init__(self, game, agent, color):
		threading.Thread.__init__(self)
		self.game = game
		self.agent = agent
		self.color = color
	def run(self):
		make_valid_move(self.game, self.agent, self.color)


def move_to_cell(move):
	x =	ord(move[0].lower())-ord('a')
	y = int(move[1:])-1
	return (x,y)

def run_game(blackAgent, whiteAgent, boardsize, time):
	game = gamestate(boardsize)
	winner = None
	timeout = False
	while(True):
		t = moveThread(game, blackAgent, "black")
		t.start()
		t.join(time+0.5)
		#if black times out white wins
		if(t.isAlive()):
			timeout = True
			winner = game.PLAYERS["white"]
			break
		if(game.winner() != game.PLAYERS["none"]):
			winner = game.winner()
			break
		t = moveThread(game, whiteAgent, "white")
		t.start()
		t.join(time+0.5)
		#if white times out black wins
		if(t.isAlive()):
			timeout = True
			winner = game.PLAYERS["black"]
			break
		if(game.winner() != game.PLAYERS["none"]):
			winner = game.winner()
			break
	winner_name = blackAgent.name if winner == game.PLAYERS["white"] else whiteAgent.name
	print("Game over, " + winner_name+ " ("+game.PLAYER_STR[winner]+") " + "wins" + (" by timeout." if timeout else "."))
	print(game)
	return winner

parser = argparse.ArgumentParser(description="Server for running a tournament between several Khex clients.")
parser.add_argument("num_clients", type=int, help="number of agents in tournament.")
parser.add_argument("num_games", type=int, help="number of *pairs* of games (one as black, one as white) to play between each pair of agents.")
parser.add_argument("--boardsize", "-b", type=int, help="side length of (square) board.")
parser.add_argument("--time", "-t", type=int, help="total time allowed for each move in seconds.")
args = parser.parse_args()

if args.boardsize:
	boardsize = args.boardsize
else:
	boardsize = 11

if args.time:
	time = args.time
else:
	time = 10

num_clients = args.num_clients
num_games = args.num_games

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

port = 1235
address = socket.gethostname()
serversocket.bind((address, port))

clients=[]

serversocket.listen(5)
print("server address: "+str(socket.gethostname())+":"+str(port))

while len(clients)<num_clients:
    (clientsocket, address) = serversocket.accept()
    clients.append(web_agent(clientsocket))

#win_stats[client_1][client_2] = (number of client_1 wins as black against client_2, number of client_1 losses as black against client_2)
win_stats = {}
for client_1 in clients:
		for client_2 in clients:
			if(client_1!=client_2):
				if !win_stats[client_1.name]:
					win_stats[client_1.name] = {}
				win_stats[client_1.name][client_2.name] = (0,0)


for game in range(num_games):
	for client_1 in clients:
		for client_2 in clients:
			if(client_1!=client_2):
				winner = run_game(client_1, client_2, boardsize, time)
				if(winner == gamestate.PLAYERS["black"]):
					win_stats[client_1.name][client_2.name][0]+=1
				else
					win_stats[client_1.name][client_2.name][1]+=1

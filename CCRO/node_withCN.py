import aiohttp
from aiohttp import web
import sys
from datetime import datetime
from CCRO import PBFTAggregator
import random

class Node:
    def __init__(self, port, loop, nodes, corrupt=False, commander=False, communication=False):
        if communication:
            assert isinstance(nodes, list)
            self.nodes = list(nodes)
        else:
            assert isinstance(nodes, int)
            self.nodes = nodes
        
        self.port = port
        self.loop = loop 
        self.app = web.Application()
        self.app.add_routes([web.get('/status', self.status),
                             web.post('/preprepare', self.pre_prepare),
                             web.post('/prepare', self.prepare),
                             web.post('/commit', self.commit),
                             web.post('/reply', self.reply)])
        self.handler = self.app.make_handler()
        self.corrupt = corrupt
        self.commander = commander 
        self.communication = communication
        if(communication):
            self.message_log = {}
        
        self.id = self.port - 8080
        self.session = aiohttp.ClientSession()
        
    async def status(self, request):
        return web.json_response(f'Node {self.id} Up and Running')
    
    async def pre_prepare(self, request):
        if(self.communication):
            message = await request.json()
            fake_message = {"data" : "Currupt"}
            random_node = -1
            if(self.corrupt):
                random_node(int(random.choice(self.nodes)))
                
            print(f"\nStarting PBFT Consensus at {datetime.now()}")
            start_time = datetime.now()
            for i in self.nodes :
                if i == random_node:
                    try:
                        async with self.session.post(f'http://localhost:{8080 + i}/prepare', json=fake_message) as response:
                            pass
                    except Exception as e:
                        pass
                else:
                    try:
                        async with self.session.post(f'http://localhost:{8080 + i}/prepare', json=message) as response:
                            pass
                    except Exception as e:
                        pass
            end_time = datetime.now()
                  
            execution_time = (end_time - start_time).total_seconds()
            print(f"\n\nPBFT Consensus Time: {execution_time}s")
            PBFTAggregator.checkReplies()
            PBFTAggregator.resetReplies(len(self.nodes) + 1)
            return web.Response(text=f'\nPBFT Consensus Time: {execution_time}s\n')
        else:
            return web.HTTPUnauthorized()
      
    
    async def prepare(self, request):
        if(self.communication == False):
            message = await request.json()
            if self.corrupt:
                message["data"] = "Corrupt"
            try:
                await self.session.post(f'http://localhost:{8080 + self.nodes}/commit', json=message)
            except Exception as e:
                pass
        else:
            for i in range(len(self.nodes)):
                message = await request.json()
                self.message_log.append(message)
        return web.HTTPOk()

    
    async def commit(self, request):
        if(self.communication):
            for i in self.nodes:
                try:
                    await self.session.post(f'http://localhost:{8080 + i}/reply', json=self.message.log)
                except Exception as e:
                    pass
        return web.HTTPOk()
    
    async def reply(self, request):
        if(self.communication == False):
            message = await request.json()
            PBFTAggregator.receiveReplies([self.id, message[self.id]["data"]])
            return web.HTTPOk()
        return 
     
    def start(self):
        try:
            coroutine = self.loop.create_server(
                self.handler, '0.0.0.0', self.port)
            self.server = self.loop.run_until_complete(coroutine)
            address, port = self.server.sockets[0].getsockname()
            print(f'Node {self.id} started on http://{address}:{port}')
        except Exception as e:
            sys.stderr.write('Error: ' + format(str(e)) + "\n")
            sys.exit(1)

    def kill(self):
        self.server.close()
        self.loop.run_until_complete(self.app.shutdown())
        self.loop.run_until_complete(self.handler.shutdown(60.0))
        self.loop.run_until_complete(self.app.cleanup())    
    
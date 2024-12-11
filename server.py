"""
Authors:
- Iván Maldonado (Kikemaldonado11@gmail.com)
- Maria José Vera (nandadevi97816@gmail.com)
- Sergio Fernández (sergiofnzg@gmail.com)

Developed at: October 2024
"""

import socket
import threading
import asyncio
import websockets
import json
from jinja2 import Environment, FileSystemLoader

from models.Game import Game
from models.Table import Table


# Set the environment for Jinja template
env = Environment(loader=FileSystemLoader('templates'))



# -------------------------------- Utilities and resources --------------------------------------------


def render_index():
    """Render the index.html template."""
    template = env.get_template('index.html')
    return template.render(available_tables=[table for table in game.tables if table.available])

async def update_tables():
    """Send the updated list of tables to all clients."""
    updated_tables = [{
        'id': table.id,
        'available': table.available,
        'players': table.players  # Añadir la lista de jugadores
    } for table in game.tables]
    for client in clients:
        await client['client'].send(json.dumps({'tables': updated_tables}))




# ---------------------- Start server connections (TCP and Websocket) --------------------------------


def start_tcp_server(host='127.0.0.1', port=8080):
    """Start the TCP server."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(6)
    print(f'TCP Server is listening on {host}:{port}')

    while True:
        client_socket, client_address = server_socket.accept()
        print(f'TCP Connection from {client_address}')
        client_thread = threading.Thread(target=handle_tcp_client, args=(client_socket,))
        client_thread.start()
    

async def start_websocket_server(host='127.0.0.1', port=8765):
    """Start the WebSocket server."""
    async with websockets.serve(handle_websocket, host, port):
        print(f'WebSocket Server is listening on {host}:{port}')
        await asyncio.Future() 
        


# ------------------------- Handle tcp clients and websocket clients ---------------------------------        


def handle_tcp_client(client_socket):
    """Handle communication with a single TCP client."""
    
    try:
        request = client_socket.recv(1024).decode('utf-8')
        
        if "GET / " in request:
            
            # Render the HTML response and send it
            
            response_body = render_index()
            response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(response_body)}\r\n\r\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))


        # Stablish constant comunication with the client

        while True:
            data = client_socket.recv(1024)
            if not data:
                break  
        
            message = data.decode()

            response_body = render_index()
            response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(response_body)}\r\n\r\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

    finally:
        client_socket.close()


async def handle_websocket(websocket, path):
    """Handle WebSocket clients asynchronously."""
    
    # Add new client connections to the list of current clients
    clients.append({'client': websocket, 'table': None})
    
    try:
        while True:
            message = await websocket.recv()

            # Crear nueva mesa
            if message == 'NEW_TABLE':
                available_tables = [table for table in game.tables if table.available]
                if len(available_tables) < 3:  # Validar que no se creen más de 3 mesas sin progreso
                    game.create_table()
                    await update_tables()
                else:
                    await websocket.send(json.dumps({'error': 'No se pueden crear más de 3 mesas que no estén en progreso.'}))
                
            # Mostrar lista de mesas actualizada
            elif message == 'GET_TABLES':
                updated_tables = [{'id': table.id, 'available': table.available} for table in game.tables]
                await websocket.send(json.dumps({'tables': updated_tables}))
                
            # Unirse a una mesa existente
            elif message.startswith('JOIN_TABLE'):
                _, table_id = message.split()
                table_id = int(table_id)
                table = next((t for t in game.tables if t.id == table_id), None)

                if table and len(table.players) < 2:
                    player_id = str(websocket)
                    table.add_player(player_id, websocket)

                    # Asociar este websocket con la mesa en la lista de clientes
                    for client in clients:
                        if client['client'] == websocket:
                            client['table'] = table_id
                            
                    # Si la mesa tiene solo 1 jugador, enviar mensaje de espera
                    if len(table.players) == 1:
                        # Enviar mensaje de espera a este jugador
                        await websocket.send(json.dumps({
                            'message': 'A la espera de otro participante...',
                            'table_id': table.id
                        }))
                    
                    # Si ambos jugadores están en la mesa, se inicia el juego
                    if len(table.players) == 2:
                        player1_socket = table.player_sockets[table.players[0]]
                        player2_socket = table.player_sockets[table.players[1]]
                        
                        table.available = False
                        
                        # Programar el inicio del juego
                        game_loop = asyncio.get_event_loop()
                        threading.Thread(target=game_thread, args=(table, player1_socket, player2_socket, game_loop)).start()

                    await update_tables()  # Actualizar la lista de mesas disponibles

            # Gestionar los movimientos de los jugadores
            elif message.startswith('MAKE_MOVE'):
                _, table_id, index = message.split(',')
                table = next((t for t in game.tables if t.id == int(table_id)), None)
                
                if table:
                    # Realizar el movimiento
                    table.make_move(int(index), table.turn)
                    
                    # Enviar la actualización del estado de la mesa a todos los jugadores
                    for client in clients:
                        if client['table'] == int(table_id):
                            # Preparar el mensaje a enviar
                            response = {
                                'board': table.game_board,
                                'table_id': int(table_id),
                                'winner': table.winner  # Incluir el estado del ganador
                            }
                            await client['client'].send(json.dumps(response))

                    # Si hay un ganador o empate, reiniciar la mesa
                    if table.winner:
                        game.remove_table(table.id)
                        await update_tables()  # Actualizar la lista de mesas disponibles

    except websockets.exceptions.ConnectionClosed:
        print("Connection closed")
    finally:
        # Eliminar cliente de la lista cuando se cierre la conexión
        client = [client for client in clients if client['client'] == websocket][0]
        clients.remove(client)




# ------------------------------Thread logic for each game ----------------------------------------------

    
def game_thread(table, player1_socket, player2_socket, game_loop):
    """Thread to handle the game logic between two players."""
    player_sockets = [player1_socket, player2_socket]
    
            
    async def send_initial_board():
        """Send the current board state to both clients."""
        for socket in player_sockets:
            await socket.send(json.dumps({
                'board': table.game_board,
                'table_id': table.id,
                'display': True,
            }))

    async def game_logic():
        await send_initial_board()
        
            
    # Schedule the game logic to run
    asyncio.run_coroutine_threadsafe(game_logic(), game_loop)



if __name__ == '__main__':
    
    # Create a game object and an empty clients list before start the server
    game = Game()
    clients = []

    # Start TCP server in a separate thread
    tcp_thread = threading.Thread(target=start_tcp_server)
    tcp_thread.start()

    # Start WebSocket server
    asyncio.run(start_websocket_server())
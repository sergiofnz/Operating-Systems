class Table:
    def __init__(self, _id):
        self.id = _id
        self.game_board = [' ' for _ in range(9)]
        self.available = True
        self.players = []
        self.player_sockets = {}
        self.winner = None
        self.turn = 'X'  
    
    def add_player(self, player_id, websocket):
        """Add a player and store their WebSocket."""
        if len(self.players) < 2:
            self.players.append(player_id)
            self.player_sockets[player_id] = websocket
            
        # Table becomes unavailable when full
        if len(self.players) == 2:
            self.available = False  

    def make_move(self, index, player_turn):
        """Make a move at the given index if the cell is empty."""
        if self.game_board[index] == ' ':
            self.game_board[index] = player_turn
            winner = self.check_winner()
            if winner:
                self.winner = winner
                self.available = False  # La mesa ya no está disponible
                self.notify_players({
                    'message': 'Game Over!',
                    'winner': winner,
                    'clear_board': True  # Añadimos esta propiedad para indicar que se debe limpiar el tablero
                })
            else:
                # Switch the turn to the other player
                self.turn = 'O' if player_turn == 'X' else 'X'

    def check_winner(self):
        """Check for a winner and return 'X', 'O', or 'Draw'."""
        winning_combinations = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Filas
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columnas
            [0, 4, 8], [2, 4, 6]               # Diagonales
        ]
        
        for combo in winning_combinations:
            if self.game_board[combo[0]] == self.game_board[combo[1]] == self.game_board[combo[2]] != ' ':
                self.winner = self.game_board[combo[0]]
                self.available = False
                self.notify_players({'message': f'Game Over! Winner: {self.winner}', 'clear_board': True})
                # Aquí podrías eliminar la mesa si es necesario
                return self.winner

        if ' ' not in self.game_board:
            self.winner = 'Draw'
            self.available = False
            self.notify_players({'message': 'Game Over! It\'s a Draw!', 'clear_board': True})
            # Aquí también podrías eliminar la mesa si es necesario
            return 'Draw'

        return None  # No hay ganador aún
    
    
    def notify_players(self, message):
        """Notify both players about the game outcome."""
        for player_id in self.players:
            websocket = self.player_sockets[player_id]
            websocket.send(message)

    
    def reset_game(self):
        """Reset the game board and state for a new game."""
        self.game_board = [' ' for _ in range(9)]
        self.available = True
        self.players = []
        self.player_sockets = {}
        self.winner = None
        self.turn = 'X'

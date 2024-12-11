"""
Authors:
- Iván Maldonado (Kikemaldonado11@gmail.com)
- Maria José Vera (nandadevi97816@gmail.com)
- Sergio Fernández (sergiofnzg@gmail.com)

Developed at: October 2024
"""

from models.Table import Table

class Game():
    
    def __init__(self):
        self.tables = []
        self.table_id = 1
          
    def create_table(self):
        """Create a new table if less than 3 tables are not available."""
        available_tables = [table for table in self.tables if table.available]
        if len(available_tables) < 3:  # Validar que haya menos de 3 mesas disponibles
            table = Table(self.table_id)
            self.tables.append(table)
            self.table_id += 1
        else:
            print("Cannot create more than 3 tables that are not in progress.")  # Mensaje de error (puedes manejarlo de otra manera)

    def remove_table(self, table_id):
        """Remove a table from the game."""
        self.tables = [table for table in self.tables if table.id != table_id]

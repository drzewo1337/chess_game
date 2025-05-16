import sys
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QLabel, QVBoxLayout, \
    QWidget, QMenu, QListWidget, QMainWindow, QGraphicsTextItem, QTextEdit, QDialog, QPushButton, QComboBox, QLineEdit
from PyQt5.QtGui import QPixmap, QColor, QPen
from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF, pyqtSignal, QObject, QTimer


def cell_name_from_row_col(row, col):
    column_letter = chr(ord('A') + col)  # Konwertowanie numeru kolumny na odpowiadającą mu literę
    row_number = 8 - row  # Numer wiersza odwrócony, aby pasował do konwencji szachowej
    return f"{column_letter}{row_number}"


class MoveHistoryWindow(QDialog):
    update_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.move_history = []
        self.setWindowTitle("Move History")
        self.setGeometry(100, 100, 300, 400)

        layout = QVBoxLayout()
        self.history_text_edit = QTextEdit()
        layout.addWidget(self.history_text_edit)
        self.setLayout(layout)

        self.update_signal.connect(self.update_history_text)

    def add_move(self, move):
        self.move_history.append(move)
        self.update_signal.emit()

    def update_history_text(self):
        text = ""
        for move in self.move_history:
            text += f"{move[1]} {move[2]} moved to {move[0]}\n"
        self.history_text_edit.setPlainText(text)


class DraggableChessPiece(QGraphicsPixmapItem):
    def __init__(self, pixmap, square_size, board_size, color, piece_type, board, parent=None):
        super().__init__(pixmap, parent)
        self.setFlag(QGraphicsPixmapItem.ItemIsMovable)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.OpenHandCursor)
        self.setZValue(1)
        self.square_size = square_size
        self.board_size = board_size
        self.color = color  # Kolor pionka
        self.piece_type = piece_type  # Rodzaj pionka
        self.board = board  # Referencja do obiektu ChessBoard

        self.row = None  # Numer wiersza
        self.col = None  # Numer kolumny

    def set_row_col(self, row, col):
        self.row = row
        self.col = col

    def mousePressEvent(self, event):
        if self.color != self.board.current_player:  # Sprawdzanie czy kolor pionka zgadza się z aktualnym graczem
            event.ignore()  # Ignoruj zdarzenie, jeśli kolor pionka nie zgadza się z aktualnym graczem
            return
        self.setCursor(Qt.ClosedHandCursor)
        self.setScale(1.3)  # Zmiana rozmiaru figury
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        self.setScale(1.0)  # Przywrócenie domyślnego rozmiaru figury
        pos = event.scenePos()
        new_x = int(pos.x() / self.square_size) * self.square_size
        new_y = int(pos.y() / self.square_size) * self.square_size
        new_x = max(0, min(self.board_size - self.square_size, new_x))
        new_y = max(0, min(self.board_size - self.square_size, new_y))
        new_pos = QPointF(new_x, new_y)

        # Sprawdzanie czy figura może się poruszyć na daną pozycję
        if self.can_move_to_position(new_x, new_y):
            items = self.scene().items(QRectF(new_pos, QSizeF(self.square_size, self.square_size)))
            for item in items:
                if isinstance(item, DraggableChessPiece) and item != self:
                    if item.color != self.color:
                        # Sprawdzamy czy ruch to bicie figury
                        if self.can_capture_piece(item):
                            self.scene().removeItem(item)
                            del item
                        else:
                            # W innym przypadku ruch nie jest dozwolony, więc figura nie może być przesunięta
                            return self.setPos(self.col * self.square_size, self.row * self.square_size)
                    else:
                        # Jeśli figura tego samego koloru stoi na docelowym polu, nie rób nic
                        return self.setPos(self.col * self.square_size, self.row * self.square_size)
                    break

            self.setPos(new_pos)

            # Ustawienie numerów wiersza i kolumny
            self.row = int(new_y / self.square_size)
            self.col = int(new_x / self.square_size)

            # Wyświetlenie komórki, na którą przeniesiono figurę
            cell_name = cell_name_from_row_col(self.row, self.col)
            print(f"Position of {self.color} {self.piece_type}: {cell_name}")

            # Dodanie ruchu do historii
            self.board.move_history_window.add_move((cell_name, self.color, self.piece_type))

            # Zmiana tury po ruchu
            self.board.change_turn()
            # Aktualizacja labela z turą
            self.board.update_turn_label()
        else:
            # Jeśli ruch jest nieprawidłowy, figury nie zostaną przesunięte
            self.setPos(self.col * self.square_size, self.row * self.square_size)

        super().mouseReleaseEvent(event)

    def can_capture_piece(self, piece):
        """
        Sprawdza, czy figura może zbijać daną figurę.
        """
        if self.piece_type == 'Pawn':
            # Pionek może bić tylko po skosie
            return abs(piece.col - self.col) == 1 and abs(piece.row - self.row) == 1
        elif self.piece_type == 'King':
            # Król może bić figurę, która jest na jednym z sąsiednich pól
            return abs(piece.col - self.col) <= 1 and abs(piece.row - self.row) <= 1
        elif self.piece_type == 'Knight':
            # Skoczek może bić figurę na polach, które są dostępne dla jego ruchu
            return (abs(piece.col - self.col) == 2 and abs(piece.row - self.row) == 1) or \
                (abs(piece.col - self.col) == 1 and abs(piece.row - self.row) == 2)
        else:
            # Dla pozostałych typów figurek, sprawdzamy czy docelowe pole jest w zasięgu ruchu
            if self.can_move_to_position(piece.col * self.square_size, piece.row * self.square_size):
                return True
            else:
                return False

    def can_move_to_position(self, x, y):
        # Sprawdzenie czy docelowe pole jest puste lub zajęte przez przeciwnika
        for item in self.scene().items():
            if isinstance(item, DraggableChessPiece):
                if item != self and item.row is not None and item.col is not None:
                    # Jeśli istnieje figura na danej pozycji
                    if item.row == int(y / self.square_size) and item.col == int(x / self.square_size):
                        # Sprawdzenie czy figura na docelowej pozycji jest przeciwnego koloru
                        if item.color != self.color:
                            return True  # Możliwe bicie figury
                        else:
                            return False  # Ruch na zajętą pozycję figury tego samego koloru
                    # Sprawdzenie czy droga figury jest przecinana przez inną figurę
                    if item.row == self.row and item.col == self.col:
                        # Jeśli figura stoi na pozycji startowej
                        continue
                    # Jeśli figura jest na tej samej linii pionowej lub poziomej co docelowa pozycja
                    if item.row == int(y / self.square_size) or item.col == int(x / self.square_size):
                        if self.piece_type in ('Rook', 'Queen') or item.piece_type in ('Rook', 'Queen'):
                            # Jeśli figura jest wieżą lub hetmanem
                            if self.row == item.row:
                                # Jeśli figura jest na tej samej linii poziomej co docelowa pozycja
                                if min(self.col, int(x / self.square_size)) < item.col < max(self.col,
                                                                                             int(x / self.square_size)):
                                    return False  # Droga figury jest przecięta przez inną figurę
                            elif self.col == item.col:
                                # Jeśli figura jest na tej samej linii pionowej co docelowa pozycja
                                if min(self.row, int(y / self.square_size)) < item.row < max(self.row,
                                                                                             int(y / self.square_size)):
                                    return False  # Droga figury jest przecięta przez inną figurę
                    # Jeśli figura jest na tej samej linii po skosie co docelowa pozycja
                    if abs(item.row - int(y / self.square_size)) == abs(item.col - int(x / self.square_size)):
                        if self.piece_type in ('Bishop', 'Queen') or item.piece_type in ('Bishop', 'Queen'):
                            # Jeśli figura jest gońcem lub hetmanem
                            min_row = min(self.row, int(y / self.square_size))
                            max_row = max(self.row, int(y / self.square_size))
                            min_col = min(self.col, int(x / self.square_size))
                            max_col = max(self.col, int(x / self.square_size))
                            # Sprawdzenie czy droga figury jest przecięta przez inną figurę
                            for i in range(min_row + 1, max_row):
                                for j in range(min_col + 1, max_col):
                                    if item.row == i and item.col == j:
                                        return False  # Droga figury jest przecięta przez inną figurę
        # Warunki sprawdzające czy figura może się poruszyć na daną pozycję
        if self.piece_type == 'Pawn':
            # Pionek może poruszyć się tylko do przodu o jedno pole, a także ma specjalne zasady dla pierwszego ruchu
            if self.color == 'White':
                if y == self.row * self.square_size + self.square_size and x == self.col * self.square_size:
                    return True
                elif y == self.row * self.square_size + self.square_size * 2 and x == self.col * self.square_size and self.row == 1:
                    return True
            else:
                if y == self.row * self.square_size - self.square_size and x == self.col * self.square_size:
                    return True
                elif y == self.row * self.square_size - self.square_size * 2 and x == self.col * self.square_size and self.row == 6:
                    return True
        elif self.piece_type == 'Rook':
            # Wieża może poruszyć się wzdłuż wierszy i kolumn
            return x == self.col * self.square_size or y == self.row * self.square_size
        elif self.piece_type == 'Knight':
            # Skoczek może poruszać się w kształcie litery "L"
            return (abs(x - self.col * self.square_size) == 2 * self.square_size and abs(
                y - self.row * self.square_size) == self.square_size) or \
                (abs(x - self.col * self.square_size) == self.square_size and abs(
                    y - self.row * self.square_size) == 2 * self.square_size)
        elif self.piece_type == 'Bishop':
            # Goniec może poruszać się po skosie
            return abs(x - self.col * self.square_size) == abs(y - self.row * self.square_size)
        elif self.piece_type == 'Queen':
            # Hetman może poruszać się jak wieża lub goniec
            return (x == self.col * self.square_size or y == self.row * self.square_size) or abs(
                x - self.col * self.square_size) == abs(y - self.row * self.square_size)
        elif self.piece_type == 'King':
            # Król może poruszać się o jedno pole w dowolnym kierunku
            return abs(x - self.col * self.square_size) <= self.square_size and abs(
                y - self.row * self.square_size) <= self.square_size
        else:
            # W pozostałych przypadkach zwracamy True, co oznacza, że figura może poruszyć się na tę pozycję
            return True


class ChessBoard(QGraphicsView):
    def __init__(self, move_history_window):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setWindowTitle("Chess Game")
        self.setMinimumSize(600, 600)
        self.board_size = 600  # Rozmiar planszy
        self.square_size = self.board_size / 8
        self.draw_board()
        self.draw_pieces()
        self.current_player = 'White'  # Ustawienie tury na białego gracza
        self.move_history_window = move_history_window  # Okno historii ruchów
        self.timer = QTimer(self)  # Timer dla mierzenia czasu
        self.timer.timeout.connect(self.update_time)  # Po zdarzeniu timera aktualizujemy czas
        self.time_options = {'1 minuta': 60, '5 minut': 300, '10 minut': 600}  # Dostępne opcje czasowe
        self.white_time = 60  # Początkowy czas dla białego gracza (60 sekund)
        self.black_time = 60  # Początkowy czas dla czarnego gracza (60 sekund)
        self.turn_label = QLabel("Current Turn: White (60 sec)")  # Etykieta do wyświetlania aktualnej tury
        self.time_combobox = QComboBox()  # Lista rozwijana do wyboru czasu
        self.time_combobox.addItems(self.time_options.keys())  # Dodaj opcje czasowe do listy rozwijanej
        self.start_button = QPushButton("Start Game")  # Przycisk do rozpoczęcia gry
        self.start_button.clicked.connect(self.start_game)  # Po kliknięciu rozpoczynamy grę

    def is_king_under_attack(self, color):
        king_row, king_col = None, None
        print("Szach")
        # Znajdź pozycję króla danego koloru
        for item in self.scene.items():
            if isinstance(item, DraggableChessPiece) and item.color == color and item.piece_type == 'King':
                king_row, king_col = item.row, item.col
                break
        # Sprawdź, czy król jest atakowany przez jakąkolwiek figurę przeciwnika
        for item in self.scene.items():
            if isinstance(item, DraggableChessPiece) and item.color != color:
                if item.can_capture_piece((king_row, king_col)):
                    return True
        return False

    def is_checkmate(self, color):
        # Sprawdź, czy król jest pod biciem
        if not self.is_king_under_attack(color):
            return False
        # Sprawdź, czy król może się obronić lub zablokować atakującą figurę
        for item in self.scene.items():
            if isinstance(item, DraggableChessPiece) and item.color == color:
                for row in range(8):
                    for col in range(8):
                        if item.is_valid_move(item.row, item.col, row, col, color):
                            if not self.is_king_under_attack(color):
                                return False
        return True

    def is_valid_move(self, row, col, target_row, target_col, color):
        # Sprawdź, czy król jest szachowany po wykonaniu ruchu
        king_is_under_attack = self.is_king_under_attack(color)
        # Sprawdź, czy ruch figury na dane pole jest prawidłowy
        for item in self.scene.items():
            if isinstance(item, DraggableChessPiece) and item.row == row and item.col == col and item.color == color:
                if not king_is_under_attack:
                    # Sprawdź, czy ruch figury na docelowe pole jest możliwy
                    if not item.can_move_to_position(target_col * self.square_size, target_row * self.square_size):
                        return False
                # Próbuj wykonać tymczasowo ruch
                original_row, original_col = item.row, item.col
                item.set_row_col(target_row, target_col)
                for piece in self.scene.items():
                    if isinstance(piece, DraggableChessPiece) and piece.color != color:
                        # Sprawdź, czy tymczasowy ruch wystawia króla na szach
                        if piece.can_capture_piece((target_row, target_col)):
                            item.set_row_col(original_row, original_col)  # Przywróć oryginalną pozycję
                            return False
                item.set_row_col(original_row, original_col)  # Przywróć oryginalną pozycję
                return True
        return False

    def handle_move_input(self):
        move_text = self.move_input.text()
        self.move_input.clear()  # Wyczyść pole tekstowe po wprowadzeniu ruchu
        if move_text:
            # Rozdziel wprowadzony tekst na poszczególne części
            parts = move_text.split()
            if len(parts) == 3:
                piece_type = parts[0]  # Rodzaj pionka
                current_position = parts[1]  # Aktualna pozycja
                target_position = parts[2]  # Docelowa pozycja
                # Sprawdź, czy wprowadzone pozycje są poprawne
                if len(current_position) == 2 and len(target_position) == 2:
                    current_col = ord(current_position[0].upper()) - ord('A')  # Konwersja litery kolumny na numer
                    current_row = 8 - int(current_position[1])  # Odwrócenie numeru wiersza
                    target_col = ord(target_position[0].upper()) - ord('A')  # Konwersja litery kolumny na numer
                    target_row = 8 - int(target_position[1])  # Odwrócenie numeru wiersza
                    # Sprawdź, czy ruch jest możliwy dla danej figury
                    if self.is_valid_move(current_row, current_col, target_row, target_col, self.current_player):
                        # Przenieś figurę na docelowe pole
                        for item in self.scene.items():
                            if isinstance(item,
                                          DraggableChessPiece) and item.row == current_row and item.col == current_col:
                                item.set_row_col(target_row, target_col)
                                item.setPos(target_col * self.square_size, target_row * self.square_size)
                                break
                        # Sprawdź, czy wykonany ruch prowadzi do szacha lub szach-matu
                        if self.is_checkmate(self.current_player):
                            print(f"{self.current_player} jest szachowany matem!")
                            self.stop_timer()  # Zatrzymaj timer
                        elif self.is_king_under_attack(self.current_player):
                            print(f"{self.current_player} jest szachowany!")
                        # Zaktualizuj tury i historię ruchów
                        self.change_turn()
                        self.update_turn_label()
                        # Zaktualizuj historię ruchów
                        cell_name_current = cell_name_from_row_col(current_row, current_col)
                        cell_name_target = cell_name_from_row_col(target_row, target_col)
                        self.move_history_window.add_move((cell_name_target, item.color, piece_type))
                        print(f"Position of {item.color} {piece_type}: {cell_name_current} moved to {cell_name_target}")
                    else:
                        print("Nieprawidłowy ruch!")
                else:
                    print("Nieprawidłowy format pozycji!")
        print("Wykonano ruch!")

    def start_game(self):
        self.start_button.setEnabled(False)  # Wyłączamy przycisk startu
        selected_time = self.time_options[self.time_combobox.currentText()]  # Wybierz czas na podstawie wyboru użytkownika
        self.white_time = selected_time  # Ustaw czas białego gracza
        self.black_time = selected_time  # Ustaw czas czarnego gracza
        self.start_timer()  # Rozpocznij odliczanie czasu

    def start_timer(self):
        self.timer.start(1000)  # Uruchomienie timera, który wywoła się co sekundę

    def stop_timer(self):
        self.timer.stop()  # Zatrzymanie timera

    def update_time(self):
        if self.current_player == 'White':
            self.white_time -= 1
            self.update_turn_label()
        else:
            self.black_time -= 1
            self.update_turn_label()

        if self.white_time <= 0:
            print("Czas minął! Czarny gracz wygrywa!")
            self.stop_timer()
        elif self.black_time <= 0:
            print("Czas minął! Biały gracz wygrywa!")
            self.stop_timer()

    def update_turn_label(self):
        if self.current_player == 'White':
            self.turn_label.setText(f"Current Turn: White ({self.white_time} sec), Black ({self.black_time})sec")
        else:
            self.turn_label.setText(f"Current Turn: White ({self.white_time} sec), Black ({self.black_time})sec")

    def draw_board(self):
        colors = [QColor(255, 206, 158), QColor(209, 139, 71)]
        font = self.font()
        font.setPixelSize(20)  # Rozmiar czcionki dla numerów wierszy i kolumn

        for row in range(8):
            for col in range(8):
                color = colors[(row + col) % 2]
                square = QRectF(col * self.square_size, row * self.square_size, self.square_size, self.square_size)
                self.scene.addRect(square, pen=QPen(Qt.black), brush=color)

        # Dodanie numerów kolumn (liter A-H)
        for col in range(8):
            col_label = QGraphicsTextItem(chr(ord('A') + col))
            col_label.setFont(font)
            col_label.setDefaultTextColor(Qt.black)
            col_label.setPos(col * self.square_size + self.square_size / 2 - col_label.boundingRect().width() / 2,
                             -col_label.boundingRect().height() + 5)
            self.scene.addItem(col_label)

        # Dodanie numerów wierszy (cyfry 1-8)
        for row in range(8):
            row_label = QGraphicsTextItem(str(8 - row))
            row_label.setFont(font)
            row_label.setDefaultTextColor(Qt.black)
            row_label.setPos(8 * self.square_size + 5,
                             row * self.square_size + self.square_size / 2 - row_label.boundingRect().height() / 2)
            self.scene.addItem(row_label)

    def draw_pieces(self):
        scale_factor = self.square_size / 60  # Współczynnik skali
        pieces = {
            (0, 0): ('chess_figures/ro_wh.png', 'White', 'Rook'),
            (1, 0): ('chess_figures/kni_wh.png', 'White', 'Knight'),
            (2, 0): ('chess_figures/bis_wh.png', 'White', 'Bishop'),
            (3, 0): ('chess_figures/q_wh.png', 'White', 'Queen'),
            (4, 0): ('chess_figures/king_wh.png', 'White', 'King'),
            (5, 0): ('chess_figures/bis_wh.png', 'White', 'Bishop'),
            (6, 0): ('chess_figures/kni_wh.png', 'White', 'Knight'),
            (7, 0): ('chess_figures/ro_wh.png', 'White', 'Rook'),

            (0, 1): ('chess_figures/pa_wh.png', 'White', 'Pawn'),
            (1, 1): ('chess_figures/pa_wh.png', 'White', 'Pawn'),
            (2, 1): ('chess_figures/pa_wh.png', 'White', 'Pawn'),
            (3, 1): ('chess_figures/pa_wh.png', 'White', 'Pawn'),
            (4, 1): ('chess_figures/pa_wh.png', 'White', 'Pawn'),
            (5, 1): ('chess_figures/pa_wh.png', 'White', 'Pawn'),
            (6, 1): ('chess_figures/pa_wh.png', 'White', 'Pawn'),
            (7, 1): ('chess_figures/pa_wh.png', 'White', 'Pawn'),

            (0, 7): ('chess_figures/ro_bl.png', 'Black', 'Rook'),
            (1, 7): ('chess_figures/kni_bl.png', 'Black', 'Knight'),
            (2, 7): ('chess_figures/bis_bl.png', 'Black', 'Bishop'),
            (3, 7): ('chess_figures/q_bl.png', 'Black', 'Queen'),
            (4, 7): ('chess_figures/king_bl.png', 'Black', 'King'),
            (5, 7): ('chess_figures/bis_bl.png', 'Black', 'Bishop'),
            (6, 7): ('chess_figures/kni_bl.png', 'Black', 'Knight'),
            (7, 7): ('chess_figures/ro_bl.png', 'Black', 'Rook'),

            (0, 6): ('chess_figures/pa_bl.png', 'Black', 'Pawn'),
            (1, 6): ('chess_figures/pa_bl.png', 'Black', 'Pawn'),
            (2, 6): ('chess_figures/pa_bl.png', 'Black', 'Pawn'),
            (3, 6): ('chess_figures/pa_bl.png', 'Black', 'Pawn'),
            (4, 6): ('chess_figures/pa_bl.png', 'Black', 'Pawn'),
            (5, 6): ('chess_figures/pa_bl.png', 'Black', 'Pawn'),
            (6, 6): ('chess_figures/pa_bl.png', 'Black', 'Pawn'),
            (7, 6): ('chess_figures/pa_bl.png', 'Black', 'Pawn'),
        }

        for (col, row), (img_file, color, piece_type) in pieces.items():
            pixmap = QPixmap(img_file)
            pixmap = pixmap.scaled(int(pixmap.width() * scale_factor), int(pixmap.height() * scale_factor))
            item = DraggableChessPiece(pixmap, self.square_size, self.board_size, color, piece_type,
                                       self)  # Przekazanie koloru pionka oraz referencji do obiektu ChessBoard
            self.scene.addItem(item)
            item.setPos(col * self.square_size, row * self.square_size)
            item.set_row_col(row, col)

    def change_turn(self):
        if self.current_player == 'White':
            self.current_player = 'Black'
        else:
            self.current_player = 'White'

    #def update_turn_label(self):
     #   self.turn_label.setText(f"Current Turn: {self.current_player}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        min_dimension = min(self.width(), self.height())
        self.board_size = min_dimension - 50  # Rozmiar planszy pomniejszony o 50 pikseli
        self.square_size = self.board_size / 8
        self.setSceneRect(0, 0, self.board_size, self.board_size)
        self.scene.clear()
        self.draw_board()
        self.draw_pieces()


class ChessGame(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.move_history_window = MoveHistoryWindow()  # Przekazanie pustej historii ruchów
        self.board = ChessBoard(self.move_history_window)
        self.move_input = QLineEdit()  # Pole tekstowe do wprowadzania ruchów
        self.move_input.returnPressed.connect(self.handle_move_input)  # Po naciśnięciu Enter obsłuż ruch
        layout.addWidget(self.move_history_window)
        layout.addWidget(self.board.turn_label)
        layout.addWidget(self.board.start_button)
        layout.addWidget(self.board.time_combobox)
        layout.addWidget(self.board)
        layout.addWidget(self.move_input)  # Dodanie pola tekstowego do layoutu
        self.setLayout(layout)
        self.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.handle_move_input()
        else:
            super().keyPressEvent(event)

    def handle_move_input(self):
        move_text = self.move_input.text()
        self.move_input.clear()  # Wyczyść pole tekstowe po wprowadzeniu ruchu
        if move_text:
            # Rozdziel wprowadzony tekst na poszczególne części
            parts = move_text.split()
            if len(parts) == 3:
                piece_type = parts[0]  # Rodzaj pionka
                current_position = parts[1]  # Aktualna pozycja
                target_position = parts[2]  # Docelowa pozycja
                # Sprawdź, czy wprowadzone pozycje są poprawne
                if len(current_position) == 2 and len(target_position) == 2:
                    current_col = ord(current_position[0].upper()) - ord('A')  # Konwersja litery kolumny na numer
                    current_row = 8 - int(current_position[1])  # Odwrócenie numeru wiersza
                    target_col = ord(target_position[0].upper()) - ord('A')  # Konwersja litery kolumny na numer
                    target_row = 8 - int(target_position[1])  # Odwrócenie numeru wiersza
                    # Znajdź pionek na podanej pozycji
                    for item in self.board.scene.items():
                        if isinstance(item, DraggableChessPiece) and item.row == current_row and item.col == current_col:
                            # Jeśli znaleziono pionka na danej pozycji, wykonaj ruch
                            item.set_row_col(target_row, target_col)
                            item.setPos(target_col * self.board.square_size, target_row * self.board.square_size)
                            self.board.change_turn()
                            self.board.update_turn_label()
                            # Zaktualizuj historię ruchów
                            cell_name_current = cell_name_from_row_col(current_row, current_col)
                            cell_name_target = cell_name_from_row_col(target_row, target_col)
                            self.move_history_window.add_move((cell_name_target, item.color, piece_type))
                            print(f"Position of {item.color} {piece_type}: {cell_name_current} moved to {cell_name_target}")
                            return
        print("Wykonano ruch!")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChessGame()
    sys.exit(app.exec_())

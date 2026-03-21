import random
from maumau.deck import create_shuffled_deck, card_suit, card_value, SUITS


class MauMauGame:
    """Core game logic for Mau-Mau."""

    HAND_SIZE = 7

    def __init__(self):
        self.players = []
        self.deck = []
        self.discard_pile = []
        self.current_player_index = 0
        self.direction = 1  # 1 = clockwise, -1 = counter-clockwise
        self.pending_draw = 0
        self.wished_suit = None
        self.status = 'waiting'
        self.winner = None
        self.rounds = 0

    def add_player(self, player_id, name, player_type='human', socket_id=None):
        if len(self.players) >= 4:
            return False
        self.players.append({
            'id': str(player_id),
            'name': name,
            'type': player_type,
            'hand': [],
            'socket_id': socket_id,
            'said_mau': False,
        })
        return True

    def start_game(self):
        if len(self.players) < 2:
            return False

        self.deck = create_shuffled_deck()
        self.discard_pile = []
        self.current_player_index = 0
        self.direction = 1
        self.pending_draw = 0
        self.wished_suit = None
        self.status = 'playing'
        self.winner = None
        self.rounds = 0

        for player in self.players:
            player['hand'] = []
            for _ in range(self.HAND_SIZE):
                if self.deck:
                    player['hand'].append(self.deck.pop())

        # Find a non-special card to start the discard pile
        while True:
            if not self.deck:
                self.deck = create_shuffled_deck()
            card = self.deck.pop()
            self.discard_pile.append(card)
            v = card_value(card)
            if v not in ('7', '8', 'J', 'A'):
                break
            self.discard_pile.pop()
            self.deck.insert(0, card)
            random.shuffle(self.deck)

        return True

    def top_card(self):
        if self.discard_pile:
            return self.discard_pile[-1]
        return None

    def current_player(self):
        return self.players[self.current_player_index]

    def _recycle_discard_pile(self):
        if len(self.discard_pile) <= 1:
            return
        top = self.discard_pile[-1]
        recycle = self.discard_pile[:-1]
        random.shuffle(recycle)
        self.deck.extend(recycle)
        self.discard_pile = [top]

    def can_play_card(self, card):
        top = self.top_card()
        if top is None:
            return True

        top_suit = card_suit(top)
        top_val = card_value(top)
        play_suit = card_suit(card)
        play_val = card_value(card)

        if self.pending_draw > 0:
            return play_val == '7'

        if play_val == 'J':
            return True

        if self.wished_suit:
            return play_suit == self.wished_suit or play_val == 'J'

        return play_suit == top_suit or play_val == top_val

    def get_playable_cards(self, player):
        return [c for c in player['hand'] if self.can_play_card(c)]

    def play_card(self, player_id, card, wished_suit=None):
        player = self.current_player()
        if str(player['id']) != str(player_id):
            return {'error': 'Not your turn'}

        if card not in player['hand']:
            return {'error': 'Card not in hand'}

        if not self.can_play_card(card):
            return {'error': 'Cannot play this card'}

        player['hand'].remove(card)
        self.discard_pile.append(card)
        self.wished_suit = None

        result = {
            'card': card,
            'player_name': player['name'],
            'player_id': player['id'],
            'special': None,
            'mau': False,
            'mau_mau': False,
        }

        v = card_value(card)

        if v == '7':
            self.pending_draw += 2
            result['special'] = 'draw2'
        elif v == '8':
            result['special'] = 'skip'
        elif v == 'J':
            if wished_suit and wished_suit in SUITS:
                self.wished_suit = wished_suit
            else:
                self.wished_suit = self._best_suit_for_player(player)
            result['special'] = 'wish'
            result['wished_suit'] = self.wished_suit
        elif v == 'A':
            if len(self.players) == 2:
                result['special'] = 'skip'
            else:
                self.direction *= -1
                result['special'] = 'reverse'

        if len(player['hand']) == 0:
            self.winner = player['id']
            self.status = 'finished'
            result['mau_mau'] = True
            return result

        if len(player['hand']) == 1:
            player['said_mau'] = True
            result['mau'] = True

        self._advance_player()

        if result['special'] == 'skip':
            self._advance_player()

        self.rounds += 1

        return result

    def draw_card(self, player_id):
        player = self.current_player()
        if str(player['id']) != str(player_id):
            return {'error': 'Not your turn'}

        draw_count = max(self.pending_draw, 1)
        drawn_cards = []

        for _ in range(draw_count):
            if not self.deck:
                self._recycle_discard_pile()
            if self.deck:
                card = self.deck.pop()
                player['hand'].append(card)
                drawn_cards.append(card)

        self.pending_draw = 0
        self._advance_player()
        self.rounds += 1

        return {
            'drawn_cards': drawn_cards,
            'draw_count': len(drawn_cards),
            'player_name': player['name'],
            'player_id': player['id'],
        }

    def _advance_player(self):
        n = len(self.players)
        self.current_player_index = (self.current_player_index + self.direction) % n

    def _best_suit_for_player(self, player):
        suit_counts = {s: 0 for s in SUITS}
        for card in player['hand']:
            s = card_suit(card)
            suit_counts[s] += 1
        return max(SUITS, key=lambda s: suit_counts[s])

    def get_state_for_player(self, player_id):
        players_view = []
        for p in self.players:
            pv = {
                'id': p['id'],
                'name': p['name'],
                'type': p['type'],
                'card_count': len(p['hand']),
                'said_mau': p.get('said_mau', False),
            }
            if str(p['id']) == str(player_id):
                pv['hand'] = p['hand']
            players_view.append(pv)

        return {
            'players': players_view,
            'top_card': self.top_card(),
            'deck_count': len(self.deck),
            'current_player_index': self.current_player_index,
            'current_player_id': self.current_player()['id'],
            'direction': self.direction,
            'pending_draw': self.pending_draw,
            'wished_suit': self.wished_suit,
            'status': self.status,
            'winner': self.winner,
            'rounds': self.rounds,
        }

    def get_full_state(self):
        return {
            'players': [{
                'id': p['id'],
                'name': p['name'],
                'type': p['type'],
                'hand': p['hand'],
                'socket_id': p.get('socket_id'),
                'said_mau': p.get('said_mau', False),
            } for p in self.players],
            'deck': self.deck,
            'discard_pile': self.discard_pile,
            'current_player_index': self.current_player_index,
            'direction': self.direction,
            'pending_draw': self.pending_draw,
            'wished_suit': self.wished_suit,
            'status': self.status,
            'winner': self.winner,
            'rounds': self.rounds,
        }

    @classmethod
    def from_state(cls, state):
        game = cls()
        game.players = []
        for p in state.get('players', []):
            game.players.append({
                'id': str(p['id']),
                'name': p['name'],
                'type': p['type'],
                'hand': list(p['hand']),
                'socket_id': p.get('socket_id'),
                'said_mau': p.get('said_mau', False),
            })
        game.deck = list(state.get('deck', []))
        game.discard_pile = list(state.get('discard_pile', []))
        game.current_player_index = state.get('current_player_index', 0)
        game.direction = state.get('direction', 1)
        game.pending_draw = state.get('pending_draw', 0)
        game.wished_suit = state.get('wished_suit')
        game.status = state.get('status', 'waiting')
        game.winner = state.get('winner')
        game.rounds = state.get('rounds', 0)
        return game

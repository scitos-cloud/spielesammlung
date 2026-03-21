from maumau.deck import card_suit, card_value, SUITS


class AIPlayer:
    """Smart AI player for Mau-Mau."""

    @staticmethod
    def choose_move(game, player):
        playable = game.get_playable_cards(player)

        if not playable:
            return {'action': 'draw'}

        card = AIPlayer._pick_best_card(playable, player, game)

        wished_suit = None
        if card_value(card) == 'J':
            wished_suit = AIPlayer._pick_best_suit(player, card)

        return {
            'action': 'play',
            'card': card,
            'wished_suit': wished_suit,
        }

    @staticmethod
    def _pick_best_card(playable, player, game):
        hand = player['hand']

        if game.pending_draw > 0:
            sevens = [c for c in playable if card_value(c) == '7']
            if sevens:
                return sevens[0]

        jacks = [c for c in playable if card_value(c) == 'J']
        non_jacks = [c for c in playable if card_value(c) != 'J']

        if not non_jacks:
            return jacks[0]

        scored = []
        for card in non_jacks:
            score = AIPlayer._score_card(card, hand, game)
            scored.append((score, card))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    @staticmethod
    def _score_card(card, hand, game):
        score = 0
        v = card_value(card)
        s = card_suit(card)

        if v == '7':
            score += 15
        elif v == '8':
            score += 12
        elif v == 'A':
            score += 8

        suit_count = sum(1 for c in hand if card_suit(c) == s and c != card)
        score += suit_count * 3

        value_order = {'2': 1, '3': 2, '4': 3, '5': 4, '6': 5,
                       '7': 6, '8': 7, '9': 8, 'T': 9, 'Q': 10, 'K': 11, 'A': 12}
        score += value_order.get(v, 0)

        if len(hand) == 2:
            if v in ('7', '8'):
                score += 20

        return score

    @staticmethod
    def _pick_best_suit(player, jack_card):
        hand = player['hand']
        suit_counts = {s: 0 for s in SUITS}

        for card in hand:
            if card != jack_card:
                s = card_suit(card)
                suit_counts[s] += 1

        best_suit = max(SUITS, key=lambda s: suit_counts[s])
        return best_suit

import random

SUITS = ['H', 'D', 'C', 'S']
VALUES = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']

SUIT_NAMES = {
    'H': 'Herz',
    'D': 'Karo',
    'C': 'Kreuz',
    'S': 'Pik',
}

SUIT_SYMBOLS = {
    'H': '\u2665',
    'D': '\u2666',
    'C': '\u2663',
    'S': '\u2660',
}

VALUE_NAMES = {
    '2': '2', '3': '3', '4': '4', '5': '5', '6': '6',
    '7': '7', '8': '8', '9': '9', 'T': '10',
    'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A',
}

SUIT_COLORS = {
    'H': 'red',
    'D': 'red',
    'C': 'black',
    'S': 'black',
}


def card_suit(card):
    return card[-1]


def card_value(card):
    return card[:-1]


def card_display_value(card):
    v = card_value(card)
    return VALUE_NAMES.get(v, v)


def card_suit_symbol(card):
    return SUIT_SYMBOLS.get(card_suit(card), '')


def card_color(card):
    return SUIT_COLORS.get(card_suit(card), 'black')


def create_deck():
    deck = []
    for suit in SUITS:
        for value in VALUES:
            deck.append(value + suit)
    return deck


def shuffle_deck(deck):
    random.shuffle(deck)
    return deck


def create_shuffled_deck():
    deck = create_deck()
    shuffle_deck(deck)
    return deck

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

SUITS = ["hearts", "diamonds", "clubs", "spades"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

RANK_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10, "A": 11,
}


class GameState(Enum):
    PLAYING = "playing"
    DEALER_TURN = "dealer_turn"
    FINISHED = "finished"


class GameResult(Enum):
    PLAYER_WIN = "player_win"
    DEALER_WIN = "dealer_win"
    TIE = "tie"


@dataclass
class Card:
    suit: str
    rank: str

    @property
    def value(self) -> int:
        return RANK_VALUES[self.rank]

    def to_dict(self) -> dict:
        return {"suit": self.suit, "rank": self.rank, "value": self.value}


HIDDEN_CARD = {"suit": "hidden", "rank": "hidden", "value": 0}


class Deck:
    def __init__(self, num_decks: int = 1):
        self.num_decks = num_decks
        self.cards: list[Card] = []
        self._build()
        self.shuffle()

    def _build(self) -> None:
        self.cards = [
            Card(suit=s, rank=r)
            for _ in range(self.num_decks)
            for s in SUITS
            for r in RANKS
        ]

    def shuffle(self) -> None:
        random.shuffle(self.cards)

    def draw(self) -> Card:
        if not self.cards:
            self._build()
            self.shuffle()
        return self.cards.pop()


@dataclass
class Hand:
    cards: list[Card] = field(default_factory=list)

    @property
    def score(self) -> int:
        total = sum(c.value for c in self.cards)
        # Count aces down as 1 if busting
        aces = sum(1 for c in self.cards if c.rank == "A")
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return total

    @property
    def is_bust(self) -> bool:
        return self.score > 21

    def add(self, card: Card) -> None:
        self.cards.append(card)

    def to_dict(self, hide_from: int | None = None) -> dict:
        cards = []
        for i, c in enumerate(self.cards):
            if hide_from is not None and i >= hide_from:
                cards.append(HIDDEN_CARD)
            else:
                cards.append(c.to_dict())
        visible_score = sum(
            c.value for i, c in enumerate(self.cards)
            if hide_from is None or i < hide_from
        )
        return {
            "cards": cards,
            "score": self.score if hide_from is None else visible_score,
        }


RESULT_MESSAGES = {
    GameResult.PLAYER_WIN: "Du gewinnst!",
    GameResult.DEALER_WIN: "Der Dealer gewinnt!",
    GameResult.TIE: "Unentschieden!",
}


class Game:
    def __init__(self, config: dict | None = None):
        config = config or {}
        self.dealer_stand: int = config.get("dealer_stand", 17)
        self.tie_rule: str = config.get("tie_rule", "dealer")
        num_decks = config.get("num_decks", 1)

        self.deck = Deck(num_decks)
        self.player = Hand()
        self.dealer = Hand()
        self.state = GameState.PLAYING
        self.result: GameResult | None = None

        # Deal initial cards: 2 to player, 2 to dealer
        self.player.add(self.deck.draw())
        self.dealer.add(self.deck.draw())
        self.player.add(self.deck.draw())
        self.dealer.add(self.deck.draw())

        # Check for natural 21
        if self.player.score == 21:
            self._finish_game()

    def hit(self) -> dict:
        if self.state != GameState.PLAYING:
            return self.to_dict()
        self.player.add(self.deck.draw())
        if self.player.is_bust:
            self.state = GameState.FINISHED
            self.result = GameResult.DEALER_WIN
        elif self.player.score == 21:
            self._finish_game()
        return self.to_dict()

    def stand(self) -> dict:
        if self.state != GameState.PLAYING:
            return self.to_dict()
        self._finish_game()
        return self.to_dict()

    def _finish_game(self) -> None:
        self._dealer_play()
        self._determine_winner()
        self.state = GameState.FINISHED

    def _dealer_play(self) -> None:
        while self.dealer.score < self.dealer_stand:
            self.dealer.add(self.deck.draw())

    def _determine_winner(self) -> None:
        if self.player.is_bust:
            self.result = GameResult.DEALER_WIN
        elif self.dealer.is_bust:
            self.result = GameResult.PLAYER_WIN
        elif self.player.score > self.dealer.score:
            self.result = GameResult.PLAYER_WIN
        elif self.player.score < self.dealer.score:
            self.result = GameResult.DEALER_WIN
        else:
            self.result = GameResult.TIE if self.tie_rule == "tie" else GameResult.DEALER_WIN

    def to_dict(self) -> dict:
        hide_dealer = self.state == GameState.PLAYING
        return {
            "player": self.player.to_dict(),
            "dealer": self.dealer.to_dict(hide_from=1 if hide_dealer else None),
            "state": self.state.value,
            "result": self.result.value if self.result else None,
            "message": RESULT_MESSAGES.get(self.result, ""),
        }

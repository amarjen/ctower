#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
todo: test ncurses:    https://mrossinek.gitlab.io/programming/testing-tui-applications-in-python/
"""
import pytest

from ctower.lib.entities import (
    Entity,
    Base,
    Satelite,
    Player,
    Trap,
    Bomb,
    Fruit,
    Lintern,
)
from ctower.lib.entities import Mountain, Mine, Cannon
from ctower.lib.entities import Spawner, Enemy
from ctower.lib.settings import Settings

from ctower.main import Game

from dataclasses import dataclass, field
from playsound import playsound
from itertools import chain
from pathlib import Path

import threading
import random
import curses
import time
import math
import sys
import os


@pytest.fixture
def game():

    game = Game()
    game.base = Base(15, 15)
    game.base.deployed = True
    game.base.gold = 100
    game.player = Player(10, 10)
    game.mines = []
    game.cannons = []
    game.mountains = [
        Mountain(20, 20),
    ]
    game.buildings = []
    game.satelites = []
    game.linterns = []

    game.bombs_activated = []
    return game


class TestMine:
    def test_build_ok(self, game):
        """
        It is only possible to build a Mine in an empty space nearby a mountain
        (distance=1) but not on top of it, and with the influence of the base or
        satellite (d<=10).
        """

        game.player.y, game.player.x = (20, 19)
        game.build_mine()
        assert len(game.mines) == 1

    def test_no_build_on_mountain(self, game):
        game.player.y, game.player.x = (20, 20)
        game.build_mine()
        assert len(game.mines) == 0

    def test_no_build_far_from_mountain(self, game):
        game.player.y, game.player.x = (20, 18)
        game.build_mine()
        assert len(game.mines) == 0

    def test_no_build_far_from_base(self, game):

        game.mountains = [
            Mountain(2, 2),
        ]
        game.player = Player(2, 3)
        game.build_mine()
        assert len(game.mines) == 0

    def test_no_build_on_existing_building(self, game):
        game.player.y, game.player.x = (20, 19)
        game.mines = [
            Mine(20, 19),
        ]

        game.buildings = list(
            chain(
                game.mines,
            )
        )
        game.build_mine()

        ## There should still be only 1 mine
        assert len(game.mines) == 1

    def test_no_build_without_gold(self, game):
        game.base.gold = 0
        game.player.y, game.player.x = (20, 19)
        game.build_mine()
        assert len(game.mines) == 0

    def test_sell_ok(self, game):
        game.player.y, game.player.x = (20, 19)
        game.mines = [
            Mine(20, 19),
        ]

        game.buildings = list(
            chain(
                game.mines,
            )
        )

        game.sell_building()
        assert len(game.mines) == 0

    def test_no_sell_from_different_location(self, game):
        game.player.y, game.player.x = (10, 10)
        game.mines = [
            Mine(10, 11),
        ]

        game.buildings = list(
            chain(
                game.mines,
            )
        )

        game.sell_building()
        assert len(game.mines) == 1


class TestCannon:
    def test_build_ok(self, game):
        """
        It is only possible to build a Cannon in an empty space nearby a mountain
        (distance=1) but not on top of it, and with the influence of the base or
        satellite (d<=10).
        """

        game.base.gold = 50
        game.player.y, game.player.x = (20, 19)
        game.build_cannon()
        assert len(game.cannons) == 1

    def test_no_build_on_mountain(self, game):
        game.player.y, game.player.x = (20, 20)
        game.build_cannon()
        assert len(game.cannons) == 0

    def test_no_build_on_existing_building(self, game):
        game.player.y, game.player.x = (20, 19)
        game.cannons = [
            Cannon(20, 19),
        ]

        game.buildings = list(
            chain(
                game.cannons,
            )
        )
        game.build_cannon()

        ## There should still be only 1 mine
        assert len(game.cannons) == 1

    def test_no_build_far_from_base(self, game):
        game.player.y, game.player.x = (2, 3)
        game.build_cannon()
        assert len(game.cannons) == 0

    def test_no_build_without_gold(self, game):
        game.base.gold = 0
        game.player.y, game.player.x = (20, 19)
        game.build_cannon()
        assert len(game.cannons) == 0

    def test_sell_ok(self, game):
        game.player.y, game.player.x = (20, 19)
        game.cannons = [
            Cannon(20, 19),
        ]

        game.buildings = list(
            chain(
                game.cannons,
            )
        )

        game.sell_building()
        assert len(game.cannons) == 0

    def test_no_sell_from_different_location(self, game):
        game.player.y, game.player.x = (10, 10)
        game.cannons = [
            Cannon(10, 11),
        ]

        game.buildings = list(
            chain(
                game.cannons,
            )
        )

        game.sell_building()
        assert len(game.cannons) == 1


class TestLantern:
    def test_build_lantern_ok(self, game):
        game.base.gold = 100
        game.player.y, game.player.x = (20, 19)
        game.build_lantern()
        assert len(game.linterns) == 1

    def test_no_build_lantern_without_gold(self, game):
        game.base.gold = 0
        game.player.y, game.player.x = (20, 19)
        game.build_lantern()
        assert len(game.linterns) == 0


class TestBombs:
    def test_throw_bomb(self, game):
        game.player.bombs = 1
        game.throw_bomb()
        assert game.player.bombs == 0

    def test_no_throw_bomb_empty_inventory(self, game):
        game.player.bombs = 0
        game.throw_bomb()
        assert game.player.bombs == 0


class TestBuildings:
    def test_upgrade(self, game):
        game.player.y, game.player.x = (20, 19)

        game.cannons = [
            Cannon(20, 19),
        ]

        game.buildings = list(
            chain(
                game.cannons,
            )
        )

        building = game.buildings[0]

        for lvl in range(1, 9):
            game.base.gold = building.cost_to_upgrade()
            game.upgrade_building()
            assert building.level == lvl + 1

    def test_no_upgrade_without_gold(self, game):
        game.player.y, game.player.x = (20, 19)

        game.cannons = [
            Cannon(20, 19, level=1),
        ]

        game.buildings = list(
            chain(
                game.cannons,
            )
        )

        building = game.buildings[0]

        for lvl in range(1, 9):
            game.base.gold = building.cost_to_upgrade() - 1
            game.upgrade_building()
            assert building.level == 1

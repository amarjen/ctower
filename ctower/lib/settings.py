#!/usr/bin/env python
# -*- coding: utf-8 -*-


class Settings:
    FPS: int = 50
    PLAYER_VISIBILITY: int = 5
    BASE_VISIBILITY: int = 10
    SATELITE_VISIBILITY: int = 10
    SPAWNER_CHANCE: int = 5
    ENEMY_VISIBILITY: int = 30
    INITIAL_GOLD: int = 100
    MINE_INITIAL_COST: int = 50
    CANNON_INITIAL_COST: int = 50
    SATELITE_INITIAL_COST: int = 50

    MINE_PRODUCTION_RATE: float = 10
    MINE_PRODUCTION_FACTOR: float = 1.5
    MINE_MAINTENANCE_COST: int = 0
    MINE_TIMER: int = 4

    CANNON_PRODUCTION_RATE: float = 1.5
    CANNON_PRODUCTION_FACTOR: float = 1.5
    CANNON_MAINTENANCE_COST: int = 1
    CANNON_TIMER: int = 2

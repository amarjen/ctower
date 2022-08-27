# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from .settings import Settings
import time
import math


@dataclass
class Entity:
    """
    Game Entity Base Class
    """

    y: int
    x: int
    kind: str = ""
    color: int = 1  # default color
    symbol: None = None
    deployed: bool = True
    visible: bool = True
    level: int = 10
    health: int = 10

    def distance(self, other):
        """
        return the euclidean distance between 2 elements
        """
        return int(math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2))


@dataclass
class Mountain(Entity):
    kind: str = "Mountain"
    symbol: str = "^"
    resource: str = "Gold"
    color: int = 11


@dataclass
class Building(Entity):
    base_cost: int = 50
    production_rate: int = 1.5
    production_factor: int = 1.5
    maintenance_cost: int = 1
    timer: int = 5
    clock: float = field(default_factory=time.time)
    visible: bool = True

    def cost_to_upgrade(self):
        return self.base_cost + self.base_cost * (2 ** (self.level - 1))

    def cost_to_recover(self):
        return sum(
            int(self.base_cost + self.base_cost * (2 ** (lvl - 2))) // 2
            for lvl in range(1, self.level + 1)
        )

    def _process(self):
        if time.time() - self.clock > self.timer:
            self.clock = time.time()
            return True
        else:
            return False

    @property
    def time_pending(self):
        return f"{self.timer - (time.time() - self.clock):0.2}"

    def upgrade(self):
        self.level += 1
        self.health = 5 * self.level
        self.production_rate = int(self.production_rate * self.production_factor)
        self.maintenance_cost += self.level
        self.timer = max(1, self.timer - 0.5)
        self._update_symbol()

    def _update_symbol(self):
        """
        define in each instance of building if different
        """
        pass


@dataclass
class Mine(Building):
    kind: str = "Mine"
    symbol: str = "1"
    resource: str = "Gold"
    level: int = 1
    health: int = 5
    production_factor: float = Settings.MINE_PRODUCTION_FACTOR
    production_rate: float = Settings.MINE_PRODUCTION_RATE
    maintenance_cost: int = Settings.MINE_MAINTENANCE_COST
    timer: int = Settings.MINE_TIMER

    def dig_success(self):
        return self._process()

    @property
    def dig_value(self):
        return self.production_rate * self.level

    def _update_symbol(self):
        self.symbol = str(self.level)
        if self.level > 2:
            self.color = 15


@dataclass
class Cannon(Building):
    kind: str = "Cannon"
    symbol: str = "I"
    level: int = 1
    kills: int = 0
    health: int = 6
    production_factor: float = Settings.CANNON_PRODUCTION_FACTOR  # factor for upgrade
    production_rate: float = Settings.CANNON_PRODUCTION_RATE  # distance
    timer: int = Settings.CANNON_TIMER  # speed

    def shot_success(self):
        return self._process()

    def _update_symbol(self):
        symbols = "I V X D I V X D C".split(" ")
        self.symbol = symbols[self.level - 1]
        if self.level > 4:
            self.color = 15


@dataclass
class Enemy(Entity):
    symbol: int = 4194430  # curses.ACS_BULLET
    kind: str = "Zombie"
    color: int = 5
    health: int = 2
    level: int = 1

    def move(self, new_y, new_x):
        self.y = new_y
        self.x = new_x


@dataclass
class Spawner(Entity):
    symbol: str = "#"
    kind: str = "Spawner"
    health: int = 10
    level: int = 10
    color: int = 5

    def spawn(self):
        return Enemy(self.y, self.x)


@dataclass
class Fruit(Entity):
    symbol: int = 4194409  # curses.ACS_LANTERN
    color: int = 3


@dataclass
class Base(Entity):
    kind: str = "Base"
    deployed: bool = False
    visible: bool = True
    health: int = 100
    gold: int = 100
    symbol: int = 4194400  # curses.ACS_DIAMOND
    color: int = 7


@dataclass
class Satelite(Entity):
    kind: str = "Satelite"
    visible: bool = True
    health: int = 10
    symbol: int = 4194400  # curses.ACS_DIAMOND
    color: int = 17


@dataclass
class Lintern(Entity):
    visible: bool = True
    symbol: str = "@"
    color: int = 17


@dataclass
class Trap(Entity):
    deployed: bool = False
    symbol: str = "%"


@dataclass
class Player(Entity):
    kind: str = "Player"
    dir_y: int = 0
    dir_x: int = 0
    world_limits: tuple = None
    health: int = 100
    points: int = 0
    bombs: int = 2
    level: int = 1
    symbol: str = "*"
    color: int = 13
    visible: bool = True

    def move(self, dy=0, dx=0):
        min_y, max_y, min_x, max_x = self.world_limits

        self.dir_y = math.copysign(1, dy)
        self.dir_x = math.copysign(1, dx)

        self.y = max(min_y, min(max_y, self.y + dy))
        self.x = max(min_x, min(max_x, self.x + dx))


@dataclass
class Bomb(Entity):
    symbol: str = "+"
    strength: int = 5
    timer: int = 2
    t0: float = field(default_factory=time.time)

    @property
    def area(self) -> set:
        s = self.strength
        return set(
            (self.y + dy, self.x + dx)
            for dy in range(-s, s + 1)
            for dx in range(-s, s + 1)
            if int(
                math.sqrt((self.x - (self.x + dx)) ** 2 + (self.y - (self.y + dy)) ** 2)
            )
            <= s
        )

    @property
    def is_kaboom(self):
        """
        check if timer is over and returns True to handle bomb self destruction, or False otherwise
        """

        return time.time() - self.t0 > self.timer

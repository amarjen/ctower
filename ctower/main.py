#!/usr/bin/env python
# -*- coding: utf-8 -*

from .lib.elements import Base, Player, Trap, Bomb, Fruit
from .lib.elements import Mountain, Mine, Cannon
from .lib.elements import Spawner, Enemy

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

FPS = 50

@dataclass
class Game:
    screen = None

    @classmethod
    def create(cls):
        game = cls()
        return game

    def init(self, screen):
        
        self.screen = screen

        # Curses Settings
        curses.curs_set(False) # Do not display blinking cursor
        curses.noecho()
        curses.cbreak()
        curses.start_color()

        # Curses Color Pairs
        curses.init_color(curses.COLOR_BLACK,0,100,100)
        curses.init_pair(1, 250, 0) # Default Color
        curses.init_pair(2, 137, 236) 

        curses.init_pair(3, curses.COLOR_MAGENTA, 0) # FRUIT
        curses.init_pair(4, curses.COLOR_MAGENTA, 243) # FRUIT

        curses.init_pair(5, curses.COLOR_YELLOW, 0) # ENEMIES
        curses.init_pair(6, curses.COLOR_YELLOW, 243) # ENEMIES

        curses.init_pair(7, curses.COLOR_GREEN, 0) # BASE
        curses.init_pair(8, curses.COLOR_GREEN, 243) # BASE

        curses.init_pair(9, curses.COLOR_BLUE, 0) # ENEMY TRAPPED
        curses.init_pair(10, curses.COLOR_BLUE, 243) # ENEMY TRAPPED
        
        curses.init_pair(11, curses.COLOR_RED, 0) # MOUNTAIN
        curses.init_pair(12, curses.COLOR_RED, 243) # MOUNTAIN

        curses.init_pair(13, 25, 231)  # PLAYER
        curses.init_pair(14, 25, 247)  # PLAYER

        curses.init_pair(15, 199, 0) # ENEMY TRAPPED
        curses.init_pair(16, 199, 243) # ENEMY TRAPPED

        # Screen Settings
        self.screen.keypad(True)
        self.screen.nodelay(True)
        self.screen.border(0)

        self.min_y, self.min_x = (2, 2)
        self.max_y, self.max_x = tuple(i-j for i,j in zip(self.screen.getmaxyx(),
                                                          (5,2) ))

        # Draw Window Borders
        self.screen.addch(self.max_y+1, 0, curses.ACS_SSSB)
        self.screen.addch(self.max_y+1, self.max_x+1, curses.ACS_SBSS)

        for x in range(1,self.max_x+1):
            self.screen.addch(self.max_y+1, x, curses.ACS_HLINE)

        # Game Elements
        self.player = Player(20, 20)
        self.trap = Trap(20, 20)
        self.base = Base( self.max_y//2, self.max_x//2 , deployed = False)

        self.mountains = [
            Mountain( y, x ) for y, x in [
                (
                    random.randint(self.min_y, self.max_y),
                    random.randint(self.min_x, self.max_x)
                ) for i in range(10)
            ]
        ]

        self.spawners= [
            Spawner( y, x ) for y, x in [
                (
                    random.randint(self.min_y, self.max_y),
                    random.randint(self.min_x, self.max_x)
                ) for i in range(40)
            ]
        ]

        self.mines = []
        self.cannons = []
        self.enemies = []
        self.fruits = []
        self.bombs_topick = []
        self.bombs_activated = []

        self.loop()


    def loop(self):

        area = { (y, x) for y in range(self.min_y, self.max_y+1) for x in range(self.min_x, self.max_x+1)}
        clock = time.time()
        while True:

            buildings = list( chain(self.mines, self.cannons) )

            area_light = set(surronding_area(self.player, 5, self.min_y, self.max_y, self.min_x, self.max_x))
            if self.base.deployed:
                area_light = set(chain(area_light,
                               surronding_area(self.base, 10, self.min_y, self.max_y, self.min_x, self.max_x)))

            area_dark = area.difference( area_light )

            self.render_fog ( area_light, method = "remove" )
            

            for item in chain(self.mountains,
                              buildings,
                              self.enemies,
                              self.spawners,
                              self.fruits,
                              self.bombs_activated,
                              self.bombs_topick,
                              [self.base, self.player, self.trap],):

                if (item.y, item.x) in area_light:
                    self.render(item)

            self.render_fog ( area_dark )
            
            ## Process Buildings (Mine -> Dig, Cannon -> Shoot...)
            ## , unless they are destroyed by an enemy
            for building in buildings:
                if building.health <= 0:
                    buildings.remove(building)
                    self.erase(building)

                    if building.kind == "Mine":
                        self.mines.remove(building)
                        
                    elif building.kind == "Cannon":
                        self.cannons.remove(building)

                else:
                    if building.kind == "Mine" and building.dig_success():
                        self.base.gold += building.dig_value

                    elif building.kind == "Cannon" and building.shot_success():
                        target = nearby_elements(building,
                                                 self.enemies,
                                                 d = building.production_rate,
                                                 ret='choice')

                        if target is not None \
                                and target in self.enemies:
                            self.enemies.remove(target)
                            self.erase(target)
                            self.player.points += 1
                            building.kills += 1

            ## Spawn Enemies
            if random.randint(0, 1000) < 10:
                s = random.choice(self.spawners)
                self.enemies.append( s.spawn() )

            ## Enemies movements
            if time.time() > clock + max(0.2, 1 - self.player.level / 12 ):
                for enemy in self.enemies:

                    ## scan targets
                    targets = [{'target': target, 'd': enemy.distance(target)} for target in chain(buildings, [self.base, self.player,]) ]

                    if len(targets) > 0:
                        # choose the nearest target and moves towards it
                        # TODO: Set weight to target kinds
                        target = sorted(targets, key=lambda x: x['d'])[0]['target']

                        if target.x - enemy.x > 0:
                            delta_x = 1
                        elif target.x - enemy.x < 0:
                            delta_x = -1

                        if target.y - enemy.y > 0:
                            delta_y = 1
                        elif target.y - enemy.y < 0:
                            delta_y = -1

                    else:
                        delta_y = random.randint( -1, 1 )
                        delta_x = random.randint( -1, 1 )

                    if (enemy.y, enemy.x) in area_light:
                        self.erase(enemy)

                    enemy.move(max(1, min(self.max_y, enemy.y + delta_y)),
                               max(1, min(self.max_x, enemy.x + delta_x)))

                    # check collision with player
                    if collision(self.player, enemy):
                        combat_result = random.randint(0,99)
                        if combat_result < 80 and enemy in self.enemies:
                            play_sound("pos")
                            self.enemies.remove(enemy)
                            self.player.points += 1
                            self.player.health -= random.randint(0, 2)

                        else:
                            play_sound("scream_fight")
                            self.player.health -= random.randint(5, 10)

                    # check collision with buildings
                    for building in buildings:
                        if collision(enemy, building):
                            building.health -= 1

                    # check collision with base
                    if collision(self.base, enemy) and enemy in self.enemies:
                        self.enemies.remove(enemy)
                        self.player.points += 1
                        self.base.health -= random.randint(0, 2)

                    if self.trap.deployed:
                        if distance(self.trap, enemy) <= 5\
                                and enemy in self.enemies:
                            self.enemies.remove(enemy)
                            enemy.color = 9
                            self.render(enemy)

                clock = time.time()


            delta_x = delta_y = 0

            ## Check Bombs
            if len(self.bombs_activated) > 0:
                for bomb in self.bombs_activated:

                    for (y, x) in bomb.area:
                        if (y > 0 and y < self.max_y) \
                                and ( x > 0 and x < self.max_x):
                            self.screen.addstr(y, x, '~', curses.color_pair(2))

                    if bomb.is_kaboom:
                        play_sound("kaboom")
                        
                        victims = nearby_elements(bomb, chain(self.enemies, self.spawners),
                                                  d = bomb.strength)

                        if victims is not None:
                            for victim in victims:
                                victim.health -= 5

                        if (self.player.y,self.player.x) in bomb.area:
                            play_sound("scream-bomb")
                            self.player.health -= 50


                        for (y, x) in bomb.area:
                            if (y > 0 and y < self.max_y)\
                                    and (x > 0 and x < self.max_x - 1):
                                self.clear(y, x)

                        self.bombs_activated.remove(bomb)
                        self.erase(bomb)
                        self.screen.refresh()

            for enemy in chain(self.enemies, self.spawners):
                if enemy.health < 0 and enemy in chain(self.enemies, self.spawners):
                    if enemy.kind == 'Zombie':
                        self.enemies.remove(enemy)
                    elif enemy.kind == 'Spawner':
                        self.spawners.remove(enemy)

                    self.erase(enemy)
                    self.player.points += enemy.level


            ## Recover Trap
            if self.trap.deployed and distance(self.trap, self.player) == 0:
                self.trap.deployed = False

            ## Fruit Spawner
            if random.randint(0, 1000) < 2:
                self.fruits.append(Fruit(random.randint(self.min_y, self.max_y),
                                    random.randint(self.min_x, self.max_x)))

            ## Bombs Spawner
            if random.randint(0, 1000) < 1:
                self.bombs_topick.append(Bomb(random.randint(self.min_y, self.max_y),
                                    random.randint(self.min_x, self.max_x)))

            ## Fruit check for collision
            if len(self.fruits) > 0:
                for fruit in self.fruits:
                    if collision(self.player, fruit):
                        play_sound("bonus")
                        self.player.health += 10
                        self.fruits.remove(fruit)

            if len(self.bombs_topick) > 0:
                for bomb in self.bombs_topick:
                    if collision(self.player, bomb):
                        play_sound("bonus")
                        self.player.bombs += 1
                        self.bombs_topick.remove(bomb)


            # Wait for a keystroke
            key = self.screen.getch()

            # Process the keystroke
            if key is not curses.ERR:
                if key == ord('q'):
                    break

                if key == ord('p'):
                    self.pause()

                if key in [ord('h'), curses.KEY_LEFT]:
                    self.player.to_move = True
                    delta_x = -1

                if key in [ord('l'), curses.KEY_RIGHT]:
                    self.player.to_move = True
                    delta_x = 1

                if key in [ord('k'), curses.KEY_UP]:
                    self.player.to_move = True
                    delta_y = -1

                if key in [ord('j'), curses.KEY_DOWN]:
                    self.player.to_move = True
                    delta_y = 1

                if key == ord('b'):
                    # deploy bomb
                    if self.player.bombs > 0:
                        self.bombs_activated.append(Bomb(self.player.y,self.player.x))
                        self.player.bombs -= 1

                if key == ord('m'):
                    # build mine, in the distance of 1 of a mine, but not ontop and
                    # not possible in an already built mine
                    if self.base.deployed \
                            and nearby_elements(self.player, chain(buildings, self.mountains, [self.base,]))  is None  \
                            and min(self.player.distance(mnt) for mnt in self.mountains) == 1 \
                            and self.base.gold >= 50:
                        self.base.gold -= 50
                        self.mines.append(Mine(self.player.y,self.player.x))

                if key == ord('c'):
                    # build cannon
                    # not possible in an already built mine
                    if self.base.deployed \
                            and nearby_elements(self.player, chain(buildings, self.mountains, [self.base,])) is None \
                            and self.base.gold >= 50:
                        self.base.gold -= 50
                        self.cannons.append(Cannon(self.player.y,self.player.x))

                if key == ord('u'):
                    # upgrade building
                    building = nearby_elements(self.player, buildings, ret = 'one')

                    if building is not None \
                            and building.level < 9:
                        cost = building.cost_to_upgrade()
                        if self.base.gold >= cost:
                            self.base.gold -= cost
                            building.upgrade()

                if key == ord('s'):
                    # sell building
                    building = nearby_elements(self.player, buildings, ret = 'one')
                    if building is not None:
                        self.base.gold += building.cost_to_recover()
                        buildings.remove(building)
                        if building.kind == 'Mine':
                            self.mines.remove(building)
                        elif building.kind == 'Cannon':
                            self.cannons.remove(building)

                if key == ord('v'):
                    # deploy base
                    if not self.base.deployed:
                        self.base.deployed = True
                        self.base.y = self.player.y
                        self.base.x = self.player.x
 
                if key == ord(' '):
                    # deploy trap
                    if self.trap.deployed == False:
                        self.trap.deployed = True
                        self.trap.y = self.player.y +self.player.dir_y * 2
                        self.trap.x = self.player.x +self.player.dir_x * 2
                      
            if self.player.to_move:
                self.erase(self.player)
                self.player.move(max(1, min(self.max_y,self.player.y + delta_y)),
                            max(1, min(self.max_x, self.player.x + delta_x)))
                delta_x = delta_y = 0
                self.player.to_move = False

            self.print_stats()

            # Gameover Condition
            if self.player.health <= 0 \
                    or self.base.health <= 0 \
                    or (self.base.gold < 50 and len(self.mines) == 0):
                self.gameover()

            # Gamewon Condition
            if self.player.level > 10 \
                    and self.trap.deployed \
                    and distance(self.base, self.trap) <= 3 \
                    and distance(self.base, self.player) <= 3 \
                    and len(self.enemies) < 2:
                self.gamewon()

            self.screen.refresh()
            curses.napms( 1000 // FPS )

    def panic(self):
        pass

    def print_stats(self):
            # print stats
            place = nearby_elements(self.player, chain(self.mines, self.cannons, self.mountains, [self.base, ]), ret='one')

            stats_line0 =  f"Coord: ({self.player.y:3},{self.player.x:3})"
            if place is not None:
                if place.kind == 'Mine':
                    stats_line0 += f"  Place: {place.kind}, lvl: {place.level}, production: {place.production_rate}, health: {place.health}, cost to (u)pgrade: {place.cost_to_upgrade()}, (s)ell for {place.cost_to_recover()}"
                    stats_line0 += f"  Time: {place.time_pending}"

                elif place.kind == 'Cannon':
                    stats_line0 += f"  Place: {place.kind}, lvl: {place.level}, kills: {place.kills}, health: {place.health}, cost to (u)pgrade: {place.cost_to_upgrade()}"
                    stats_line0 += f"  Time: {place.time_pending}"
 
                else:
                    stats_line0 += f"  Place: {place.kind}, lvl: {place.level}, health: {place.health}"

            stats_line1 =  f"Level: {self.player.level:2}     "
            stats_line1 += f"Health: {self.player.health:3}     "
            stats_line1 += f"Points: {self.player.points:3}     "
            stats_line1 += f"Base Health: {self.base.health:3}     "
            stats_line1 += f"Gold: {self.base.gold:4}     "
            stats_line1 += f"Enemies: {len(self.enemies):3}     "
            stats_line1 += f"Bombs: {self.player.bombs:3}"
            

            self.screen.addstr(self.max_y +2, 23, 138*" ")
            self.screen.addstr(self.max_y +2, 5, stats_line0)
            self.screen.addstr(self.max_y +3, 23, stats_line1)

            self.player.level =self.player.points // 20 + 1


    def pause(self, key_continue = None):
        while True:
            key = self.screen.getch()
            if key is not curses.ERR:
                if key_continue is not None:
                    if key == ord(key_continue):
                        break
                else:
                    break

    def gameover(self):
        self.screen.addstr(self.max_y//2, self.max_x//2, "¡¡¡ GAME OVER !!!", curses.A_BLINK)
        self.pause('q')
        sys.exit()

    def gamewon(self):
        self.screen.addstr(self.max_y//2, self.max_x//2, "¡¡¡ CONGRATULATIONS, YOU WON !!!", curses.A_BLINK)
        self.screen.addstr(self.max_y//2+1, self.max_x//2, "This is very impresive.", curses.A_BLINK)
        self.pause('q')
        sys.exit()

    def erase(self, element):
        """
        Erase element position
        """
        self.clear(element.y, element.x)

    def clear(self, y, x):
        self.screen.addch(y, x, ' ', curses.color_pair(1))

    def render(self, element, *args, **kwargs):
        """
        render elements in screen
        """

        if not element.deployed or not element.visible:
            return

        c = element.color

        if 'symbol' not in kwargs.keys():
            symbol = None

        else:
            symbol = kwargs['symbol']

        if element.symbol is None and symbol is None:
            print("Element has not symbol defined, this it is not drawable")
            raise BaseException

        if symbol is None: # and element.color is not None:
            self.screen.addch(element.y,
                              element.x,
                              element.symbol,
                              curses.color_pair(c) )
        else:
            self.screen.addch(element.y,
                              element.x,
                              symbol,
                              curses.color_pair(c))

    def render_fog(self, area, method = 'set' ):
        if method == 'set':
            for (y, x) in area:
                self.screen.addch(y, x, '-', curses.color_pair(2))

        elif method == 'remove':
            for (y, x) in area:
                self.screen.addch(y, x, ' ', curses.color_pair(1))

def distance(objA, objB):
    return objA.distance(objB)

def surronding_area(obj, distance,  min_y, max_y, min_x, max_x, includes_self = True):
        area = [( max(min_y, min(max_y, (obj.y + dy))),
                  max(min_x, min(max_x, (obj.x + dx))) ) \
                for dy in range(-distance, distance + 1) \
                for dx in range(-distance, distance + 1) \
                if int(
                    math.sqrt(
                        (obj.y-(obj.y + dy))**2 + (obj.x-(obj.x+dx))**2
                    )
                ) <= distance ]
    
        if not includes_self:
            area = set(area).difference({(obj.y, obj.x)})

        return list(area)

def is_inside(obj, area):
    return {(obj.y, obj.x)} in area

def collision(objA, objB):
    return objA.distance(objB) == 0

def nearby_elements(objA, lst, d = 0, ret='all'):
    """
    returns nearby elements from lst within d distance of objA
    """
    result = [objB for objB in lst if objB.distance(objA)<=d]

    if len(result) == 0:
        return None

    if ret == "all":
        return result

    elif ret == "one":
        return result[0]

    elif ret == "choice":
        return random.choice(result)

def play_sound(asset):
    f = Path(f"./assets/{asset}.mp3")
    if not f.is_file():
        f = Path(f"./assets/{asset}.wav")

    if f.is_file():
        threading.Thread(target=playsound, args=(f,), daemon=True).start()

def start():
    game = Game.create()
    curses.wrapper(game.init)
    
if __name__ == "__main__":
    start()

# -*- coding: utf-8 -*-
"""
麻将游戏引擎
"""

import random
from typing import List, Optional, Dict, Callable, Tuple, Any
from enum import Enum

from .tile import Tile, TileType
from .deck import Deck
from .player import Player, PlayerType
from rules.sichuan_rule import SichuanRule
from rules.base_rule import BaseRule
from utils.logger import setup_logger

class GameState(Enum):
    """游戏状态"""
    WAITING = "waiting"
    DEALING = "dealing"
    TILE_EXCHANGE = "tile_exchange"
    MISSING_SUIT_SELECTION = "missing_suit_selection"
    PLAYING = "playing"
    WAITING_ACTION = "waiting_action"
    GAME_OVER = "game_over"

class GameMode(Enum):
    """游戏模式"""
    TRAINING = "training"
    COMPETITIVE = "competitive"

class GameAction(Enum):
    """游戏动作"""
    DISCARD = "discard"
    PENG = "peng"
    GANG = "gang"
    CHI = "chi"
    WIN = "win"
    PASS = "pass"

class GameEngine:
    """游戏引擎"""
    
    def __init__(self):
        self.logger = setup_logger("game_engine")
        
        # 游戏状态
        self.state = GameState.WAITING
        self.mode = GameMode.COMPETITIVE
        self.rule_type = "sichuan"
        
        # 游戏组件
        self.deck: Optional[Deck] = None
        self.rule: Optional[BaseRule] = None
        self.players: List[Player] = []
        self.current_player_index = 0
        
        # 游戏数据
        self.round_number = 0
        self.last_discarded_tile: Optional[Tile] = None
        self.last_discard_player: Optional[Player] = None
        self.game_history: List[Dict] = []
        
        # 回调函数
        self.on_game_state_changed: Optional[Callable] = None
        self.on_player_action: Optional[Callable] = None
        self.on_game_over: Optional[Callable] = None
        
        # 换三张相关
        self.exchange_tiles: Dict[int, List[Tile]] = {}  # 玩家选择的换牌
        self.exchange_direction = 1  # 1为顺时针，-1为逆时针
        
        # 缺一门相关
        self.missing_suits: Dict[int, Optional[TileType]] = {}  # 玩家选择的缺门
        
        # 血战到底相关
        self.winners: List[int] = []  # 已胡牌的玩家索引
        self.active_players: List[int] = []  # 仍在游戏中的玩家索引
        
        self.logger.info("游戏引擎初始化完成")
    
    def setup_game(self, mode: GameMode, rule_type: str = "sichuan"):
        """设置游戏"""
        self.mode = mode
        self.rule_type = rule_type
        
        # 创建规则
        if rule_type == "sichuan":
            self.rule = SichuanRule()
        elif rule_type == "national":
            from rules.national_rule import NationalRule
            self.rule = NationalRule()
        else:
            self.rule = SichuanRule()  # 默认四川麻将
        
        # 创建牌堆
        self.deck = Deck(rule_type)
        
        # 创建玩家
        self.players = []
        if mode == GameMode.TRAINING:
            # 训练模式：1个人类玩家 + 1个训练AI + 2个普通AI
            self.players.append(Player("玩家", PlayerType.HUMAN, 0))
            self.players.append(Player("训练师", PlayerType.AI_TRAINER, 1))
            self.players.append(Player("AI-1", PlayerType.AI_MEDIUM, 2))
            self.players.append(Player("AI-2", PlayerType.AI_MEDIUM, 3))
        else:
            # 竞技模式：1个人类玩家 + 3个AI
            self.players.append(Player("玩家", PlayerType.HUMAN, 0))
            self.players.append(Player("AI-1", PlayerType.AI_HARD, 1))
            self.players.append(Player("AI-2", PlayerType.AI_HARD, 2))
            self.players.append(Player("AI-3", PlayerType.AI_HARD, 3))
        
        self.state = GameState.WAITING
        self.logger.info(f"游戏设置完成: {mode.value}, {rule_type}")
    
    def start_new_game(self):
        """开始新游戏"""
        if not self.deck or not self.rule or not self.players:
            self.logger.error("游戏未正确设置")
            return False
        
        # 重置游戏状态
        self.round_number += 1
        self.current_player_index = 0
        self.last_discarded_tile = None
        self.last_discard_player = None
        
        # 重置玩家
        for player in self.players:
            player.reset()
        
        # 重置牌堆
        self.deck.reset()
        
        # 开始发牌
        self.state = GameState.DEALING
        self._deal_initial_cards()
        
        # 选择缺门（四川麻将）
        if self.rule_type == "sichuan":
            self.state = GameState.TILE_EXCHANGE
            self._start_tile_exchange()
        else:
            self.state = GameState.PLAYING
            self._start_playing()
        
        self._notify_state_changed()
        
        self.logger.info(f"新游戏开始，第{self.round_number}轮")
        return True
    
    def _deal_initial_cards(self):
        """发初始手牌"""
        hand_size = self.rule.get_initial_hand_size()
        
        for player in self.players:
            tiles = self.deck.draw_multiple(hand_size)
            player.add_tiles(tiles)
        
        # 庄家多摸一张
        dealer = self.players[0]  # 第一个玩家是庄家
        extra_tile = self.deck.draw_tile()
        if extra_tile:
            dealer.add_tile(extra_tile)
        
        self.logger.info("发牌完成")
    
    def _start_tile_exchange(self):
        """开始换三张阶段"""
        # 随机决定换牌方向
        self.exchange_direction = random.choice([1, -1])
        direction_text = "顺时针" if self.exchange_direction == 1 else "逆时针"
        
        self.logger.info(f"换三张阶段开始，方向: {direction_text}")
        
        # 清空之前的换牌选择
        self.exchange_tiles = {}
        
        # 通知所有玩家开始选择换牌
        for player in self.players:
            if hasattr(player, 'on_tile_exchange_start'):
                player.on_tile_exchange_start(self.exchange_direction)
    
    def submit_exchange_tiles(self, player_id: int, tiles: List[Tile]) -> bool:
        """
        提交换牌选择
        
        Args:
            player_id: 玩家ID
            tiles: 选择的三张牌
            
        Returns:
            是否成功提交
        """
        if self.state != GameState.TILE_EXCHANGE:
            return False
        
        if player_id not in range(4):
            return False
        
        if len(tiles) != 3:
            self.logger.error(f"玩家 {player_id} 换牌数量错误: {len(tiles)}")
            return False
        
        # 检查是否为同花色
        if not self._is_same_suit(tiles):
            self.logger.error(f"玩家 {player_id} 换牌不是同花色")
            return False
        
        # 检查玩家是否拥有这些牌
        player = self.players[player_id]
        for tile in tiles:
            if not player.has_tile_in_hand(tile):
                self.logger.error(f"玩家 {player_id} 没有牌: {tile}")
                return False
        
        self.exchange_tiles[player_id] = tiles
        self.logger.info(f"玩家 {player_id} 提交换牌: {[str(t) for t in tiles]}")
        
        # 检查是否所有玩家都已提交
        if len(self.exchange_tiles) == 4:
            self._execute_tile_exchange()
        
        return True
    
    def _is_same_suit(self, tiles: List[Tile]) -> bool:
        """检查牌是否为同花色"""
        if not tiles:
            return True
        
        first_suit = tiles[0].tile_type
        return all(tile.tile_type == first_suit for tile in tiles)
    
    def _execute_tile_exchange(self):
        """执行换牌"""
        self.logger.info("执行换牌操作")
        
        # 从玩家手牌中移除要换的牌
        removed_tiles = {}
        for player_id, tiles in self.exchange_tiles.items():
            player = self.players[player_id]
            removed_tiles[player_id] = []
            for tile in tiles:
                if player.remove_tile_from_hand(tile):
                    removed_tiles[player_id].append(tile)
        
        # 按方向分发牌
        for player_id in range(4):
            if player_id in removed_tiles:
                # 计算目标玩家ID
                target_player_id = (player_id + self.exchange_direction) % 4
                target_player = self.players[target_player_id]
                
                # 将牌给目标玩家
                for tile in removed_tiles[player_id]:
                    target_player.add_tile_to_hand(tile)
        
        # 重新排序手牌
        for player in self.players:
            player.sort_hand()
        
        self.logger.info("换牌完成")
        
        # 进入选择缺一门阶段
        self.state = GameState.MISSING_SUIT_SELECTION
        self._start_missing_suit_selection()
    
    def _start_missing_suit_selection(self):
        """开始选择缺一门阶段"""
        self.logger.info("开始选择缺一门")
        
        # 清空之前的选择
        for player_id in self.missing_suits:
            self.missing_suits[player_id] = None
        
        # 通知所有玩家选择缺门
        for player in self.players:
            if hasattr(player, 'on_missing_suit_selection_start'):
                player.on_missing_suit_selection_start()
    
    def submit_missing_suit(self, player_id: int, suit: TileType) -> bool:
        """
        提交缺一门选择
        
        Args:
            player_id: 玩家ID
            suit: 选择缺少的花色
            
        Returns:
            是否成功提交
        """
        if self.state != GameState.MISSING_SUIT_SELECTION:
            return False
        
        if player_id not in range(4):
            return False
        
        # 四川麻将只能选择万、筒、条
        if suit not in [TileType.WAN, TileType.TONG, TileType.TIAO]:
            return False
        
        self.missing_suits[player_id] = suit
        self.logger.info(f"玩家 {player_id} 选择缺 {suit.value}")
        
        # 检查是否所有玩家都已选择
        if all(suit is not None for suit in self.missing_suits.values()):
            self._start_playing()
        
        return True
    
    def _start_playing(self):
        """开始游戏阶段"""
        self.state = GameState.PLAYING
        self.current_player_index = 0
        
        # 庄家摸第一张牌
        if self.active_players:
            first_player = self.players[self.current_player_index]
            tile = self.deck.draw_tile()
            if tile:
                first_player.add_tile_to_hand(tile)
                first_player.sort_hand()
        
        self.logger.info("游戏阶段开始")
    
    def get_current_player(self) -> Player:
        """获取当前玩家"""
        return self.players[self.current_player_index]
    
    def get_human_player(self) -> Optional[Player]:
        """获取人类玩家"""
        for player in self.players:
            if player.player_type == PlayerType.HUMAN:
                return player
        return None
    
    def can_player_action(self, player: Player, action: GameAction, tile: Optional[Tile] = None) -> bool:
        """检查玩家是否可以执行动作"""
        if self.state != GameState.PLAYING:
            return False
        
        if action == GameAction.DISCARD:
            return (player == self.get_current_player() and 
                    tile and tile in player.hand_tiles and
                    self.rule.can_discard(player, tile))
        
        elif action == GameAction.PENG:
            return (player != self.last_discard_player and
                    self.last_discarded_tile and
                    player.can_peng(self.last_discarded_tile))
        
        elif action == GameAction.GANG:
            return (player != self.last_discard_player and
                    self.last_discarded_tile and
                    player.can_gang(self.last_discarded_tile))
        
        elif action == GameAction.CHI:
            return (player != self.last_discard_player and
                    self.last_discarded_tile and
                    len(player.can_chi(self.last_discarded_tile)) > 0)
        
        elif action == GameAction.WIN:
            return self.rule.can_win(player, self.last_discarded_tile)
        
        return False
    
    def execute_player_action(self, player: Player, action: GameAction, 
                            tile: Optional[Tile] = None, extra_data: Optional[Dict] = None) -> bool:
        """执行玩家动作"""
        if not self.can_player_action(player, action, tile):
            return False
        
        self.logger.info(f"{player.name}执行动作: {action.value}")
        
        if action == GameAction.DISCARD:
            return self._execute_discard(player, tile)
        
        elif action == GameAction.PENG:
            return self._execute_peng(player)
        
        elif action == GameAction.GANG:
            return self._execute_gang(player)
        
        elif action == GameAction.CHI:
            chi_tiles = extra_data.get("chi_tiles", []) if extra_data else []
            return self._execute_chi(player, chi_tiles)
        
        elif action == GameAction.WIN:
            return self._execute_win(player)
        
        return False
    
    def _execute_discard(self, player: Player, tile: Tile) -> bool:
        """执行打牌"""
        if not player.remove_tile(tile):
            return False
        
        self.deck.discard_tile(tile)
        self.last_discarded_tile = tile
        self.last_discard_player = player
        
        # 检查其他玩家是否可以胡牌
        for other_player in self.players:
            if other_player != player and self.rule.can_win(other_player, tile):
                other_player.can_win = True
        
        self._next_player()
        self._notify_player_action(player, GameAction.DISCARD, tile)
        return True
    
    def _execute_peng(self, player: Player) -> bool:
        """执行碰牌"""
        if not self.last_discarded_tile:
            return False
        
        if player.make_peng(self.last_discarded_tile):
            self.current_player_index = player.position
            self.last_discarded_tile = None
            self.last_discard_player = None
            self._notify_player_action(player, GameAction.PENG, self.last_discarded_tile)
            return True
        
        return False
    
    def _execute_gang(self, player: Player) -> bool:
        """执行杠牌"""
        if not self.last_discarded_tile:
            return False
        
        if player.make_gang(self.last_discarded_tile):
            # 杠牌后需要补牌
            new_tile = self.deck.draw_tile()
            if new_tile:
                player.add_tile(new_tile)
            
            self.current_player_index = player.position
            self.last_discarded_tile = None
            self.last_discard_player = None
            self._notify_player_action(player, GameAction.GANG, self.last_discarded_tile)
            return True
        
        return False
    
    def _execute_chi(self, player: Player, chi_tiles: List[Tile]) -> bool:
        """执行吃牌"""
        if not chi_tiles or len(chi_tiles) != 3:
            return False
        
        if player.make_chi(chi_tiles):
            self.current_player_index = player.position
            self.last_discarded_tile = None
            self.last_discard_player = None
            self._notify_player_action(player, GameAction.CHI, chi_tiles)
            return True
        
        return False
    
    def _execute_win(self, player: Player) -> bool:
        """执行胡牌"""
        if self.rule.can_win(player, self.last_discarded_tile):
            player.is_winner = True
            self.state = GameState.GAME_OVER
            
            # 计算得分
            scores = self.rule.calculate_score(player, self.players, self.last_discarded_tile)
            for p in self.players:
                p.score += scores[p.name]
                if p.is_winner:
                    p.wins += 1
                else:
                    p.losses += 1
            
            self._notify_game_over(player, scores)
            return True
        
        return False
    
    def _next_player(self):
        """下一个玩家"""
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        
        # 摸牌
        current_player = self.get_current_player()
        new_tile = self.deck.draw_tile()
        if new_tile:
            current_player.add_tile(new_tile)
        
        # 检查是否可以胡牌
        if self.rule.can_win(current_player):
            current_player.can_win = True
    
    def set_player_missing_suit(self, player: Player, suit: str) -> bool:
        """设置玩家缺门"""
        if player.player_type == PlayerType.HUMAN and not player.missing_suit:
            player.set_missing_suit(suit)
            self.logger.info(f"{player.name}选择缺{suit}")
            return True
        return False
    
    def get_game_status(self) -> Dict:
        """获取游戏状态"""
        return {
            "state": self.state.value,
            "mode": self.mode.value,
            "rule_type": self.rule_type,
            "round_number": self.round_number,
            "current_player": self.current_player_index,
            "remaining_tiles": self.deck.get_remaining_count() if self.deck else 0,
            "players": [
                {
                    "name": p.name,
                    "type": p.player_type.value,
                    "hand_count": p.get_hand_count(),
                    "score": p.score,
                    "can_win": p.can_win,
                    "missing_suit": p.missing_suit
                }
                for p in self.players
            ]
        }
    
    def _notify_state_changed(self):
        """通知游戏状态变化"""
        if self.on_game_state_changed:
            self.on_game_state_changed(self.state)
    
    def _notify_player_action(self, player: Player, action: GameAction, data=None):
        """通知玩家动作"""
        if self.on_player_action:
            self.on_player_action(player, action, data)
    
    def _notify_game_over(self, winner: Player, scores: Dict):
        """通知游戏结束"""
        if self.on_game_over:
            self.on_game_over(winner, scores)
    
    def is_game_over(self) -> bool:
        """游戏是否结束"""
        return self.state == GameState.GAME_OVER
    
    def get_game_state(self) -> Dict[str, Any]:
        """获取游戏状态信息"""
        return {
            'state': self.state.value,
            'current_player': self.current_player_index,
            'active_players': self.active_players,
            'winners': self.winners,
            'round_number': self.round_number,
            'remaining_tiles': self.deck.get_remaining_count() if self.deck else 0,
            'missing_suits': self.missing_suits,
            'exchange_direction': self.exchange_direction if hasattr(self, 'exchange_direction') else None
        }
    
    def get_player_info(self, player_id: int) -> Optional[Dict[str, Any]]:
        """获取玩家信息"""
        if player_id not in range(len(self.players)):
            return None
        
        player = self.players[player_id]
        return {
            'player_id': player_id,
            'name': player.name,
            'hand_count': len(player.hand_tiles),
            'melds': player.melds,
            'missing_suit': self.missing_suits.get(player_id),
            'is_active': player_id in self.active_players,
            'is_winner': player_id in self.winners
        } 
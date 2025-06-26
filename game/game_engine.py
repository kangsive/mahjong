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
    GANG = "gang"  # 包含明杠和暗杠
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
        self.last_drawn_tile: Optional[Tile] = None  # 新增：最后摸到的牌
        self.game_history: List[Dict] = []
        
        # 新增：公共出牌池
        self.discard_pool: List[Tuple[Tile, str]] = []  # (牌, 玩家名)
        
        # 回调函数
        self.on_game_state_changed: Optional[Callable] = None
        self.on_player_action: Optional[Callable] = None
        self.on_game_over: Optional[Callable] = None
        self.on_ai_turn_start: Optional[Callable] = None  # 新增：AI回合开始回调
        
        # 换三张相关
        self.exchange_tiles: Dict[int, List[Tile]] = {}  # 玩家选择的换牌
        self.exchange_direction = 1  # 1为顺时针，-1为逆时针
        
        # 缺一门相关
        self.missing_suits: Dict[int, Optional[TileType]] = {}  # 玩家选择的缺门
        
        # 血战到底相关
        self.winners: List[int] = []  # 已胡牌的玩家索引
        self.active_players: List[int] = []  # 仍在游戏中的玩家索引
        
        # 庄家管理
        self.dealer_index = 0  # 当前庄家索引
        self.last_game_winners: List[int] = []  # 上局胜者列表
        self.last_game_winner_tile: Optional[Tile] = None  # 上局胡牌的牌
        self.is_first_game = True  # 是否为第一局游戏
        
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
            self.players.append(Player("AI-1", PlayerType.AI_HARD, 2))
            self.players.append(Player("AI-2", PlayerType.AI_HARD, 3))
        else:
            # 竞技模式：1个人类玩家 + 3个AI
            self.players.append(Player("玩家", PlayerType.HUMAN, 0))
            self.players.append(Player("AI-1", PlayerType.AI_HARD, 1))
            self.players.append(Player("AI-2", PlayerType.AI_HARD, 2))
            self.players.append(Player("AI-3", PlayerType.AI_HARD, 3))
        
        self.state = GameState.WAITING
        self.logger.info(f"游戏设置完成: {mode.value}, {rule_type}")
    
    def start_game(self):
        """开始游戏（兼容接口）"""
        return self.start_new_game()
    
    def start_new_game(self):
        """开始新游戏"""
        if not self.deck or not self.rule or not self.players:
            self.logger.error("游戏未正确设置")
            return False
        
        # 重置游戏状态
        self.round_number += 1
        self.last_discarded_tile = None
        self.last_discard_player = None
        
        # 决定庄家
        self._determine_dealer()
        
        # 重置玩家
        for player in self.players:
            player.reset()
        
        # 重置牌堆
        self.deck.reset()
        
        # 初始化活跃玩家列表
        self.active_players = list(range(len(self.players)))
        self.winners = []
        
        # 初始化换牌和缺门字典
        self.exchange_tiles = {}
        self.missing_suits = {i: None for i in range(len(self.players))}
        
        # 开始发牌
        self.state = GameState.DEALING
        self._deal_initial_cards()
        
        # 换三张以及选择缺门（四川麻将）
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
        dealer = self.get_dealer()
        extra_tile = self.deck.draw_tile()
        if extra_tile:
            dealer.add_tile(extra_tile)
        
        self.logger.info(f"发牌完成，庄家 {dealer.name} 获得14张牌")
    
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
            if hasattr(player, 'on_tile_exchange_start') and player.on_tile_exchange_start:
                player.on_tile_exchange_start(self.exchange_direction)
        
        # AI玩家自动选择换牌
        self._ai_auto_exchange()
    
    def _ai_auto_exchange(self):
        """AI玩家自动选择换牌"""
        for i, player in enumerate(self.players):
            if player.player_type != PlayerType.HUMAN:
                # AI自动选择换牌
                self._ai_choose_exchange_tiles(i, player)
    
    def _ai_choose_exchange_tiles(self, player_id: int, player: Player):
        """AI选择换牌"""
        # 尝试使用指定AI类的方法
        exchange_tiles = self._try_ai_exchange_tiles(player)
        
        if exchange_tiles and len(exchange_tiles) == 3:
            # AI类提供了有效的换牌选择
            self.submit_exchange_tiles(player_id, exchange_tiles)
            self.logger.info(f"AI玩家 {player_id} 使用AI算法选择换牌: {[str(t) for t in exchange_tiles]}")
        else:
            # 使用默认逻辑：按花色分组，选择数量最多的花色的前三张牌
            suits = {}
            for tile in player.hand_tiles:
                if tile.tile_type not in suits:
                    suits[tile.tile_type] = []
                suits[tile.tile_type].append(tile)
            
            # 选择数量最多的花色的前三张牌
            if suits:
                max_suit = max(suits.keys(), key=lambda s: len(suits[s]))
                exchange_tiles = suits[max_suit][:3]
                
                if len(exchange_tiles) == 3:
                    self.submit_exchange_tiles(player_id, exchange_tiles)
                    self.logger.info(f"AI玩家 {player_id} 使用默认策略选择换牌: {[str(t) for t in exchange_tiles]}")
    
    def _try_ai_exchange_tiles(self, player: Player) -> Optional[List[Tile]]:
        """尝试使用AI类的换牌方法"""
        try:
            ai = self._create_ai_for_player(player)
            if ai and hasattr(ai, 'choose_exchange_tiles'):
                # AI类有换牌方法，使用它
                tiles = ai.choose_exchange_tiles(player, 3)
                # 验证返回的牌是否有效
                if (tiles and len(tiles) == 3 and 
                    all(tile in player.hand_tiles for tile in tiles) and
                    self._is_same_suit(tiles)):
                    return tiles
            return None
        except Exception as e:
            self.logger.warning(f"AI换牌方法执行失败: {e}")
            return None
    
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
        
        # 记录每个玩家获得的牌
        self.received_tiles = {}  # 新增：记录每个玩家获得的牌
        
        # 按方向分发牌
        for player_id in range(4):
            if player_id in removed_tiles:
                # 计算目标玩家ID
                target_player_id = (player_id + self.exchange_direction) % 4
                target_player = self.players[target_player_id]
                
                # 记录目标玩家获得的牌
                if target_player_id not in self.received_tiles:
                    self.received_tiles[target_player_id] = []
                
                # 将牌给目标玩家
                for tile in removed_tiles[player_id]:
                    target_player.add_tile_to_hand(tile)
                    self.received_tiles[target_player_id].append(tile)
        
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
            if hasattr(player, 'on_missing_suit_selection_start') and player.on_missing_suit_selection_start:
                player.on_missing_suit_selection_start()
        
        # AI玩家自动选择缺门
        self._ai_auto_choose_missing_suit()
    
    def _ai_auto_choose_missing_suit(self):
        """AI玩家自动选择缺门"""
        for i, player in enumerate(self.players):
            if player.player_type != PlayerType.HUMAN:
                # AI自动选择缺门
                self._ai_choose_missing_suit(i, player)
    
    def _ai_choose_missing_suit(self, player_id: int, player: Player):
        """AI选择缺门"""
        # 尝试使用指定AI类的方法
        missing_suit_str = self._try_ai_missing_suit(player)
        
        if missing_suit_str:
            # AI类提供了有效的缺门选择，转换为TileType
            suit_map = {"万": TileType.WAN, "筒": TileType.TONG, "条": TileType.TIAO}
            missing_suit = suit_map.get(missing_suit_str)
            if missing_suit:
                self.submit_missing_suit(player_id, missing_suit)
                self.logger.info(f"AI玩家 {player_id} 使用AI算法选择缺{missing_suit.value}")
                return
        
        # 使用默认逻辑：统计各花色数量，选择最少的
        suit_counts = {TileType.WAN: 0, TileType.TONG: 0, TileType.TIAO: 0}
        for tile in player.hand_tiles:
            if tile.tile_type in suit_counts:
                suit_counts[tile.tile_type] += 1
        
        missing_suit = min(suit_counts.keys(), key=lambda s: suit_counts[s])
        self.submit_missing_suit(player_id, missing_suit)
        self.logger.info(f"AI玩家 {player_id} 使用默认策略选择缺{missing_suit.value}")
    
    def _try_ai_missing_suit(self, player: Player) -> Optional[str]:
        """尝试使用AI类的缺门选择方法"""
        try:
            ai = self._create_ai_for_player(player)
            if ai and hasattr(ai, 'choose_missing_suit'):
                # AI类有缺门选择方法，使用它
                suit_str = ai.choose_missing_suit(player)
                # 验证返回的缺门是否有效
                if suit_str in ["万", "筒", "条"]:
                    return suit_str
            return None
        except Exception as e:
            self.logger.warning(f"AI缺门选择方法执行失败: {e}")
            return None
    
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
        self.current_player_index = self.dealer_index  # 庄家先开始
        
        # 清空出牌池
        self.discard_pool = []
        
        # 确保所有玩家的missing_suit属性已设置
        for i, player in enumerate(self.players):
            if hasattr(player, 'missing_suit') and not player.missing_suit:
                # 从missing_suits字典中获取缺门信息
                missing_suit_type = self.missing_suits.get(i)
                if missing_suit_type:
                    player.missing_suit = missing_suit_type.value
        
        self.logger.info("游戏阶段开始，庄家开始出牌")
        
        # 通知游戏状态变化
        self._notify_state_changed()
        
        # 启动第一个玩家的回合（如果是AI自动开始）
        self._start_player_turn()
    
    def _start_player_turn(self):
        """开始玩家回合"""
        current_player = self.get_current_player()
        if current_player:
            self.logger.info(f"轮到 {current_player.name} 出牌")
            
            # 如果是AI玩家，通知UI启动AI回合
            if current_player.player_type != PlayerType.HUMAN:
                if self.on_ai_turn_start:
                    self.on_ai_turn_start(current_player)
    
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
        # PASS动作总是可以执行
        if action is None or action == GameAction.PASS:
            return True
            
        # 只有在PLAYING或WAITING_ACTION状态下才能执行其他动作
        if self.state not in [GameState.PLAYING, GameState.WAITING_ACTION]:
            return False
        
        if action == GameAction.DISCARD:
            # 只有在PLAYING状态且是当前玩家才能出牌
            return (self.state == GameState.PLAYING and
                    player == self.get_current_player() and 
                    tile and tile in player.hand_tiles and
                    self.rule.can_discard(player, tile))
        
        elif action == GameAction.PENG:
            return (player != self.last_discard_player and
                    self.last_discarded_tile and
                    player.can_peng(self.last_discarded_tile))
        
        elif action == GameAction.GANG:
            # 明杠：只有当玩家对上一张弃牌拥有三张相同牌时才成立
            if (self.last_discarded_tile and
                player != self.last_discard_player and
                player.can_gang(self.last_discarded_tile)):
                return True
            # 暗杠：当前玩家的回合，可以杠自己手中的四张相同牌
            if (player == self.get_current_player() and 
                self.state == GameState.PLAYING and
                len(player.can_hidden_gang()) > 0):
                return True
            return False
        
        elif action == GameAction.CHI:
            return (player != self.last_discard_player and
                    self.last_discarded_tile and
                    len(player.can_chi(self.last_discarded_tile)) > 0)
        
        elif action == GameAction.WIN:
            # 检查自摸胡牌（当前玩家的回合）
            if player == self.get_current_player() and self.state == GameState.PLAYING:
                return self.rule.can_win(player, None)  # 自摸胡牌
            # 检查点炮胡牌（响应其他玩家的出牌）
            else:
                return self.rule.can_win(player, self.last_discarded_tile)
        
        return False
    
    def execute_player_action(self, player: Player, action: GameAction, 
                            tile: Optional[Tile] = None, extra_data: Optional[Dict] = None) -> bool:
        """执行玩家动作"""
        # 处理PASS动作（选择过）
        if action is None or action == GameAction.PASS:
            return self._execute_pass(player)
        
        if not self.can_player_action(player, action, tile):
            return False
        
        self.logger.info(f"{player.name}执行动作: {action.value}")
        
        if action == GameAction.DISCARD:
            return self._execute_discard(player, tile)
        
        elif action == GameAction.PENG:
            return self._execute_peng(player)
        
        elif action == GameAction.GANG:
            return self._execute_gang(player, tile)
        
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
        
        # 添加到公共出牌池
        self.discard_pool.append((tile, player.name))
        
        # 也添加到牌堆的弃牌区（保持兼容性）
        self.deck.discard_tile(tile)
        self.last_discarded_tile = tile
        self.last_discard_player = player
        
        self.logger.info(f"{player.name} 打出了 {tile}")
        
        # 检查其他玩家是否可以胡牌、碰牌、杠牌
        response_actions = self._check_response_actions(player, tile)
        
        if response_actions:
            # 有玩家可以响应，进入等待响应状态
            self.state = GameState.WAITING_ACTION
            self._notify_player_action(player, GameAction.DISCARD, {"tile": tile, "response_actions": response_actions})
        else:
            # 无人响应，直接进入下一玩家回合
            self._next_player()
            self._notify_player_action(player, GameAction.DISCARD, tile)
            
        return True
    
    def _check_response_actions(self, discard_player: Player, tile: Tile) -> Dict[int, List[GameAction]]:
        """检查其他玩家可以执行的响应动作"""
        response_actions = {}
        
        for i, player in enumerate(self.players):
            if player == discard_player:
                continue
            
            # 血战到底：只检查活跃玩家的响应
            if hasattr(self, 'active_players') and i not in self.active_players:
                continue
                
            actions = []
            
            # 检查胡牌
            if self.rule and self.rule.can_win(player, tile):
                actions.append(GameAction.WIN)
            
            # 检查杠牌
            if player.can_gang(tile):
                actions.append(GameAction.GANG)
            
            # 检查碰牌
            if player.can_peng(tile):
                actions.append(GameAction.PENG)
            
            # 四川麻将不支持吃牌
            # if self.rule_type != "sichuan" and player.can_chi(tile):
            #     actions.append(GameAction.CHI)
            
            if actions:
                response_actions[i] = actions
        
        return response_actions
    
    def _execute_peng(self, player: Player) -> bool:
        """执行碰牌"""
        if not self.last_discarded_tile:
            return False
        
        if player.make_peng(self.last_discarded_tile):
            # 从公共出牌池中移除被碰的牌
            self._remove_tile_from_discard_pool(self.last_discarded_tile)
            
            self.current_player_index = player.position
            self.last_discarded_tile = None
            self.last_discard_player = None
            self.last_drawn_tile = None  # 碰牌不涉及摸牌，清空摸牌状态
            
            # 检查碰牌后是否可以胡牌
            if self.rule and self.rule.can_win(player):
                player.can_win = True
                self.logger.info(f"{player.name} 碰牌后可以胡牌")
            
            # 碰牌后转换为正常游戏状态，让碰牌玩家继续出牌
            self.state = GameState.PLAYING
            
            self._notify_player_action(player, GameAction.PENG, self.last_discarded_tile)
            return True
        
        return False
    
    def _execute_gang(self, player: Player, tile: Optional[Tile] = None) -> bool:
        """执行杠牌（包含明杠和暗杠）"""
        is_hidden_gang = False
        gang_tile = None
        
        # 判断是明杠还是暗杠
        if (self.last_discarded_tile and
            player != self.last_discard_player and
            player.can_gang(self.last_discarded_tile)):
            gang_tile = self.last_discarded_tile
            is_hidden_gang = False
        elif tile and player == self.get_current_player():
            # 暗杠：当前玩家的回合，杠自己手中的四张相同牌
            hidden_gang_tiles = player.can_hidden_gang(tile)
            if not hidden_gang_tiles:  # 如果返回空列表，说明不能暗杠
                return False
            gang_tile = tile
            is_hidden_gang = True
        else:
            return False
        
        # 执行杠牌操作
        if is_hidden_gang:
            success = player.make_hidden_gang(gang_tile)
            # 暗杠立即结算：所有仍在场且未胡牌玩家各付 2 分
            if success:
                for p in self.players:
                    if p == player or getattr(p, 'is_winner', False):
                        continue
                    p.score -= 2
                    player.score += 2
        else:
            success = player.make_gang(gang_tile)
            # 明杠立即结算：放杠者支付 1 分
            if success and self.last_discard_player and self.last_discard_player != player:
                self.last_discard_player.score -= 1
                player.score += 1
        
        if not success:
            return False
        
        # 明杠需要从公共出牌池中移除被杠的牌
        if not is_hidden_gang:
            self._remove_tile_from_discard_pool(gang_tile)
        
        # 检查是否流局（杠牌后需要摸牌）
        if not self.deck or self.deck.get_remaining_count() <= 0:
            gang_type = "暗杠" if is_hidden_gang else "杠牌"
            self.logger.info(f"{gang_type}后无牌可摸，游戏流局")
            self._handle_draw_game()
            return True
        
        # 杠牌后需要补牌
        new_tile = self.deck.draw_tile()
        if new_tile:
            player.add_tile(new_tile)
            self.last_drawn_tile = new_tile  # 记录摸到的牌
            gang_type = "暗杠" if is_hidden_gang else "杠牌"
            if player.player_type == PlayerType.HUMAN:
                self.logger.info(f"{player.name} {gang_type}后摸了一张牌: {new_tile}")
            else:
                self.logger.info(f"{player.name} {gang_type}后摸了一张牌")
        else:
            gang_type = "暗杠" if is_hidden_gang else "杠牌"
            self.logger.warning(f"{gang_type}后摸牌失败")
            self._handle_draw_game()
            return True
        
        self.current_player_index = player.position
        self.last_discarded_tile = None
        self.last_discard_player = None
        
        # 检查杠牌后是否可以胡牌
        if self.rule and self.rule.can_win(player):
            player.can_win = True
            gang_type = "暗杠" if is_hidden_gang else "杠牌"
            self.logger.info(f"{player.name} {gang_type}后可以胡牌")
        
        # 杠牌后转换为正常游戏状态，让杠牌玩家继续出牌
        self.state = GameState.PLAYING
        
        # 通知动作，传递是否为暗杠的信息
        action_data = {"tile": gang_tile, "is_hidden": is_hidden_gang}
        self._notify_player_action(player, GameAction.GANG, action_data)
        return True
    
    def _execute_chi(self, player: Player, chi_tiles: List[Tile]) -> bool:
        """执行吃牌"""
        if not chi_tiles or len(chi_tiles) != 3:
            return False
        
        if player.make_chi(chi_tiles):
            # 从公共出牌池中移除被吃的牌（第一张牌，即其他玩家打出的牌）
            if self.last_discarded_tile and self.last_discarded_tile in chi_tiles:
                self._remove_tile_from_discard_pool(self.last_discarded_tile)
            
            self.current_player_index = player.position
            self.last_discarded_tile = None
            self.last_discard_player = None
            self.last_drawn_tile = None  # 吃牌不涉及摸牌，清空摸牌状态
            
            # 吃牌后转换为正常游戏状态，让吃牌玩家继续出牌
            self.state = GameState.PLAYING
            
            self._notify_player_action(player, GameAction.CHI, chi_tiles)
            return True
        
        return False
    
    def _execute_win(self, player: Player) -> bool:
        """执行胡牌"""
        # 判断是否为自摸胡牌
        is_self_draw = (player == self.get_current_player() and self.state == GameState.PLAYING)
        
        # 根据胡牌类型选择正确的牌来检查
        win_tile = None if is_self_draw else self.last_discarded_tile
        
        if self.rule.can_win(player, win_tile):
            # 如果是点炮胡牌，需要将胡牌加入手牌中进行最终检查
            if not is_self_draw and self.last_discarded_tile:
                # 从公共出牌池中移除被胡的牌
                self._remove_tile_from_discard_pool(self.last_discarded_tile)
                # 将胡牌加入手牌（用于最终的牌型检查和显示）
                player.add_tile_to_hand(self.last_discarded_tile)
            
            player.is_winner = True
            player_id = player.position
            
            # 记录胜者信息 - 血战到底：累积记录胜者
            if player_id not in self.winners:
                self.winners.append(player_id)
            
            # 从活跃玩家中移除该玩家
            if player_id in self.active_players:
                self.active_players.remove(player_id)
            
            winner_tile = self.last_drawn_tile if is_self_draw else self.last_discarded_tile
            
            # 收集所有能胡这张牌的玩家（一炮多响检测）
            all_winners = [player]  # 当前胡牌玩家
            
            # 检查是否有其他玩家也能胡这张牌（一炮多响，只有点炮时才可能）
            if self.last_discarded_tile and not is_self_draw:
                for other_player in self.players:
                    if (other_player != player and 
                        other_player != self.last_discard_player and
                        not getattr(other_player, 'is_winner', False) and  # 避免重复处理
                        self.rule.can_win(other_player, self.last_discarded_tile)):
                        # 其他玩家也能胡，也将胡牌加入其手牌
                        other_player.add_tile_to_hand(self.last_discarded_tile)
                        other_player.is_winner = True
                        other_id = other_player.position
                        if other_id not in self.winners:
                            self.winners.append(other_id)
                        if other_id in self.active_players:
                            self.active_players.remove(other_id)
                        all_winners.append(other_player)
            
            # 为每个胡牌的玩家单独计分
            for winner_player in all_winners:
                # 计算得分，传递正确的自摸标志和放炮者信息
                scores = self.rule.calculate_score(
                    winner_player, self.players, winner_tile, 
                    is_self_draw=is_self_draw,
                    discard_player=self.last_discard_player
                )
                
                # 应用得分变化
                for p in self.players:
                    score_change = scores[p.name]
                    p.score += score_change
                    # 累加本局得分变化用于显示
                    if not hasattr(p, 'last_score_change'):
                        p.last_score_change = 0
                    p.last_score_change += score_change
                    
                # 更新胜负记录
                winner_player.wins += 1
                for p in self.players:
                    if p != winner_player and not getattr(p, 'is_winner', False):
                        p.losses += 1
                
                # 记录胡牌类型用于显示
                win_type = "自摸" if is_self_draw else "点炮胡"
                current_rank = len([w for w in all_winners if self.winners.index(w.position) <= self.winners.index(winner_player.position)])
                rank_names = ["", "第一名", "第二名", "第三名", "第四名"]
                rank_name = rank_names[current_rank] if current_rank < len(rank_names) else f"第{current_rank}名"
                
                self.logger.info(f"{winner_player.name} {win_type}胡牌！获得{rank_name}！胡牌: {winner_tile}")
            
            # 血战到底：检查游戏是否结束
            if len(self.active_players) <= 1:
                # 游戏结束：只剩1个或更少活跃玩家
                self.state = GameState.GAME_OVER
                
                # 如果还有1个活跃玩家，他自动成为最后一名
                if len(self.active_players) == 1:
                    last_player_id = self.active_players[0]
                    last_player = self.players[last_player_id]
                    if last_player_id not in self.winners:
                        self.winners.append(last_player_id)
                        last_player.losses += 1
                        last_rank = len(self.winners)
                        last_rank_name = rank_names[last_rank] if last_rank < len(rank_names) else f"第{last_rank}名"
                        self.logger.info(f"{last_player.name} 获得{last_rank_name}")
                    self.active_players.remove(last_player_id)
                
                # 记录游戏结果用于下局决定庄家
                self._record_game_result(self.winners, winner_tile)
                
                # 传递最后一个胜者和总得分信息
                final_scores = {p.name: getattr(p, 'last_score_change', 0) for p in self.players}
                self._notify_game_over(all_winners[-1], final_scores, is_self_draw, winner_tile)
                
                self.logger.info(f"血战到底结束！最终排名: {[self.players[i].name for i in self.winners]}")
            else:
                # 游戏继续：血战到底
                remaining_count = len(self.active_players)
                self.logger.info(f"血战到底继续，剩余{remaining_count}名玩家")
                
                # 血战到底：胡牌后从胡牌玩家的下一家开始继续游戏
                # 先把当前索引定位到胡牌玩家，待下一步统一用 _next_player() 处理
                self.current_player_index = player.position

                # 重置为正常游戏状态，然后调用 _next_player()，
                # 由该方法负责跳到下一个活跃玩家并完成摸牌流程
                self.state = GameState.PLAYING

                self._next_player()
            
            return True
        
        return False
    
    def _execute_pass(self, player: Player) -> bool:
        """执行过牌动作"""
        self.logger.info(f"{player.name} 选择过")
        
        # 如果当前在等待响应状态，检查是否所有玩家都已响应
        if self.state == GameState.WAITING_ACTION:
            self._handle_response_timeout()
        
        return True
    
    def _handle_response_timeout(self):
        """处理响应超时（所有玩家都选择过）"""
        self.logger.info("所有玩家都选择过，继续游戏")
        
        # 重置状态为正常游戏状态
        self.state = GameState.PLAYING
        
        # 进入下一个玩家的回合
        self._next_player()
    
    def _skip_to_next_active_player(self):
        """跳到下一个活跃玩家（血战到底专用）"""
        max_attempts = len(self.players)
        attempts = 0
        
        while attempts < max_attempts:
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            if self.current_player_index in self.active_players:
                break
            attempts += 1
        
        if attempts >= max_attempts:
            self.logger.error("无法找到活跃玩家")
            self._handle_draw_game()
    
    def _next_player(self):
        """下一个玩家"""
        # 切换到下一个活跃玩家（血战到底）
        if len(self.active_players) > 1:
            self._skip_to_next_active_player()
        else:
            # 游戏应该已经结束
            self.logger.warning("活跃玩家不足，游戏应该已结束")
            return
        
        current_player = self.get_current_player()
        
        # 确保当前玩家是活跃的
        if self.current_player_index not in self.active_players:
            self.logger.error(f"当前玩家 {current_player.name} 不在活跃列表中")
            self._skip_to_next_active_player()
            current_player = self.get_current_player()
        
        self.logger.info(f"切换到下一个玩家: {current_player.name}")
        
        # 检查是否流局（牌堆已空）
        if not self.deck or self.deck.get_remaining_count() <= 0:
            self.logger.info("牌堆已空，游戏流局")
            self._handle_draw_game()
            return
        
        # 摸牌
        new_tile = self.deck.draw_tile()
        if new_tile:
            current_player.add_tile(new_tile)
            self.last_drawn_tile = new_tile  # 记录最后摸到的牌
            if current_player.player_type == PlayerType.HUMAN:
                self.logger.info(f"{current_player.name} 摸了一张牌: {new_tile}")
            else:
                self.logger.info(f"{current_player.name} 摸了一张牌")
        else:
            self.logger.warning("摸牌失败，牌堆可能已空")
            self._handle_draw_game()
            return
        
        # 检查自摸胡牌
        # 注意：摸牌后玩家手牌数变成了14张（13+1），需要检查整体是否构成胡牌
        if self.rule and self.rule.can_win(current_player, None):
            current_player.can_win = True
            self.logger.info(f"{current_player.name} 可以自摸胡牌")
        
        # 启动玩家回合
        self._start_player_turn()
    
    def _handle_draw_game(self):
        """处理流局"""
        self.state = GameState.GAME_OVER
        self.logger.info("游戏流局，无人胜出")
        
        # 记录流局结果（无胜者）
        self._record_game_result([])
        
        # 流局时所有玩家得分为0
        scores = {player.name: 0 for player in self.players}
        
        # 通知游戏结束
        if self.on_game_over:
            self.on_game_over(None, scores)  # winner为None表示流局
    
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
    
    def _notify_game_over(self, winner: Player, scores: Dict, is_self_draw: bool = False, winner_tile: Optional[Tile] = None):
        """通知游戏结束"""
        if self.on_game_over:
            self.on_game_over(winner, scores, is_self_draw, winner_tile)
    
    def is_game_over(self) -> bool:
        """游戏是否结束"""
        # 血战到底：当活跃玩家数量 <= 1 时游戏结束
        if hasattr(self, 'active_players') and len(self.active_players) <= 1:
            return True
        return self.state == GameState.GAME_OVER
    
    def get_game_state(self) -> Dict[str, Any]:
        """获取游戏状态信息"""
        return {
            'state': self.state.value,
            'current_player': self.current_player_index,
            'dealer_index': self.dealer_index,  # 新增：庄家索引
            'dealer_name': self.get_dealer().name,  # 新增：庄家姓名
            'active_players': self.active_players,
            'winners': self.winners,
            'round_number': self.round_number,
            'remaining_tiles': self.deck.get_remaining_count() if self.deck else 0,
            'missing_suits': self.missing_suits,
            'exchange_direction': self.exchange_direction if hasattr(self, 'exchange_direction') else None,
            'discard_pool': self.discard_pool,  # 新增：出牌池
            'last_discarded_tile': str(self.last_discarded_tile) if self.last_discarded_tile else None,
            'last_discard_player': self.last_discard_player.name if self.last_discard_player else None,
            'is_first_game': self.is_first_game,  # 新增：是否第一局
            'received_tiles': self.received_tiles if hasattr(self, 'received_tiles') else None
        }
    
    def get_player_info(self, player_id: int) -> Optional[Dict[str, Any]]:
        """获取玩家信息"""
        if player_id not in range(len(self.players)):
            return None
        
        player = self.players[player_id]
        
        # 方位信息
        positions = ["东", "南", "西", "北"]
        
        return {
            'player_id': player_id,
            'name': player.name,
            'position': positions[player_id],  # 新增：方位
            'hand_count': len(player.hand_tiles),
            'hand_tiles': [str(tile) for tile in player.hand_tiles] if player.player_type == PlayerType.HUMAN else [],
            'melds': [{'type': meld.meld_type, 'tiles': [str(t) for t in meld.tiles]} for meld in player.melds],  # 新增：明牌
            'missing_suit': self.missing_suits.get(player_id),
            'is_active': player_id in self.active_players,
            'is_winner': player_id in self.winners,
            'is_current': player_id == self.current_player_index,  # 新增：是否当前玩家
            'is_dealer': player_id == self.dealer_index,  # 新增：是否庄家
            'can_win': getattr(player, 'can_win', False),
            'score': getattr(player, 'score', 0)
        }
        
    def get_all_players_info(self) -> List[Dict[str, Any]]:
        """获取所有玩家信息"""
        return [self.get_player_info(i) for i in range(len(self.players))]
    
    def _determine_dealer(self):
        """
        决定庄家
        规则：
        1. 第一局游戏：随机分配庄家
        2. 一炮多响（多人同时胡一张玩家打出来的牌）：优先坐庄
        3. 否则第一个胡牌的玩家为庄家
        """
        if self.is_first_game:
            # 第一局游戏，随机分配庄家
            self.dealer_index = random.randint(0, len(self.players) - 1)
            self.logger.info(f"第一局游戏，随机分配庄家: {self.players[self.dealer_index].name}")
        else:
            # 根据上局结果决定庄家
            if len(self.last_game_winners) > 1 and self.last_game_winner_tile:
                # 一炮多响情况：多人同时胡同一张牌
                # 按座位顺序，选择第一个胡牌的玩家为庄家
                self.dealer_index = min(self.last_game_winners)
                self.logger.info(f"一炮多响，{self.players[self.dealer_index].name} 优先坐庄")
            elif self.last_game_winners:
                # 单人胡牌，胡牌者为庄家
                self.dealer_index = self.last_game_winners[0]
                self.logger.info(f"上局胜者 {self.players[self.dealer_index].name} 坐庄")
            else:
                # 流局或其他情况，庄家不变
                self.logger.info(f"流局，庄家不变: {self.players[self.dealer_index].name}")
        
        # 设置当前玩家为庄家
        self.current_player_index = self.dealer_index
    
    def _record_game_result(self, winners: List[int], winner_tile: Optional[Tile] = None):
        """
        记录游戏结果，用于下局决定庄家
        
        Args:
            winners: 胜者列表
            winner_tile: 胡牌的牌（如果是点炮胡牌）
        """
        self.last_game_winners = winners.copy()
        self.last_game_winner_tile = winner_tile
        self.is_first_game = False
        
        self.logger.info(f"记录游戏结果: 胜者 {[self.players[i].name for i in winners]}, 胡牌: {winner_tile}")
    
    def get_dealer(self) -> Player:
        """获取当前庄家"""
        return self.players[self.dealer_index]
    
    def _remove_tile_from_discard_pool(self, tile: Tile) -> bool:
        """从公共出牌池中移除指定的牌"""
        for i, (pool_tile, player_name) in enumerate(self.discard_pool):
            if (pool_tile.tile_type == tile.tile_type and 
                pool_tile.value == tile.value and
                pool_tile.feng_type == tile.feng_type and
                pool_tile.jian_type == tile.jian_type):
                # 找到匹配的牌，移除它
                removed_tile, removed_player = self.discard_pool.pop(i)
                self.logger.info(f"从出牌池移除: {removed_tile} (原打出者: {removed_player})")
                return True
        return False
    
    def _create_ai_for_player(self, player: Player) -> Optional:
        """为玩家创建对应的AI实例"""
        return self.create_ai_instance(player.player_type)
    
    def create_ai_instance(self, player_type: PlayerType = None, ai_difficulty: str = None):
        """
        创建AI实例的统一方法
        
        Args:
            player_type: 玩家类型，如果为None则使用ai_difficulty参数
            ai_difficulty: AI难度，如果为None则使用引擎的ai_difficulty属性
            
        Returns:
            AI实例或None
        """
        try:
            # 如果指定了玩家类型且为训练AI，直接返回训练AI
            if player_type == PlayerType.AI_TRAINER:
                from ai.trainer_ai import TrainerAI
                return TrainerAI()
            
            # 确定AI难度
            if ai_difficulty is None:
                ai_difficulty = getattr(self, 'ai_difficulty', 'medium')
            
            # 根据难度创建AI实例
            if ai_difficulty == "easy":
                from ai.simple_ai import SimpleAI
                return SimpleAI("easy")
            elif ai_difficulty == "medium":
                from ai.aggressive_ai import AggressiveAI
                return AggressiveAI("aggressive")
            elif ai_difficulty == "hard":
                from ai.mcts_ai import MctsAI
                return MctsAI(difficulty="hard", engine=self)
            else:  # expert 难度，使用 ShantenAI
                from ai.shanten_ai import ShantenAI
                return ShantenAI(difficulty="hard")
                
        except ImportError as e:
            self.logger.warning(f"无法导入AI类: {e}")
            return None
        except Exception as e:
            self.logger.warning(f"创建AI实例失败: {e}")
            return None 
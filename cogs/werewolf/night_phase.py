"""
Werewolf Night Phase Handler
Xử lý ban đêm - nhận DM actions từ các vai trò
"""
import asyncio
import discord
from typing import Optional, Callable, Dict, List
from datetime import datetime
from .models import GameWerewolf, GamePlayer, Role, Faction, ROLE_METADATA
from .special_roles import SpecialRolesHandler


def log(msg: str):
    """Log message"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [NightPhase] {msg}")


class NightPhaseHandler:
    """Xử lý ban đêm"""
    
    def __init__(self, bot):
        self.bot = bot
        self.wolf_votes = {}  # game_id -> {wolf_user_id -> target_id}
        self.wolf_votes_lock = {}  # game_id -> asyncio.Lock
    
    async def _get_or_create_vote_lock(self, game_id):
        """Get or create vote lock for game"""
        if game_id not in self.wolf_votes_lock:
            self.wolf_votes_lock[game_id] = asyncio.Lock()
        return self.wolf_votes_lock[game_id]
    
    async def run_night_phase(
        self,
        game: GameWerewolf,
        channel: discord.TextChannel
    ) -> Dict:
        """
        Chạy ban đêm hoàn chỉnh.
        Return: dict với kết quả
        Support early exit when all wolves vote
        """
        # Mute chat channel
        await self._mute_channel(channel, mute=True)
        
        # Initialize wolf votes tracking for this game
        game_id = game.guild_id
        self.wolf_votes[game_id] = {}
        
        # Gửi thông báo ban đêm bắt đầu
        embed = discord.Embed(
            title=f"ĐÊM #{game.night_count}",
            description="Các vai trò hành động...",
            color=discord.Color.dark_blue()
        )
        night_msg = await channel.send(embed=embed)
        log(f"Night {game.night_count} started")
        
        # Count wolves that need to vote
        alive_wolves = [
            p for p in game.get_alive_players()
            if p.role in [Role.WEREWOLF, Role.WOLF_SHAMAN, Role.WOLF_ALPHA, Role.WOLF_SEER]
        ]
        log(f"NIGHT_PHASE: {len(alive_wolves)} wolves need to vote")
        
        # Gửi DM cho từng vai trò
        tasks = []
        for player in game.get_alive_players():
            if player.role in [Role.WEREWOLF, Role.WOLF_SHAMAN, Role.WOLF_ALPHA, Role.WOLF_SEER]:
                tasks.append(self._handle_wolf_action(game, player))
            elif player.role == Role.DOCTOR:
                tasks.append(self._handle_doctor_action(game, player))
            elif player.role == Role.SEER:
                tasks.append(self._handle_seer_action(game, player))
            elif player.role == Role.AURA_SEER:
                tasks.append(self._handle_aura_seer_action(game, player))
            elif player.role == Role.WITCH:
                tasks.append(self._handle_witch_action(game, player))
            elif player.role == Role.BEAST_HUNTER:
                tasks.append(self._handle_beast_hunter_action(game, player))
            elif player.role == Role.MEDIUM:
                tasks.append(self._handle_medium_action(game, player))
            elif player.role == Role.BOMBER:
                tasks.append(self._handle_bomber_action(game, player))
        
        # Run all tasks in parallel
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Timer countdown (45s) with early exit when all wolves voted
        duration = game.night_duration
        for countdown in range(int(duration), 0, -5):
            try:
                remaining = f"{countdown}s" if countdown >= 5 else "Ket thuc..."
                embed = discord.Embed(
                    title=f"NIGHT #{game.night_count}",
                    description=f"Con lai: **{remaining}**",
                    color=discord.Color.dark_blue()
                )
                await night_msg.edit(embed=embed)
            except:
                pass
            
            # Check if all wolves have voted - if so, skip remaining time
            if len(alive_wolves) > 0 and len(self.wolf_votes.get(game_id, {})) == len(alive_wolves):
                log(f"NIGHT_EARLY_EXIT: All {len(alive_wolves)} wolves voted, skipping remaining time")
                try:
                    embed = discord.Embed(
                        title=f"NIGHT #{game.night_count}",
                        description="OK Tat ca soi da bo phieu, den sang ngay!",
                        color=discord.Color.green()
                    )
                    await night_msg.edit(embed=embed)
                except:
                    pass
                break
            
            await asyncio.sleep(5)
        
        # Resolve all actions
        result = await self._resolve_night_actions(game, channel)
        
        # Clean up wolf votes tracking
        if game_id in self.wolf_votes:
            del self.wolf_votes[game_id]
        
        # Unmute channel
        await self._mute_channel(channel, mute=False)
        
        return result
    
    # ================ WOLF ACTIONS ================
    
    async def _handle_wolf_action(self, game: GameWerewolf, wolf: GamePlayer):
        """Sói chọn mục tiêu để cắn - vote trong wolf thread"""
        try:
            # Get game channel
            game_channel = self.bot.get_channel(game.channel_id)
            if not game_channel:
                log(f"FAIL WOLF_ACTION [{wolf.username}] Game channel {game.channel_id} not found")
                return
            
            # Create wolf thread if not exists (first wolf's turn)
            if not game.wolf_thread_id:
                try:
                    wolf_thread = await game_channel.create_thread(
                        name=f"Sói-Đêm-{game.night_count}",
                        type=discord.ChannelType.private_thread
                    )
                    game.wolf_thread_id = wolf_thread.id
                    log(f"WOLF_THREAD_CREATE Night {game.night_count}: Created thread {wolf_thread.id}")
                except Exception as e:
                    log(f"FAIL WOLF_THREAD_CREATE [{wolf.username}]: {e}")
                    return
            
            # Get wolf thread
            wolf_thread = self.bot.get_channel(game.wolf_thread_id)
            if not wolf_thread:
                log(f"FAIL WOLF_ACTION [{wolf.username}] Wolf thread {game.wolf_thread_id} not found")
                return
            
            alive_targets = [p for p in game.get_alive_players() if p.user_id != wolf.user_id]
            if not alive_targets:
                log(f"WARN WOLF_ACTION [{wolf.username}] No alive targets available")
                return
            
            # Prepare target list
            target_list = "\n".join([f"• {p.username}" for p in alive_targets])
            embed = discord.Embed(
                title=f"Đêm {game.night_count} - Chọn mục tiêu",
                description=f"**<@{wolf.user_id}> hãy chọn mục tiêu để cắn:**\n\n{target_list}",
                color=discord.Color.red()
            )
            
            from .views import RoleSelectView
            view = RoleSelectView(
                game=game,
                player=wolf,
                candidates=alive_targets,
                action_type="kill",
                on_select=self._on_wolf_select,
                timeout=game.night_duration
            )
            
            # Send to wolf thread with ping for this wolf
            await wolf_thread.send(f"<@{wolf.user_id}>", embed=embed, view=view)
            log(f"OK WOLF_ACTION [{wolf.username}] Sent action prompt with {len(alive_targets)} targets in thread")
            
        except Exception as e:
            log(f"FAIL WOLF_ACTION_ERROR [{wolf.username}]: {e}")
    
    async def _on_wolf_select(self, interaction: discord.Interaction, player: GamePlayer, target_id: int, action: str):
        """Callback khi Sói chọn - Track wolf vote for early exit"""
        try:
            log(f"WOLF_SELECT_START [{player.username}] target_id={target_id}, action={action}")
            
            player.night_target = target_id
            player.night_action = action
            
            # Get game_id from player.game instead of interaction.guild (safer for DM fallback)
            if not player.game:
                log(f"FAIL WOLF_SELECT: player.game is None")
                try:
                    await interaction.response.defer(ephemeral=True)
                    await interaction.followup.send("ERROR: Game not found", ephemeral=True)
                except:
                    pass
                return
            
            game_id = player.game.guild_id
            if game_id not in self.wolf_votes:
                self.wolf_votes[game_id] = {}
            
            lock = await self._get_or_create_vote_lock(game_id)
            async with lock:
                self.wolf_votes[game_id][player.user_id] = target_id
                log(f"WOLF_VOTE_TRACKED [{player.username}] target={target_id}, total_votes={len(self.wolf_votes[game_id])}")
            
            # Defer and send response safely - with better error handling
            try:
                log(f"WOLF_SELECT_RESPOND: Deferring interaction for {player.username}")
                await interaction.response.defer(ephemeral=True)
                log(f"WOLF_SELECT_RESPOND: Deferred, now sending followup")
                await interaction.followup.send("OK Ban da chon muc tieu", ephemeral=True)
                log(f"WOLF_SELECT_RESPOND: Sent followup successfully")
            except discord.errors.InteractionResponded:
                log(f"WARN WOLF_SELECT: Interaction already responded")
            except Exception as resp_err:
                log(f"WARN WOLF_SELECT_RESPONSE: Could not send response: {type(resp_err).__name__}: {resp_err}")
                
        except Exception as e:
            log(f"FAIL WOLF_SELECT_ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    # ================ DOCTOR ACTIONS ================
    
    async def _handle_doctor_action(self, game: GameWerewolf, doctor: GamePlayer):
        """Bác Sĩ chọn người để che chở"""
        try:
            user = await self.bot.fetch_user(doctor.user_id)
            alive_targets = [p for p in game.get_alive_players() if p.user_id != doctor.user_id]
            
            if not alive_targets:
                return
            
            # Filter out the person protected last night (cannot protect same person 2 nights in a row)
            if doctor.doctor_last_protected:
                alive_targets = [p for p in alive_targets if p.user_id != doctor.doctor_last_protected]
            
            if not alive_targets:
                # If all targets are filtered (only 1 person left), allow protecting them
                alive_targets = [p for p in game.get_alive_players() if p.user_id != doctor.user_id]
            
            embed = discord.Embed(
                title="⚕️ BAN ĐÊM - CHE CHỞ",
                description="Chọn một người để che chở (sẽ không bị giết)\n\n**Lưu ý:** Không thể che chở cùng người ở đêm liên tiếp",
                color=discord.Color.green()
            )
            
            # Show who was protected last night
            if doctor.doctor_last_protected:
                last_protected = game.players.get(doctor.doctor_last_protected)
                if last_protected:
                    embed.add_field(
                        name="Đêm trước",
                        value=f"Đã che chở: **{last_protected.username}**",
                        inline=False
                    )
            
            from .views import RoleSelectView
            view = RoleSelectView(
                game=game,
                player=doctor,
                candidates=alive_targets,
                action_type="heal",
                on_select=self._on_doctor_select,
                timeout=game.night_duration
            )
            
            await user.send(embed=embed, view=view)
            log(f"DM sent to {doctor.username} (Doctor)")
        
        except Exception as e:
            log(f"Error in _handle_doctor_action: {e}")
    
    async def _on_doctor_select(self, interaction: discord.Interaction, player: GamePlayer, target_id: int, action: str):
        """Callback khi Bác Sĩ chọn"""
        try:
            log(f"DOCTOR_SELECT_START [{player.username}] target_id={target_id}")
            
            # Check if changing previous choice
            old_target_id = player.night_target
            player.night_target = target_id
            player.night_action = action
            
            target_player = player.game.players.get(target_id)
            target_name = target_player.username if target_player else "Unknown"
            
            old_target_name = ""
            if old_target_id and old_target_id != target_id:
                old_target = player.game.players.get(old_target_id)
                old_target_name = old_target.username if old_target else "Unknown"
                log(f"DOCTOR_CHANGE: {player.username} changed from {old_target_name} to {target_name}")
            
            try:
                await interaction.response.defer(ephemeral=True)
                if old_target_id and old_target_id != target_id:
                    await interaction.followup.send(
                        f"✅ Đã thay đổi: Từ **{old_target_name}** → **{target_name}**",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"✅ Bạn sẽ che chở **{target_name}**",
                        ephemeral=True
                    )
                log(f"DOCTOR_SELECT_OK [{player.username}] protecting {target_name}")
            except discord.errors.InteractionResponded:
                log(f"WARN DOCTOR_SELECT: Interaction already responded")
            except Exception as resp_err:
                log(f"WARN DOCTOR_SELECT_RESPONSE: {type(resp_err).__name__}: {resp_err}")
        except Exception as e:
            log(f"FAIL DOCTOR_SELECT_ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    # ================ SEER ACTIONS ================
    
    async def _handle_seer_action(self, game: GameWerewolf, seer: GamePlayer):
        """Tiên Tri xem vai trò của người chơi"""
        try:
            user = await self.bot.fetch_user(seer.user_id)
            alive_targets = [p for p in game.get_alive_players() if p.user_id != seer.user_id]
            
            if not alive_targets:
                return
            
            embed = discord.Embed(
                title="🔮 BAN ĐÊM - SỰ HIỆN NGỘ",
                description="Chọn một người để xem vai trò thực sự",
                color=discord.Color.purple()
            )
            
            from .views import RoleSelectView
            view = RoleSelectView(
                game=game,
                player=seer,
                candidates=alive_targets,
                action_type="check",
                on_select=self._on_seer_select,
                timeout=game.night_duration
            )
            
            await user.send(embed=embed, view=view)
            log(f"DM sent to {seer.username} (Seer)")
        
        except Exception as e:
            log(f"Error in _handle_seer_action: {e}")
    
    async def _on_seer_select(self, interaction: discord.Interaction, player: GamePlayer, target_id: int, action: str):
        """Callback khi Tiên Tri chọn"""
        try:
            log(f"SEER_SELECT_START [{player.username}] target_id={target_id}")
            
            try:
                await interaction.response.defer(ephemeral=True)
                
                if target_id in player.game.players:
                    target = player.game.players[target_id]
                    role_name = target.role.value if target.role else "?"
                    
                    await interaction.followup.send(
                        f"✅ Vai trò của {target.username}: **{role_name}**",
                        ephemeral=True
                    )
                    log(f"SEER_SELECT_OK [{player.username}] target={target.username} role={role_name}")
                else:
                    log(f"WARN SEER_SELECT: Target {target_id} not in game")
            except discord.errors.InteractionResponded:
                log(f"WARN SEER_SELECT: Interaction already responded")
            except Exception as resp_err:
                log(f"WARN SEER_SELECT_RESPONSE: {type(resp_err).__name__}: {resp_err}")
            
            player.night_target = target_id
            player.night_action = action
        except Exception as e:
            log(f"FAIL SEER_SELECT_ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    # ================ AURA SEER ACTIONS ================
    
    async def _handle_aura_seer_action(self, game: GameWerewolf, aura_seer: GamePlayer):
        """Thầy Bói xem phe của người chơi"""
        try:
            user = await self.bot.fetch_user(aura_seer.user_id)
            alive_targets = [p for p in game.get_alive_players() if p.user_id != aura_seer.user_id]
            
            if not alive_targets:
                return
            
            embed = discord.Embed(
                title="👁️ BAN ĐÊM - NHÌN THẤU HỒNG NHAN",
                description="Chọn một người để xem họ là Sói hay Dân",
                color=discord.Color.orange()
            )
            
            from .views import RoleSelectView
            view = RoleSelectView(
                game=game,
                player=aura_seer,
                candidates=alive_targets,
                action_type="aura",
                on_select=self._on_aura_seer_select,
                timeout=game.night_duration
            )
            
            await user.send(embed=embed, view=view)
            log(f"DM sent to {aura_seer.username} (Aura Seer)")
        
        except Exception as e:
            log(f"Error in _handle_aura_seer_action: {e}")
    
    async def _on_aura_seer_select(self, interaction: discord.Interaction, player: GamePlayer, target_id: int, action: str):
        """Callback khi Thầy Bói chọn"""
        try:
            if target_id in player.game.players:
                target = player.game.players[target_id]
                metadata = ROLE_METADATA.get(target.role)
                faction_name = metadata.faction.value if metadata else "?"
                
                await interaction.response.send_message(
                    f"✅ {target.username} thuộc phe: **{faction_name}**",
                    ephemeral=True
                )
            
            player.night_target = target_id
            player.night_action = action
        except Exception as e:
            log(f"Error in _on_aura_seer_select: {e}")
    
    # ================ WITCH ACTIONS ================
    
    async def _handle_witch_action(self, game: GameWerewolf, witch: GamePlayer):
        """Phù Thủy dùng bình"""
        try:
            user = await self.bot.fetch_user(witch.user_id)
            
            # Check nếu ai bị tấn công trong đêm này
            # Witch chỉ có thể dùng bình cứu khi ai bị tấn công
            embed = discord.Embed(
                title="🧪 BAN ĐÊM - PHÂN TÍCH",
                description=f"Bạn có 2 bình:\n"
                           f"• **Bình Cứu** (1 lần) - Chỉ dùng khi ai bị tấn công\n"
                           f"• **Bình Giết** (1 lần) - Giết ai đó\n\n"
                           f"Bình cứu: {'✅' if witch.potion_heal else '❌'}\n"
                           f"Bình giết: {'✅' if witch.potion_kill else '❌'}\n\n"
                           f"(Note: Các lựa chọn sẽ được xử lý nếu ai bị tấn công)",
                color=discord.Color.blue()
            )
            
            # TODO: Implement witch potion UI (wait to see if someone is attacked first)
            # For now, just send info
            await user.send(embed=embed)
            log(f"DM sent to {witch.username} (Witch)")
        
        except Exception as e:
            log(f"Error in _handle_witch_action: {e}")
    
    # ================ BEAST HUNTER ACTIONS ================
    
    async def _handle_beast_hunter_action(self, game: GameWerewolf, hunter: GamePlayer):
        """Thợ Săn Quái Thú đặt bẫy"""
        try:
            user = await self.bot.fetch_user(hunter.user_id)
            alive_targets = [p for p in game.get_alive_players()]  # Có thể bẫy chính mình
            
            if not alive_targets:
                return
            
            embed = discord.Embed(
                title="🪤 BAN ĐÊM - ĐẶT BẪY",
                description="Đặt bẫy lên một người (nếu Sói cắn thì Sói yếu nhất chết)",
                color=discord.Color.brown()
            )
            
            from .views import RoleSelectView
            view = RoleSelectView(
                game=game,
                player=hunter,
                candidates=alive_targets,
                action_type="trap",
                on_select=self._on_beast_hunter_select,
                timeout=game.night_duration
            )
            
            await user.send(embed=embed, view=view)
            log(f"DM sent to {hunter.username} (Beast Hunter)")
        
        except Exception as e:
            log(f"Error in _handle_beast_hunter_action: {e}")
    
    async def _on_beast_hunter_select(self, interaction: discord.Interaction, player: GamePlayer, target_id: int, action: str):
        """Callback khi Thợ Săn đặt bẫy"""
        try:
            player.trap_on = target_id
            player.night_action = action
            await interaction.response.send_message("✅ Bạn đã đặt bẫy", ephemeral=True)
        except Exception as e:
            log(f"Error in _on_beast_hunter_select: {e}")
    
    # ================ MEDIUM ACTIONS ================
    
    async def _handle_medium_action(self, game: GameWerewolf, medium: GamePlayer):
        """Thầy Đồng nói chuyện với người chết & hồi sinh"""
        try:
            user = await self.bot.fetch_user(medium.user_id)
            dead_players = game.get_dead_players()
            
            if not dead_players:
                embed = discord.Embed(
                    title="👻 BAN ĐÊM - THẦY ĐỒNG",
                    description="Không có ai chết để bạn nói chuyện",
                    color=discord.Color.gray()
                )
                await user.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="👻 BAN ĐÊM - HỒI SINH",
                description="Chọn một người để hồi sinh (chỉ 1 lần/ván)",
                color=discord.Color.light_gray()
            )
            
            from .views import RoleSelectView
            view = RoleSelectView(
                game=game,
                player=medium,
                candidates=dead_players,
                action_type="revive",
                on_select=self._on_medium_select,
                timeout=game.night_duration
            )
            
            await user.send(embed=embed, view=view)
            log(f"DM sent to {medium.username} (Medium)")
        
        except Exception as e:
            log(f"Error in _handle_medium_action: {e}")
    
    async def _on_medium_select(self, interaction: discord.Interaction, player: GamePlayer, target_id: int, action: str):
        """Callback khi Thầy Đồng chọn hồi sinh"""
        try:
            player.night_target = target_id
            player.night_action = action
            await interaction.response.send_message("✅ Bạn đã chọn hồi sinh người đó", ephemeral=True)
        except Exception as e:
            log(f"Error in _on_medium_select: {e}")
    
    # ================ BOMBER ACTIONS ================
    
    async def _handle_bomber_action(self, game: GameWerewolf, bomber: GamePlayer):
        """Kẻ Đặt Bom đặt bom"""
        try:
            user = await self.bot.fetch_user(bomber.user_id)
            alive_targets = [p for p in game.get_alive_players()]
            
            if not alive_targets:
                return
            
            embed = discord.Embed(
                title="💣 BAN ĐÊM - ĐẶT BOM",
                description="Chọn một người để đặt bom (nổ đêm tiếp theo)",
                color=discord.Color.dark_red()
            )
            
            from .views import RoleSelectView
            view = RoleSelectView(
                game=game,
                player=bomber,
                candidates=alive_targets,
                action_type="bomb",
                on_select=self._on_bomber_select,
                timeout=game.night_duration
            )
            
            await user.send(embed=embed, view=view)
            log(f"DM sent to {bomber.username} (Bomber)")
        
        except Exception as e:
            log(f"Error in _handle_bomber_action: {e}")
    
    async def _on_bomber_select(self, interaction: discord.Interaction, player: GamePlayer, target_id: int, action: str):
        """Callback khi Kẻ Đặt Bom chọn"""
        try:
            player.bomb_target_night = target_id
            player.night_action = action
            await interaction.response.send_message("✅ Bạn đã đặt bom", ephemeral=True)
        except Exception as e:
            log(f"Error in _on_bomber_select: {e}")
    
    # ================ RESOLVE NIGHT ACTIONS ================
    
    async def _resolve_night_actions(self, game: GameWerewolf, channel: discord.TextChannel) -> Dict:
        """Xử lý tất cả hành động ban đêm"""
        kills = []
        heals = []
        log_lines = []
        
        # 1. Collect wolf kills
        wolf_targets = []
        for player in game.get_players_by_faction(Faction.WOLF):
            if player.night_target and player.is_alive:
                weight = 1
                if player.role == Role.WOLF_ALPHA:
                    weight = 2  # Alpha wolf kill counts twice
                wolf_targets.extend([player.night_target] * weight)
        
        # Determine victim (most votes)
        if wolf_targets:
            from collections import Counter
            victim = Counter(wolf_targets).most_common(1)[0][0]
            kills.append(victim)
            
            victim_player = game.players.get(victim)
            log_lines.append(f"🐺 Sói cắn {victim_player.username if victim_player else 'người chơi #' + str(victim)}")
            log(f"NIGHT_KILL: Wolf targets victim {victim_player.username if victim_player else victim}")
        
        # 2. Collect doctor heals
        for player in game.players.values():
            if player.role == Role.DOCTOR and player.night_target and player.is_alive:
                heals.append(player.night_target)
                healed_player = game.players.get(player.night_target)
                log_lines.append(f"⚕️ Bác sĩ che chở {healed_player.username if healed_player else 'người chơi #' + str(player.night_target)}")
                log(f"NIGHT_HEAL: Doctor protects {healed_player.username if healed_player else player.night_target}")
        
        # 3. Witch actions
        for player in game.players.values():
            if player.role == Role.WITCH and player.is_alive:
                # TODO: Implement witch potion use
                pass
        
        # 4. Apply heals (remove kills that were protected)
        final_kills = [k for k in kills if k not in heals]
        
        # Log if someone was saved
        if len(final_kills) < len(kills):
            log_lines.append(f"✅ Người bị cắn được cứu sống!")
            log(f"NIGHT_SAVED: {len(kills) - len(final_kills)} player(s) saved by doctor")
        
        # 5. Beast Hunter trap
        for player in game.players.values():
            if player.role == Role.BEAST_HUNTER and player.trap_on and player.is_alive:
                if player.trap_on in final_kills:
                    # Trap triggers - weakest wolf dies
                    wolves = game.get_players_by_faction(Faction.WOLF)
                    if wolves:
                        weakest = min(wolves, key=lambda w: w.user_id)  # Simple logic
                        final_kills.append(weakest.user_id)
                        log_lines.append(f"🪤 Bẫy kích hoạt! {weakest.username} chết!")
                        log(f"NIGHT_TRAP: Beast hunter trap kills {weakest.username}")
        
        # 6. Apply kills
        for user_id in final_kills:
            if user_id in game.players:
                player = game.players[user_id]
                player.is_alive = False
                game.dead_players.append(user_id)
                log(f"NIGHT_DEAD: {player.username} is now dead")
        
        # 7. Check cursed villager turning into wolf
        for user_id in final_kills:
            if user_id in game.players:
                player = game.players[user_id]
                if player.role == Role.CURSED_VILLAGER:
                    player.role = Role.WEREWOLF
                    player.is_alive = True  # Resurrected as wolf
                    log_lines.append(f"🔄 {player.username} đã biến thành Sói!")
                    log(f"NIGHT_CONVERT: {player.username} converted to werewolf")
        
        # 8. Medium revival
        for player in game.players.values():
            if player.role == Role.MEDIUM and player.night_target and player.revival_available and player.is_alive:
                if player.night_target in game.dead_players:
                    target = game.players.get(player.night_target)
                    if target:
                        target.is_alive = True
                        game.dead_players.remove(player.night_target)
                        player.revival_available = False
                        log_lines.append(f"👻 {target.username} được hồi sinh!")
                        log(f"NIGHT_REVIVAL: Medium revives {target.username}")
        
        # 9. Update doctor's protection history for next night
        for player in game.players.values():
            if player.role == Role.DOCTOR and player.is_alive:
                if player.night_target:
                    player.doctor_last_protected = player.night_target
                    log(f"DOCTOR_HISTORY: {player.username} protected {game.players.get(player.night_target).username if player.night_target in game.players else player.night_target}")
        
        # 10. Send night results to channel
        if log_lines:
            embed = discord.Embed(
                title=f"🌙 Kết Quả Ban Đêm #{game.night_count}",
                description="\n".join(log_lines),
                color=discord.Color.dark_blue()
            )
            await channel.send(embed=embed)
        else:
            embed = discord.Embed(
                title=f"🌙 Đêm #{game.night_count}",
                description="Đêm qua bình yên lành...",
                color=discord.Color.dark_blue()
            )
            await channel.send(embed=embed)
        
        # Reset night actions for next round
        game.night_actions_log = {
            "kills": final_kills,
            "heals": heals,
            "log": "\n".join(log_lines)
        }
        
        # Reset night targets for next round (for roles that reset each night)
        for player in game.players.values():
            if player.is_alive:
                player.night_target = None
                player.night_action = None
        
        return game.night_actions_log
    
    # ================ UTILITY ================
    
    async def _mute_channel(self, channel: discord.TextChannel, mute: bool):
        """Mute/unmute channel - if mute=True, also mutes dead players individually"""
        try:
            guild = channel.guild
            
            if mute:
                log(f"🔇 MUTE: Muting #{channel.name} for ban đêm")
                # Deny @everyone first
                overwrite = channel.overwrites_for(guild.default_role)
                overwrite.send_messages = False
                await channel.set_permissions(guild.default_role, overwrite=overwrite)
                log(f"✅ MUTE: @everyone muted in #{channel.name}")
            else:
                log(f"🔊 UNMUTE: Unmuting #{channel.name} for ban ngày")
                # Allow @everyone to send messages again
                overwrite = channel.overwrites_for(guild.default_role)
                overwrite.send_messages = None
                await channel.set_permissions(guild.default_role, overwrite=overwrite)
                log(f"✅ UNMUTE: @everyone unmuted in #{channel.name}")
        except Exception as e:
            log(f"❌ MUTE_ERROR in #{channel.name}: {e}")
